import gc
import math
import os
import sys
import glob
import h5py
from scipy.signal import butter, filtfilt, spectrogram
from scipy.interpolate import interp1d
from sklearn.cluster import DBSCAN
import multiprocessing
from Updater import check_for_update, download_and_install_update
from VideoEditor import VideoEditor
from GridWidget import GridWidget
from GraphWidget import GraphWidget
from LoadingDialog import LoadingDialog
from LegendWidget import LegendWidget
from SquareWidget import SquareWidget
from AnalysisThread import AnalysisThread
from ColorCell import ColorCell
from MatlabEngineThread import MatlabEngineThread
from RasterPlot import RasterPlot
from GroupSelectionDialog import GroupSelectionDialog, Group
from Settings import (
    SettingsWidgetManager,
    SpectrogramSettingsWidget,
    DBSCANSettingsWidget,
    PeakSettingsWidget,
)
from ClusterTracker import ClusterLegend, ClusterTracker
from SignalAnalyzer import SignalAnalyzer
from Media import SaveChannelPlotsDialog, save_grid_as_png, save_mea_with_plots
from ProgressBar import EEGScrubberWidget

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import (
    QLineF,
    QPointF,
    QRectF,
    QThread,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import qdarktheme
from Constants import (
    BACKGROUND,
    PROPAGATION,
    SEIZURE,
    SE,
    ACTIVE,
    GRAPH_DOWNSAMPLE,
    STROKE_WIDTH,
    MAC,
    WIN,
    VERSION,
)


class UpdateThread(QThread):
    update_completed = pyqtSignal(bool)

    def __init__(self, latest_release):
        super().__init__()
        self.latest_release = latest_release

    def run(self):
        success = download_and_install_update(self.latest_release)
        self.update_completed.emit(success)


class MainWindow(QMainWindow):
    gridUpdateRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        pg.setConfigOptions(antialias=True)
        pg.setConfigOptions(enableExperimental=True)
        try:
            pg.setConfigOptions(useNumba=True)
            pg.setConfigOptions(useOpenGL=True)
            win = pg.plot()
            win.setWindowTitle('pyqtgraph 2D Plot Test')
            x = np.linspace(0, 10, 100)
            y = np.sin(x)
            win.plot(x, y, pen='r', symbol='o')
            win.hide()
            del win
            del x, y
        except Exception as e:
            print(f"Error: {e}")
            pg.setConfigOptions(antialias=False)
            pg.setConfigOptions(enableExperimental=False)
            pg.setConfigOptions(useOpenGL=False)
        self.file_path = None
        self.tolerance = 40
        self.recording_length = None
        self.sampling_rate = 100
        self.time_vector = None
        self.data = None
        self.active_channels = None
        self.selected_channel = None
        self.plotted_channels: list[ColorCell] = [None] * 4
        self.selected_subplot = None
        self.raster_tooltip = None
        self.is_recording_video = False
        self.min_strength = None
        self.max_strength = None
        self.raster_downsample_factor = 1
        self.opacity = 1.0
        self.seized_cells = []
        self.prop_cells = []
        self.arrow_items = []
        self.prop_arrow_items = []
        self.do_show_spread_lines = False
        self.do_show_prop_lines = False
        self.do_show_playheads = True
        self.current_region = None
        self.custom_region = None
        self.peak_thresholds = {}
        self.discharges = {}
        self.raster_plot = None
        self.order_amount = 10
        self.do_show_false_color_map = True
        self.do_show_events = True
        self.overall_min_voltage = None
        self.overall_max_voltage = None
        self.last_skip_time = 0
        self.groups = []
        self.left_pane = None
        self.right_pane = None
        self.grid_widget = None
        self.lock_to_playhead = False
        self.enhanced_region = None
        self.n_std_dev = 4
        self.distance = 10
        self.chunk_size = 256
        self.overlap = 0
        self.fs_range = (0.5, 50)
        self.centroids = []
        self.eps = 4.8
        self.min_samples = 4
        self.percentile = 99
        self.max_distance = 10
        self.bin_size = 0.0133
        self.signal_analyzer = None
        self.active_discharges = []
        self.snr_threshold = 7
        self.current_discharge_index = 0
        self.is_auto_analyzing = False
        self.low_pass_cutoff = 35  # Default value
        self.markers = []

        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.analysis_cancelled.connect(self.cancel_analysis)

        self.analysis_thread = AnalysisThread(self)
        self.analysis_thread.progress_updated.connect(
            self.loading_dialog.update_progress
        )
        self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)

        self.setWindowTitle(f"--- MEA GUI {VERSION} ---")

        self.menuBar = QMenuBar(self)
        self.menuBar.setNativeMenuBar(False)
        self.setMenuBar(self.menuBar)

        self.fileMenu = QMenu("File", self)
        self.menuBar.addMenu(self.fileMenu)
        self.openAction = QAction("Open file", self)
        self.openAction.triggered.connect(self.openFile)
        self.fileMenu.addAction(self.openAction)
        self.createVideoAction = QAction("Save MEA as video", self)
        self.createVideoAction.triggered.connect(self.show_video_editor)
        self.fileMenu.addAction(self.createVideoAction)
        self.saveGridAction = QAction("Save MEA as png", self)
        self.saveGridAction.triggered.connect(lambda: save_grid_as_png(self))
        self.fileMenu.addAction(self.saveGridAction)
        self.saveChannelPlotsAction = QAction("Save channel plots", self)
        self.saveChannelPlotsAction.triggered.connect(self.save_channel_plots)
        self.fileMenu.addAction(self.saveChannelPlotsAction)
        self.saveMeaWithPlotsAction = QAction("Save MEA with channel plots", self)
        self.saveMeaWithPlotsAction.triggered.connect(lambda: save_mea_with_plots(self))
        self.fileMenu.addAction(self.saveMeaWithPlotsAction)

        self.editMenu = QMenu("Edit", self)
        self.menuBar.addMenu(self.editMenu)

        self.setLowPassFilterAction = QAction("Set Low Pass Filter", self)
        self.setLowPassFilterAction.triggered.connect(self.set_low_pass_filter)
        self.editMenu.addAction(self.setLowPassFilterAction)

        self.settings_manager = SettingsWidgetManager(self.editMenu)

        self.setRasterDownsampleAction = QAction("Set raster downsample factor", self)
        self.setRasterDownsampleAction.triggered.connect(self.set_raster_downsample)
        self.editMenu.addAction(self.setRasterDownsampleAction)

        self.updateRasterPlotAction = QAction("Create raster", self)
        self.updateRasterPlotAction.triggered.connect(self.update_raster)
        self.editMenu.addAction(self.updateRasterPlotAction)
        self.editMenu.addSeparator()

        self.peak_settings_widget = PeakSettingsWidget(self)
        self.settings_manager.add_widget("Set Peak Settings", self.peak_settings_widget)

        self.spectrogram_settings_widget = SpectrogramSettingsWidget(self)
        self.settings_manager.add_widget(
            "Set spectrogram settings", self.spectrogram_settings_widget
        )

        self.db_scan_settings_widget = DBSCANSettingsWidget(self)
        self.settings_manager.add_widget(
            "Set DBSCAN settings", self.db_scan_settings_widget
        )

        self.viewMenu = QMenu("View", self)
        self.menuBar.addMenu(self.viewMenu)

        self.toggleLegendAction = QAction("Legend", self, checkable=True)
        self.toggleLegendAction.setChecked(False)
        self.toggleLegendAction.triggered.connect(self.toggle_legend)
        self.viewMenu.addAction(self.toggleLegendAction)

        self.toggleMiniMapAction = QAction("Mini-map", self, checkable=True)
        self.toggleMiniMapAction.setChecked(True)
        self.toggleMiniMapAction.triggered.connect(self.toggle_mini_map)
        self.viewMenu.addAction(self.toggleMiniMapAction)

        self.togglePlayheadsActions = QAction("Playheads", self, checkable=True)
        self.togglePlayheadsActions.setChecked(True)
        self.togglePlayheadsActions.triggered.connect(self.toggle_playheads)
        self.viewMenu.addAction(self.togglePlayheadsActions)

        self.antiAliasAction = QAction("Anti-aliasing", self, checkable=True)
        self.antiAliasAction.setChecked(False)
        self.antiAliasAction.triggered.connect(self.toggle_antialiasing)
        self.viewMenu.addAction(self.antiAliasAction)

        self.toggleLinesAction = QAction("Spread lines", self, checkable=True)
        self.toggleLinesAction.setChecked(False)
        self.toggleLinesAction.triggered.connect(self.toggle_lines)
        self.viewMenu.addAction(self.toggleLinesAction)

        self.togglePropLinesAction = QAction("Propagation lines", self, checkable=True)
        self.togglePropLinesAction.setChecked(False)
        self.togglePropLinesAction.triggered.connect(self.toggle_prop_lines)
        self.viewMenu.addAction(self.togglePropLinesAction)

        self.toggleEventsAction = QAction("Detected events", self, checkable=True)
        self.toggleEventsAction.setChecked(True)
        self.toggleEventsAction.triggered.connect(self.toggle_events)
        self.viewMenu.addAction(self.toggleEventsAction)

        self.toggleColorMappingAction = QAction("False color map", self, checkable=True)
        self.toggleColorMappingAction.setChecked(True)
        self.toggleColorMappingAction.triggered.connect(self.toggle_false_color_map)
        self.viewMenu.addAction(self.toggleColorMappingAction)

        self.viewMenu.addSeparator()

        self.toggleRegionsAction = QAction("Seizure regions", self, checkable=True)
        self.toggleRegionsAction.setChecked(True)
        self.toggleRegionsAction.triggered.connect(self.toggle_regions)
        self.viewMenu.addAction(self.toggleRegionsAction)

        self.toggleSpectrogramAction = QAction("Spectrograms", self, checkable=True)
        self.toggleSpectrogramAction.setChecked(False)
        self.toggleSpectrogramAction.triggered.connect(self.toggle_spectrogram)
        self.viewMenu.addAction(self.toggleSpectrogramAction)

        self.viewMenu.addSeparator()

        self.setBinSizeAction = QAction("Set bin size", self)
        self.setBinSizeAction.triggered.connect(self.set_bin_size)
        self.viewMenu.addAction(self.setBinSizeAction)

        self.setOrderAmountAction = QAction("Set order amount", self)
        self.setOrderAmountAction.triggered.connect(self.set_order_amount)
        self.viewMenu.addAction(self.setOrderAmountAction)

        for action in self.viewMenu.actions():
            if action.isCheckable():
                action.triggered.connect(self.handle_checkable_action)

        self.main_tab_widget = QTabWidget()
        self.tab_widget = QTabWidget()
        self.main_tab_widget.currentChanged.connect(self.update_tab_layout)
        self.setCentralWidget(self.main_tab_widget)

        self.main_tab = QWidget()
        self.main_tab_layout = QHBoxLayout()
        self.main_tab.setLayout(self.main_tab_layout)

        self.stats_tab = QWidget()
        self.stats_tab_layout = QVBoxLayout()
        self.stats_tab.setLayout(self.stats_tab_layout)

        self.main_tab_widget.addTab(self.main_tab, "Main")
        self.main_tab_widget.addTab(self.stats_tab, "Stats")

        self.left_pane = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_pane.setLayout(self.left_layout)
        self.main_tab_layout.addWidget(self.left_pane)

        self.left_layout.addWidget(self.tab_widget)

        self.grid_widget = GridWidget(64, 64)
        self.grid_widget.setMinimumHeight(self.grid_widget.height() + 100)
        self.grid_widget.cell_clicked.connect(self.on_cell_clicked)
        self.grid_widget.save_as_video_requested.connect(self.show_video_editor)
        self.grid_widget.save_as_image_requested.connect(lambda: save_grid_as_png(self))

        square_widget = SquareWidget()
        square_layout = QVBoxLayout()
        square_widget.setLayout(square_layout)
        square_layout.addWidget(self.grid_widget)

        self.cluster_tracker = ClusterTracker()

        self.legend_view = QGraphicsView()
        self.legend_scene = QGraphicsScene()
        self.legend_view.setScene(self.legend_scene)
        self.legend_view.setFixedHeight(100)

        legend_width = self.grid_widget.width()
        self.cluster_legend = ClusterLegend(
            self.legend_scene,
            0,
            0,
            legend_width,
            100,
        )

        self.legend_widget = LegendWidget()
        self.legend_widget.setVisible(False)

        mea_grid_layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.legend_widget)
        top_layout.addWidget(square_widget)

        mea_grid_layout.addLayout(top_layout)
        mea_grid_layout.addWidget(self.legend_view)

        mea_grid_widget = QWidget()
        mea_grid_widget.setLayout(mea_grid_layout)

        self.tab_widget.addTab(mea_grid_widget, "MEA Grid")

        self.second_tab_widget = QWidget()
        self.second_tab_layout = QVBoxLayout()
        self.second_tab_widget.setLayout(self.second_tab_layout)
        self.tab_widget.addTab(self.second_tab_widget, "Raster Plot")

        self.second_plot_widget = pg.PlotWidget()
        self.second_plot_widget.setAspectLocked(False)
        self.second_plot_widget.setBackground("w")
        self.second_tab_layout.addWidget(self.second_plot_widget)

        self.raster_settings_layout = QHBoxLayout()
        self.second_tab_layout.addLayout(self.raster_settings_layout)

        self.raster_settings_layout.addWidget(QLabel("Raster Settings:"))

        self.edit_raster_settings_button = QPushButton("Edit Raster Settings")
        self.raster_settings_layout.addWidget(self.edit_raster_settings_button)
        self.edit_raster_settings_button.clicked.connect(self.edit_raster_settings)

        self.create_groups_button = QPushButton("Create Groups")
        self.raster_settings_layout.addWidget(self.create_groups_button)
        self.create_groups_button.clicked.connect(self.create_groups)

        self.toggle_color_mode_button = QPushButton("Toggle Color Mode")
        self.raster_settings_layout.addWidget(self.toggle_color_mode_button)
        self.toggle_color_mode_button.clicked.connect(self.toggle_raster_color_mode)

        self.tab_widget.currentChanged.connect(self.update_tab_layout)

        self.right_pane = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_pane.setLayout(self.right_layout)
        self.main_tab_layout.addWidget(self.right_pane)

        # Create a splitter for the right pane
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_layout.addWidget(self.right_splitter)

        # Add graph pane to the splitter
        self.graph_pane = QWidget()
        self.graph_layout = QVBoxLayout()
        self.graph_pane.setLayout(self.graph_layout)
        self.right_splitter.addWidget(self.graph_pane)

        self.graph_widget = GraphWidget(self)
        self.graph_layout.addWidget(self.graph_widget)
        self.graph_widget.region_clicked.connect(self.handle_region_clicked)
        self.graph_widget.save_single_plot.connect(
            lambda: self.save_channel_plot(self.graph_widget.active_plot_index)
        )
        self.graph_widget.save_all_plots.connect(self.save_channel_plots)

        # Add settings pane to the splitter
        self.settings_pane = QWidget()
        self.settings_layout = QVBoxLayout()
        self.settings_pane.setLayout(self.settings_layout)
        self.right_splitter.addWidget(self.settings_pane)

        self.settings_top_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.settings_top_layout)

        self.opacity_label = QLabel("Image Opacity:")
        self.settings_top_layout.addWidget(self.opacity_label)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setTickPosition(QSlider.TicksBelow)
        self.opacity_slider.setTickInterval(25)
        self.opacity_slider.valueChanged.connect(self.set_grid_opacity)
        self.settings_top_layout.addWidget(self.opacity_slider)

        self.show_order_checkbox = QCheckBox("Show Order")
        self.show_order_checkbox.setEnabled(False)
        self.settings_top_layout.addWidget(self.show_order_checkbox)
        self.show_order_checkbox.stateChanged.connect(self.toggle_order)

        self.order_combo = QComboBox()
        self.order_combo.addItems(["Default", "Order by Seizure", "Order by SE"])
        self.settings_top_layout.addWidget(self.order_combo)
        self.order_combo.currentIndexChanged.connect(self.set_raster_order)

        self.control_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.control_layout)

        self.open_button = QPushButton(" Open File")
        self.open_button.clicked.connect(self.openFile)
        self.control_layout.addWidget(self.open_button)

        self.low_ram_checkbox = QCheckBox("󰡵 Low RAM Mode")
        self.control_layout.addWidget(self.low_ram_checkbox)

        self.cpp_mode_checkbox = QCheckBox(" Use C++")
        self.cpp_mode_checkbox.stateChanged.connect(self.toggle_cpp_mode)
        self.control_layout.addWidget(self.cpp_mode_checkbox)

        self.view_button = QPushButton(" Quick View")
        self.view_button.clicked.connect(self.run_analysis)
        self.control_layout.addWidget(self.view_button)

        self.run_button = QPushButton(" Run Analysis")
        self.run_button.clicked.connect(self.run_analysis)
        self.control_layout.addWidget(self.run_button)

        self.clear_button = QPushButton("󰆴 Clear Plots")
        self.control_layout.addWidget(self.clear_button)
        self.clear_button.clicked.connect(self.clear_plots)

        self.bottom_pane = QWidget()
        self.bottom_layout = QHBoxLayout()
        self.bottom_pane.setLayout(self.bottom_layout)
        self.right_layout.addWidget(self.bottom_pane)

        self.playback_layout = QHBoxLayout()
        self.bottom_layout.addLayout(self.playback_layout)

        self.progress_bar = EEGScrubberWidget()
        self.progress_bar.valueChanged.connect(self.seekPosition)
        self.playback_layout.addWidget(self.progress_bar, 1)

        self.skip_backward_button = QPushButton("")
        self.skip_backward_button.clicked.connect(self.skipBackward)
        self.progress_bar.control_layout.addWidget(self.skip_backward_button)

        self.prev_frame_button = QPushButton("")
        self.prev_frame_button.clicked.connect(self.stepBackward)
        self.progress_bar.control_layout.addWidget(self.prev_frame_button)

        self.play_pause_button = QPushButton("")
        self.play_pause_button.clicked.connect(self.playPause)
        self.progress_bar.control_layout.addWidget(self.play_pause_button)

        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.updatePlayback)

        self.next_frame_button = QPushButton("")
        self.next_frame_button.clicked.connect(self.stepForward)
        self.progress_bar.control_layout.addWidget(self.next_frame_button)

        self.skip_forward_button = QPushButton("")
        self.skip_forward_button.clicked.connect(self.skipForward)
        self.progress_bar.control_layout.addWidget(self.skip_forward_button)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(
            ["0.01", "0.1", "0.25", "0.5", "1.0", "2.0", "4.0", "16.0"]
        )
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentIndexChanged.connect(self.setPlaybackSpeed)

        self.speed_combo.view().setMinimumWidth(50)
        self.progress_bar.control_layout.addWidget(self.speed_combo)

        self.set_widgets_enabled()

        cwd = os.path.dirname(os.path.realpath(__file__))

        print(f"Current working directory: {cwd}")

        self.matlab_thread = MatlabEngineThread(cwd)
        self.matlab_thread.engine_started.connect(self.on_engine_started)
        self.matlab_thread.error_occurred.connect(self.on_engine_error)
        self.matlab_thread.start()
        self.eng = None
        self.use_cpp = False
        self.engine_started = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.redraw_arrows()

    def handle_update_button(self, button):
        if button.text() == "&Yes":
            self.download_msg = QMessageBox(self)
            self.download_msg.setIcon(QMessageBox.Information)
            self.download_msg.setText("Downloading update...")
            self.download_msg.setWindowTitle("Update in Progress")
            self.download_msg.setStandardButtons(QMessageBox.NoButton)
            self.download_msg.show()

            # Start the update thread
            self.update_thread = UpdateThread(self.latest_release)
            self.update_thread.update_completed.connect(self.on_update_completed)
            self.update_thread.start()

    def on_update_completed(self, success):
        # Close the "Downloading update..." message box
        self.download_msg.close()

        if success:
            sys.exit()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Update process failed.")
            msg.setWindowTitle("Update")
            msg.exec_()

    def confirm_latest_version(self):
        update_available, self.latest_release = check_for_update()
        if update_available:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("An update is available. Would you like to update now?")
            msg.setWindowTitle("Update")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.buttonClicked.connect(self.handle_update_button)
            msg.exec_()
        else:
            print("No update available.")

    def update_cluster_legend(self, cluster_stats):
        self.cluster_legend.update(cluster_stats)

        self.legend_view.setSceneRect(self.legend_scene.sceneRect())
        self.legend_view.fitInView(self.legend_scene.sceneRect(), Qt.KeepAspectRatio)

    def handle_checkable_action(self):
        QTimer.singleShot(0, self.viewMenu.show)

    def on_engine_error(self, error):
        print(f"Error starting MATLAB engine: {error}")
        # Show a temporary notifaication saying that c++ will be used instead
        self.use_cpp = True
        self.eng = None
        self.set_widgets_enabled()

    def on_engine_started(self, eng):
        self.engine_started = True
        self.eng = eng
        self.set_widgets_enabled()

    def update_progress(self, message, value):
        self.loading_dialog.update_progress(message, value)

    def toggle_events(self, checked):
        self.do_show_events = checked
        self.update_grid()

    def toggle_raster_color_mode(self):
        if self.raster_plot:
            self.raster_plot.toggle_color_mode()

    def toggle_false_color_map(self, checked):
        self.do_show_false_color_map = checked
        self.update_grid()

    def set_bin_size(self):
        bin_size, ok = QInputDialog.getText(
            self,
            "Set Bin Size",
            "Size:",
            QLineEdit.Normal,
            str(self.bin_size),
        )

        if ok:
            try:
                bin_size = float(bin_size)
                if bin_size <= 0:
                    raise ValueError("Bin size must be greater than 0.")
                self.bin_size = bin_size
            except ValueError as e:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(str(e))
                msg.setWindowTitle("Invalid Bin Size")
                msg.exec_()

    def enhance_current_view(self):
        start, stop = self.graph_widget.plot_widgets[0].viewRange()[0]

        self.enhanced_region = (start, stop)

        for i in range(4):
            if self.plotted_channels[i] is not None:
                self.graph_widget.redraw_region(start, stop, i)

    def clear_enhanced_view(self):
        self.enhanced_region = None
        self.current_region = None
        for i in range(4):
            if i in self.graph_widget.region_plots:
                self.graph_widget.plot_widgets[i].removeItem(
                    self.graph_widget.region_plots[i]
                )
                del self.graph_widget.region_plots[i]
            for item in self.graph_widget.plot_widgets[i].items():
                if (
                    isinstance(item, (pg.ScatterPlotItem, pg.PlotDataItem))
                    and item != self.graph_widget.plots[i]
                ):
                    self.graph_widget.plot_widgets[i].removeItem(item)
            ignore = int(10 * self.sampling_rate)

            if self.plotted_channels[i] is not None:
                row, col = self.plotted_channels[i].row, self.plotted_channels[i].col
                x = self.time_vector[ignore:-ignore]
                y = self.data[row, col]["signal"][ignore:-ignore]
                downsampled_x, downsampled_y = self.graph_widget.downsample_data(
                    x, y, GRAPH_DOWNSAMPLE
                )
                self.graph_widget.plots[i].setData(downsampled_x, downsampled_y)

    def handle_region_clicked(self, start, stop):
        print(f"Region clicked: {start}, {stop}")
        for i in range(4):
            if self.plotted_channels[i] is not None:
                self.graph_widget.plot_widgets[i].setXRange(start, stop)
                self.progress_bar.setValue(math.floor(start * self.sampling_rate))
                self.last_skip_time = start
        self.current_region = (start, stop)

    def toggle_regions(self, checked):
        self.graph_widget.do_show_regions = checked
        if checked:
            self.graph_widget.show_regions()
        else:
            self.graph_widget.hide_regions()

    def edit_raster_settings(self):
        if self.raster_plot is None:
            self.raster_plot = RasterPlot(
                self.data,
                self.sampling_rate,
                self.active_channels,
                self.raster_downsample_factor,
            )
            self.raster_plot.set_main_window(self)

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Raster Settings")
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumSize(300, 200)

        layout = QVBoxLayout(dialog)

        downsample_layout = QHBoxLayout()
        downsample_label = QLabel("Downsample Factor:")
        downsample_input = QLineEdit(str(self.raster_downsample_factor))
        downsample_layout.addWidget(downsample_label)
        downsample_layout.addWidget(downsample_input)
        layout.addLayout(downsample_layout)

        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Spike Threshold:")
        threshold_input = QLineEdit(str(self.raster_plot.spike_threshold))
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(threshold_input)
        layout.addLayout(threshold_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            try:
                downsample_factor = int(downsample_input.text())
                spike_threshold = float(threshold_input.text())

                self.raster_downsample_factor = downsample_factor
                self.raster_plot.downsample_factor = downsample_factor
                self.raster_plot.spike_threshold = spike_threshold

                self.update_raster()
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Invalid input values. Please enter valid numbers.",
                )

    def create_groups(self):
        dialog = GroupSelectionDialog(
            self, self.grid_widget.image_path, self.active_channels
        )
        if dialog.exec() == QDialog.Accepted:
            groups: list[Group] = dialog.get_groups()
            self.groups = groups
            for group in groups:
                for row, col in group.channels:
                    cell = self.grid_widget.cells[row - 1][col - 1]
                    color = [int(255 * x) for x in group.color]
                    cell.setColor(QColor(*color), 1, self.opacity)
            if self.raster_plot:
                self.raster_plot.set_groups(groups)
                self.raster_plot.update_raster_plot_data()

    def set_order_amount(self):
        order_amount, ok = QInputDialog.getInt(
            self,
            "Set Order Amount",
            "Amount:",
            self.order_amount,
        )

        if ok:
            if order_amount < 1:
                order_amount = 1
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Order amount must be greater than 0.")
                msg.setWindowTitle("Invalid Order Amount")
                msg.exec_()

            self.order_amount = order_amount
            self.toggle_order(self.show_order_checkbox.checkState())

    def toggle_legend(self, checked):
        self.legend_widget.setVisible(checked)
        if self.data is not None:
            self.redraw_arrows()
            self.update_grid()

    def toggle_mini_map(self, checked):
        self.graph_widget.toggle_mini_map(checked)

    def show_prop_lines(self):
        for arrow_item in self.prop_arrow_items:
            arrow_item["arrow"].show()
            arrow_item["arrow_head"].show()

    def hide_prop_lines(self):
        for arrow_item in self.prop_arrow_items:
            arrow_item["arrow"].hide()
            arrow_item["arrow_head"].hide()
        self.prop_arrow_items.clear()

    def show_spread_lines(self):
        for arrow_item in self.arrow_items:
            arrow_item["arrow"].show()
            arrow_item["arrow_head"].show()

    def hide_spread_lines(self):
        for arrow_item in self.arrow_items:
            arrow_item["arrow"].hide()
            arrow_item["arrow_head"].hide()
        self.arrow_items.clear()

    def set_spectrogram_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Spectrogram Settings")
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        chunk_layout = QHBoxLayout()
        chunk_label = QLabel("Chunk Size:")
        chunk_input = QLineEdit(str(self.chunk_size))
        chunk_layout.addWidget(chunk_label)
        chunk_layout.addWidget(chunk_input)
        layout.addLayout(chunk_layout)

        overlap_layout = QHBoxLayout()
        overlap_label = QLabel("Overlap:")
        overlap_input = QLineEdit(str(self.overlap))
        overlap_layout.addWidget(overlap_label)
        overlap_layout.addWidget(overlap_input)
        layout.addLayout(overlap_layout)

        fs_range_layout = QHBoxLayout()
        fs_range_label = QLabel("Frequency Range:")

        fs_min_label = QLabel("Min:")
        fs_min_input = QLineEdit(str(self.fs_range[0]))
        fs_max_label = QLabel("Max:")
        fs_max_input = QLineEdit(str(self.fs_range[1]))

        fs_range_layout.addWidget(fs_range_label)
        fs_range_layout.addWidget(fs_min_label)
        fs_range_layout.addWidget(fs_min_input)
        fs_range_layout.addWidget(fs_max_label)
        fs_range_layout.addWidget(fs_max_input)

        layout.addLayout(fs_range_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            try:
                chunk_size = int(chunk_input.text())
                overlap = int(overlap_input.text())
                fs_range = (float(fs_min_input.text()), float(fs_max_input.text()))

                self.chunk_size = chunk_size
                self.overlap = overlap
                self.fs_range = fs_range
                self.hide_spectrograms()
                self.show_spectrograms()
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Invalid input values. Please enter valid numbers.",
                )

    def show_DBSCAN_settings(self):
        menu_item_rect = self.editMenu.actionGeometry(self.setDBSCANSettingsAction)
        global_pos = self.editMenu.mapToGlobal(menu_item_rect.topRight())
        self.db_scan_settings_widget.move(global_pos)

        self.db_scan_settings_widget.show()

    def show_spectrogram_settings_widget(self):
        menu_item_rect = self.editMenu.actionGeometry(self.setSpectrogramSettingsAction)
        global_pos = self.editMenu.mapToGlobal(menu_item_rect.topRight())
        self.spectrogram_settings_widget.move(global_pos)

        self.spectrogram_settings_widget.show()

    def show_spectrograms(self):
        for i in range(4):
            if self.plotted_channels[i] is not None:
                eeg_data = self.data[
                    self.plotted_channels[i].row,
                    self.plotted_channels[i].col,
                ]["signal"]

                print(f"Creating spectrogram for channel {i + 1}")

                f, t, Sxx = spectrogram(
                    eeg_data,
                    fs=self.sampling_rate,
                    window="hann",
                    nperseg=self.chunk_size,
                    noverlap=self.overlap,
                    nfft=self.chunk_size,
                    scaling="density",
                    mode="psd",
                )

                Sxx_db = 10 * np.log10(Sxx)

                freq_mask = (f >= self.fs_range[0]) & (f <= self.fs_range[1])
                Sxx_db = Sxx_db[freq_mask, :]

                cmap = pg.colormap.get("inferno")
                lut = cmap.getLookupTable()

                img = pg.ImageItem()
                img.setLookupTable(lut)
                img.setLevels([np.min(Sxx_db), np.max(Sxx_db)])
                img.setImage(Sxx_db.T, autoLevels=False)

                x_range = (self.time_vector[0], self.time_vector[-1])
                y_range = (min(eeg_data) + max(eeg_data), 2 * max(eeg_data))
                img.setRect(
                    QRectF(
                        x_range[0],
                        y_range[0],
                        x_range[1] - x_range[0],
                        y_range[1] - y_range[0],
                    )
                )

                self.graph_widget.plot_widgets[i].addItem(img)

                img.setZValue(-1)

    def hide_spectrograms(self):
        for i in range(4):
            for item in self.graph_widget.plot_widgets[i].items():
                if isinstance(item, pg.ImageItem):
                    self.graph_widget.plot_widgets[i].removeItem(item)

    def toggle_antialiasing(self, checked):
        pg.setConfigOptions(antialias=checked)
        self.update_grid()

    def toggle_spectrogram(self, checked):
        if checked:
            self.show_spectrograms()
        else:
            self.hide_spectrograms()

    def toggle_prop_lines(self, checked):
        self.do_show_prop_lines = checked
        if checked:
            self.show_prop_lines()
        else:
            self.hide_prop_lines()

    def toggle_playheads(self, checked):
        self.do_show_playheads = checked
        self.update_grid()

    def toggle_cpp_mode(self, state):
        self.use_cpp = state == Qt.Checked
        self.set_widgets_enabled()

    def toggle_lines(self, checked):
        self.do_show_spread_lines = checked
        if checked:
            self.show_spread_lines()
        else:
            self.hide_spread_lines()

    def set_peak_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Peak Settings")
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumSize(300, 200)

        layout = QVBoxLayout(dialog)

        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Peak Threshold:")
        threshold_input = QLineEdit(str(self.n_std_dev))
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(threshold_input)
        layout.addLayout(threshold_layout)

        distance_layout = QHBoxLayout()
        distance_label = QLabel("Distance:")
        distance_input = QLineEdit(str(self.distance))
        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(distance_input)
        layout.addLayout(distance_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            try:
                n_std_dev = int(threshold_input.text())
                distance = int(distance_input.text())

                self.n_std_dev = n_std_dev
                self.distance = distance
                self.signal_analyzer.n_std_dev = n_std_dev
                self.signal_analyzer.distance = distance
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Invalid input values. Please enter valid numbers.",
                )

    def show_statistics_widgets(self):
        while self.stats_tab_layout.count():
            item = self.stats_tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for group in self.groups:
            card_widget = QWidget()
            card_layout = QHBoxLayout(card_widget)

            splitter = QSplitter(Qt.Horizontal)

            image_raster_widget = QWidget()
            image_raster_layout = QHBoxLayout(image_raster_widget)

            image_label = QLabel()
            pixmap = QPixmap(group.image)
            image_label.setPixmap(
                pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            image_raster_layout.addWidget(image_label)

            raster_plot_widget = pg.PlotWidget()
            raster_plot_widget.setAspectLocked(False)
            raster_plot_widget.setBackground("w")
            image_raster_layout.addWidget(raster_plot_widget)

            group_data = np.empty_like(self.data)
            group_data.fill(None)
            for row, col in group.channels:
                group_data[row - 1, col - 1] = self.data[row - 1, col - 1]
            group_raster_plot = RasterPlot(
                group_data,
                self.sampling_rate,
                group.channels,
                self.raster_downsample_factor,
            )
            group_raster_plot.generate_raster()
            group_raster_plot.create_raster_plot(raster_plot_widget)

            splitter.addWidget(image_raster_widget)

            stats_widget = QWidget()
            stats_layout = QVBoxLayout(stats_widget)

            group_name_label = QLabel(f"Group: {group.number}")
            stats_layout.addWidget(group_name_label)

            channel_count_label = QLabel(f"Number of Channels: {len(group.channels)}")
            stats_layout.addWidget(channel_count_label)

            seizure_count = 0
            average_seizure_duration = 0
            average_seizure_strength = 0

            se_count = 0
            average_se_duration = 0
            average_se_strength = 0
            for row, col in group.channels:
                seizures = self.data[row - 1, col - 1]["SzTimes"]
                se = self.data[row - 1, col - 1]["SETimes"]
                if seizures.size > 0:
                    seizure_count += seizures.shape[0]
                if se.size > 0:
                    se_count += se.shape[0]

                for start, stop, strength in seizures:
                    average_seizure_duration += stop - start
                    average_seizure_strength += strength
                for start, stop, strength in se:
                    average_se_duration += stop - start
                    average_se_strength += strength

            if seizure_count > 0:
                average_seizure_duration /= seizure_count
                average_seizure_strength /= seizure_count
            else:
                average_seizure_duration = 0
                average_seizure_strength = 0

            if se_count > 0:
                average_se_duration /= se_count
                average_se_strength /= se_count
            else:
                average_se_duration = 0
                average_se_strength = 0

            seizure_count_label = QLabel(f"Number of Seizures: {seizure_count}")
            stats_layout.addWidget(seizure_count_label)

            average_seizure_count = seizure_count / len(group.channels)
            average_seizure_count_label = QLabel(
                f"Average Seizures per Channel: {average_seizure_count:.2f}"
            )
            stats_layout.addWidget(average_seizure_count_label)

            average_seizure_duration_label = QLabel(
                f"Average Seizure Duration: {average_seizure_duration:.2f}"
            )
            stats_layout.addWidget(average_seizure_duration_label)

            average_seizure_strength_label = QLabel(
                f"Average Seizure Strength: {average_seizure_strength:.2f}"
            )
            stats_layout.addWidget(average_seizure_strength_label)

            se_count_label = QLabel(f"Number of SEs: {se_count}")
            stats_layout.addWidget(se_count_label)

            average_se_count = se_count / len(group.channels)
            average_se_count_label = QLabel(
                f"Average SEs per Channel: {average_se_count:.2f}"
            )
            stats_layout.addWidget(average_se_count_label)

            average_se_duration_label = QLabel(
                f"Average SE Duration: {average_se_duration:.2f}"
            )
            stats_layout.addWidget(average_se_duration_label)

            average_se_strength_label = QLabel(
                f"Average SE Strength: {average_se_strength:.2f}"
            )
            stats_layout.addWidget(average_se_strength_label)

            splitter.addWidget(stats_widget)

            card_layout.addWidget(splitter)

            scroll_layout.addWidget(card_widget)

        scroll_area.setWidget(scroll_widget)
        self.stats_tab_layout.addWidget(scroll_area)

    def update_tab_layout(self, index):
        if not self.is_recording_video:
            print(f"Updating tab layout: {index}")
            if self.main_tab_widget.currentWidget() == self.main_tab:
                if self.left_pane:
                    self.left_pane.setVisible(True)
                if self.right_pane:
                    self.right_pane.setVisible(True)
                if self.tab_widget:
                    if self.tab_widget.currentIndex() == 0:
                        self.grid_widget.setVisible(True)
                        self.second_plot_widget.setVisible(False)
                        self.opacity_label.setVisible(True)
                        self.opacity_slider.setVisible(True)
                    elif self.tab_widget.currentIndex() == 1:
                        self.grid_widget.setVisible(False)
                        self.second_plot_widget.setVisible(True)
                        self.opacity_label.setVisible(False)
                        self.opacity_slider.setVisible(False)
            elif self.main_tab_widget.currentWidget() == self.stats_tab:
                self.left_pane.setVisible(False)
                self.right_pane.setVisible(False)
                self.show_statistics_widgets()

    def clear_plots(self):
        if self.enhanced_region is not None:
            self.clear_enhanced_view()
        for i in range(4):
            if self.plotted_channels[i] is not None:
                self.plotted_channels[i].plotted_state = False
                self.plotted_channels[i].plotted_shape = None
                self.plotted_channels[i].update()
            if i in self.graph_widget.region_plots:
                self.graph_widget.plot_widgets[i].removeItem(
                    self.graph_widget.region_plots[i]
                )
            self.graph_widget.plots[i].setData([], [])
            self.graph_widget.x_data[i] = None
            self.graph_widget.y_data[i] = None
            self.graph_widget.plot_widgets[i].setTitle("Select Channel")
            self.graph_widget.plot_widgets[i].setLabel("bottom", "sec")
            self.graph_widget.plot_widgets[i].setLabel("left", "mV")
            for item in self.graph_widget.plot_widgets[i].items():
                if isinstance(
                    item, (pg.LinearRegionItem, pg.ScatterPlotItem, pg.ImageItem)
                ):
                    self.graph_widget.plot_widgets[i].removeItem(item)

        self.plotted_channels = [None] * 4
        self.graph_widget.region_plots.clear()
        self.grid_widget.update()
        self.current_region = None
        self.update_raster_plotted_channels()

    def toggle_order(self, state):
        if state == Qt.Checked:
            self.show_seizure_order()
        else:
            self.hide_seizure_order()

    def show_seizure_order(self):
        if self.data is None:
            return

        self.hide_seizure_order()

        index = self.order_combo.currentIndex()
        order = None

        if index == 1:
            order = sorted(
                self.active_channels,
                key=lambda x: self.raster_plot.get_first_seizure_time(
                    x[0] - 1, x[1] - 1
                ),
            )
        elif index == 2:
            order = sorted(
                self.active_channels,
                key=lambda x: self.raster_plot.get_first_se_time(x[0] - 1, x[1] - 1),
            )

        if order:
            for i, (row, col) in enumerate(order[: self.order_amount], start=1):
                cell = self.grid_widget.cells[row - 1][col - 1]
                cell.setText(str(i))

    def hide_seizure_order(self):
        print("Hiding seizure order")
        for row in range(self.grid_widget.rows):
            for col in range(self.grid_widget.cols):
                cell = self.grid_widget.cells[row][col]
                cell.setText("")

    def set_raster_downsample(self):
        downsample_factor, ok = QInputDialog.getInt(
            self,
            "Set Raster Downsample Factor",
            "Factor:",
            self.raster_downsample_factor,
        )

        if ok:
            if downsample_factor < 1:
                downsample_factor = 1
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Downsample factor must be greater than 0.")
                msg.setWindowTitle("Invalid Downsample Factor")
                msg.exec_()

            self.raster_downsample_factor = downsample_factor

    def update_raster_plotted_channels(self):
        if self.raster_plot is not None:
            raster_plotted_channels = []
            for i in range(4):
                if self.plotted_channels[i] is not None:
                    row, col = (
                        self.plotted_channels[i].row + 1,
                        self.plotted_channels[i].col + 1,
                    )
                    raster_plotted_channels.append((row, col))
            self.raster_plot.set_plotted_channels(raster_plotted_channels)

    def set_raster_order(self, index):
        if self.raster_plot is None:
            self.raster_plot = RasterPlot(
                self.data,
                self.sampling_rate,
                self.active_channels,
                self.raster_downsample_factor,
            )
            self.raster_plot.set_main_window(self)
        if index == 0:
            self.raster_plot.set_raster_order("default")
            self.show_order_checkbox.setCheckState(False)
            self.show_order_checkbox.setEnabled(False)
        elif index == 1:
            self.raster_plot.set_raster_order("seizure")
            self.show_order_checkbox.setEnabled(True)
        elif index == 2:
            self.raster_plot.set_raster_order("SE")
            self.show_order_checkbox.setEnabled(True)

        self.toggle_order(self.show_order_checkbox.checkState())

        if self.show_order_checkbox.isChecked():
            self.show_seizure_order()
        else:
            self.hide_seizure_order()

        self.update_raster_plotted_channels()

    def update_raster(self):
        if self.updateRasterPlotAction.text() == "Create raster":
            self.updateRasterPlotAction.setText("Update raster")

        if self.raster_plot is None:
            self.raster_plot = RasterPlot(
                self.data,
                self.sampling_rate,
                self.active_channels,
                self.raster_downsample_factor,
            )
            self.raster_plot.set_main_window(self)
        else:
            self.raster_plot.downsample_factor = self.raster_downsample_factor

        self.raster_plot.generate_raster()
        self.raster_plot.create_raster_plot(self.second_plot_widget)

    def update_raster_tooltip(self, pos):
        if self.raster_plot is None:
            return

        self.raster_plot.update_tooltip(pos)

    def set_grid_opacity(self, value):
        self.opacity = value / 100.0
        for row in range(self.grid_widget.rows):
            for col in range(self.grid_widget.cols):
                cell = self.grid_widget.cells[row][col]
                color = cell.brush().color()
                cell.setColor(color, 1, self.opacity)

    def deselect_cell(self):
        if self.selected_channel is not None:
            row, col = self.selected_channel
            self.grid_widget.cells[row][col].clicked_state = False
            self.grid_widget.cells[row][col].update()
            self.selected_channel = None
            self.grid_widget.hide_all_selected_tooltips()

    def mousePressEvent(self, event):
        if not self.grid_widget.underMouse() and not self.is_recording_video:
            self.deselect_cell()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        key_mapping = [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4]
        shape_mapping = ["", "󰔷", "x", ""]
        if event.key() in key_mapping:
            index = key_mapping.index(event.key())
            if self.selected_channel is not None:
                row, col = self.selected_channel
                seizures = self.data[row, col]["SzTimes"]
                se = self.data[row, col]["SETimes"]
                if self.data is not None:
                    if self.plotted_channels[index] is not None:
                        self.plotted_channels[index].plotted_state = False
                        self.plotted_channels[index].plotted_shape = None
                        self.plotted_channels[index].update()
                    self.plotted_channels[index] = self.grid_widget.cells[row][col]
                    self.plotted_channels[index].plotted_state = True
                    self.plotted_channels[index].plotted_shape = shape_mapping[index]
                    self.plotted_channels[index].update()

                    if self.raster_plot is not None:
                        raster_plotted_channels = []
                        for i in range(4):
                            if self.plotted_channels[i] is not None:
                                r_row, r_col = (
                                    self.plotted_channels[i].row + 1,
                                    self.plotted_channels[i].col + 1,
                                )
                                raster_plotted_channels.append((r_row, r_col))
                        self.raster_plot.set_plotted_channels(raster_plotted_channels)

                if self.toggleSpectrogramAction.text() == "Hide spectrogram":
                    self.hide_spectrograms()
                    self.show_spectrograms()

                ignore = int(10 * self.sampling_rate)

                self.graph_widget.plot(
                    self.time_vector[ignore:-ignore],
                    self.data[row, col]["signal"][ignore:-ignore],
                    f"{shape_mapping[index]} Channel ({row + 1}, {col + 1})",
                    "sec",
                    "mV",
                    index,
                    shape_mapping[index],
                    seizures,
                    se,
                )

                if self.current_region is not None:
                    start, stop = self.current_region
                    self.graph_widget.redraw_regions(start, stop, self.plotted_channels)

                self.grid_widget.cells[row][col].clicked_state = False
                self.grid_widget.cells[row][col].selected_tooltip.hide()
                self.grid_widget.cells[row][col].update()
                self.grid_widget.selected_channel = None
        else:
            if event.key() == Qt.Key_Shift:
                self.graph_widget.change_view_mode("pan")
            elif event.key() == Qt.Key_C:
                self.clear_enhanced_view()
            elif event.key() == Qt.Key_Right:
                if self.skip_backward_button.isEnabled():
                    self.stepForward()
            elif event.key() == Qt.Key_Left:
                if self.skip_forward_button.isEnabled():
                    self.stepBackward()
            elif event.key() == Qt.Key_Space:
                if self.play_pause_button.isEnabled():
                    self.playPause()
            elif event.key() == Qt.Key_Up:
                if self.speed_combo.currentIndex() < self.speed_combo.count() - 1:
                    self.speed_combo.setCurrentIndex(
                        self.speed_combo.currentIndex() + 1
                    )
            elif event.key() == Qt.Key_Down:
                if self.speed_combo.currentIndex() > 0:
                    self.speed_combo.setCurrentIndex(
                        self.speed_combo.currentIndex() - 1
                    )
            elif event.key() == Qt.Key_L:
                self.lock_to_playhead = not self.lock_to_playhead
                if self.lock_to_playhead:
                    self.lock_plots_to_playhead()
            elif event.key() == Qt.Key_E:
                self.enhance_current_view()
            elif event.key() == Qt.Key_S:
                cursor_pos = QCursor.pos()
                for i in range(4):
                    plot_widget = self.graph_widget.plot_widgets[i]
                    plot_item = plot_widget.getPlotItem()
                    view_box = plot_item.getViewBox()

                    local_pos = plot_widget.mapFromGlobal(cursor_pos)

                    if plot_widget.rect().contains(local_pos):
                        scene_pos = plot_item.mapToScene(local_pos)

                        view_pos = view_box.mapSceneToView(scene_pos)

                        seek_pos = view_pos.x()

                        self.progress_bar.setValue(int(seek_pos * self.sampling_rate))

                        self.update_grid()
                        if self.lock_to_playhead:
                            self.lock_plots_to_playhead()
                        break
            elif event.key() == Qt.Key_F:
                for i in range(4):
                    if self.plotted_channels[i] is not None:
                        row, col = (
                            self.plotted_channels[i].row,
                            self.plotted_channels[i].col,
                        )
                        volt_signal = self.data[row, col]["signal"]
                        start, stop = self.graph_widget.plot_widgets[i].viewRange()[0]

                        peak_x, peak_y, discharge_start_x, discharge_start_y = (
                            self.signal_analyzer.analyze_signal(
                                volt_signal, start, stop
                            )
                        )

                        for item in self.graph_widget.plot_widgets[i].items():
                            if isinstance(item, pg.ScatterPlotItem):
                                self.graph_widget.plot_widgets[i].removeItem(item)

                        peak_plot = pg.ScatterPlotItem(
                            x=peak_x,
                            y=peak_y,
                            symbol="o",
                            size=5,
                            brush=pg.mkBrush(color=(255, 0, 0)),
                            pen=pg.mkPen(color=(255, 0, 0), width=STROKE_WIDTH),
                        )
                        self.graph_widget.plot_widgets[i].addItem(peak_plot)

                        discharge_plot = pg.ScatterPlotItem(
                            x=discharge_start_x,
                            y=discharge_start_y,
                            symbol="o",
                            size=8,
                            brush=pg.mkBrush(color=(255, 165, 0)),
                            pen=pg.mkPen(color=(255, 165, 0), width=STROKE_WIDTH),
                        )
                        self.graph_widget.plot_widgets[i].addItem(discharge_plot)

            elif event.key() == Qt.Key_B:
                self.set_custom_region()
            elif event.key() == Qt.Key_A:
                self.find_discharges()
            elif event.key() == Qt.Key_R:
                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.draw_seizures(
                    self.grid_widget.scene, cell_width, cell_height
                )
            elif event.key() == Qt.Key_H:
                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.draw_seizures_time(
                    self.grid_widget.scene, cell_width, cell_height
                )
            elif event.key() == Qt.Key_J:
                rows, cols = 64, 64
                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.create_heatmap(
                    self.grid_widget.scene, cell_width, cell_height, rows, cols
                )
            elif event.key() == Qt.Key_K:
                rows, cols = 64, 64
                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.create_continuous_heatmap(
                    self.grid_widget.scene, cell_width, cell_height, rows, cols
                )
            elif event.key() == Qt.Key_G:
                self.auto_analyze()
            elif event.key() == Qt.Key_T:
                if self.is_auto_analyzing:
                    self.is_auto_analyzing = False
                    self.cluster_tracker.seizure_graphics_items.clear()
                    self.cluster_tracker.seizures.clear()
            elif event.key() == Qt.Key_M:
                current_time = self.progress_bar.value() / self.sampling_rate
                self.markers.append(current_time)
                self.progress_bar.setMarkers(self.markers)
                print(f"Added marker at {current_time}")

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.graph_widget.change_view_mode("rect")
        elif event.key() == Qt.Key_F:
            print("Clearing peaks")
            for i in range(4):
                if self.plotted_channels[i] is not None:
                    for item in self.graph_widget.plot_widgets[i].items():
                        if isinstance(item, pg.ScatterPlotItem):
                            self.graph_widget.plot_widgets[i].removeItem(item)
        elif event.key() in [Qt.Key_R, Qt.Key_H, Qt.Key_J, Qt.Key_K]:
            self.cluster_tracker.clear_plot(self.grid_widget.scene)

    def set_custom_region(self):
        print("Setting custom region")
        start, stop = self.graph_widget.plot_widgets[0].viewRange()[0]
        self.custom_region = (start, stop)

    def terminate_auto_analysis(self):
        self.is_auto_analyzing = False
        print("Auto-analysis terminated by user")

    def load_discharges(self):
        print("Loading discharges")

        with h5py.File(self.file_path, "r") as f:
            tracked_discharges_group = f["tracked_discharges"]
            timeranges = list(tracked_discharges_group.keys())

            time_range, ok = QInputDialog.getItem(
                self,
                "Select Time Range",
                "Time Range:",
                timeranges,
                0,
                False,
            )

            if ok:
                timerange_group = tracked_discharges_group[time_range]

                discharge_groups = [
                    key
                    for key in timerange_group.keys()
                    if key.startswith("discharge_")
                ]

                for discharge_key in discharge_groups:
                    discharge_group = timerange_group[discharge_key]

                    start_point = discharge_group["start_point"][:]
                    end_point = discharge_group["end_point"][:]
                    start_time = float(discharge_group["start_time"][()])
                    end_time = float(discharge_group["end_time"][()])
                    duration_s = float(discharge_group["duration"][()])
                    length_mm = float(discharge_group["length"][()])
                    avg_speed = float(discharge_group["avg_speed"][()])
                    points = discharge_group["points"][:]
                    time_since_last_discharge = float(
                        discharge_group["time_since_last_discharge"][()]
                    )

                    seizure = {
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration_s * 1000,
                        "length": length_mm,
                        "avg_speed": avg_speed,
                        "points": points.tolist(),
                        "start_point": start_point.tolist(),
                        "end_point": end_point.tolist(),
                        "time_since_last_discharge": time_since_last_discharge,
                    }

                    self.cluster_tracker.seizures.append(seizure)

    def auto_analyze(self):
        if self.custom_region is None or self.plotted_channels[0] is None:
            return

        self.togglePropLinesAction.setChecked(True)
        self.toggle_prop_lines(True)

        self.cluster_tracker.seizures.clear()
        self.cluster_tracker.seizure_graphics_items.clear()
        self.cluster_tracker.last_seizure = None
        start, stop = self.custom_region
        row, col = self.plotted_channels[0].row, self.plotted_channels[0].col
        discharges_x, _ = self.discharges[row, col]

        self.current_discharge_index = 0
        self.discharges_to_analyze = [x for x in discharges_x if start <= x <= stop]

        if not self.discharges_to_analyze:
            print("No discharges to analyze in the selected region")
            return

        self.is_auto_analyzing = True
        self.analyze_next_discharge()

    def analyze_next_discharge(self):
        if not self.is_auto_analyzing or self.current_discharge_index >= len(
            self.discharges_to_analyze
        ):
            if self.is_auto_analyzing:
                print("Auto-analysis complete")

                self.cluster_tracker.save_seizures_to_hdf(
                    self.file_path, *self.custom_region
                )
            self.is_auto_analyzing = False
            return

        discharge_x = self.discharges_to_analyze[self.current_discharge_index]
        print(f"Analyzing discharge at {discharge_x}")
        discharge_index = int(discharge_x * self.sampling_rate)
        start_index = max(0, discharge_index - int(0.1 * self.sampling_rate))
        end_index = min(
            len(self.time_vector) - 1, discharge_index + int(0.15 * self.sampling_rate)
        )

        self.progress_bar.setValue(start_index)
        self.update_grid()
        if self.lock_to_playhead:
            self.lock_plots_to_playhead()

        QTimer.singleShot(50, lambda: self.continue_analysis(end_index))

    def continue_analysis(self, end_index):
        if not self.is_auto_analyzing:
            return

        current_index = self.progress_bar.value()
        if current_index < end_index:
            self.progress_bar.setValue(current_index + 1)
            self.update_grid()
            if self.lock_to_playhead:
                self.lock_plots_to_playhead()
            QTimer.singleShot(5, lambda: self.continue_analysis(end_index))
        else:
            self.current_discharge_index += 1
            QTimer.singleShot(50, self.analyze_next_discharge)

    def on_cell_clicked(self, row, col):
        if self.selected_channel:
            prev_row, prev_col = self.selected_channel
            prev_cell = self.grid_widget.cells[prev_row][prev_col]
            prev_cell.clicked_state = False
            prev_cell.update()
            prev_cell.selected_tooltip.hide()
            prev_cell.hover_tooltip.hide()
        self.selected_channel = (row, col)

    def set_widgets_enabled(self):
        if self.file_path is not None and (self.engine_started or self.use_cpp):
            self.run_button.setEnabled(True)
            self.view_button.setEnabled(True)
        else:
            self.run_button.setEnabled(False)
            self.view_button.setEnabled(False)

        if self.data is not None:
            self.clear_button.setEnabled(True)
            self.skip_backward_button.setEnabled(True)
            self.prev_frame_button.setEnabled(True)
            self.play_pause_button.setEnabled(True)
            self.next_frame_button.setEnabled(True)
            self.skip_forward_button.setEnabled(True)
            self.progress_bar.setEnabled(True)
            self.speed_combo.setEnabled(True)
            self.order_combo.setEnabled(True)
            self.saveGridAction.setEnabled(True)
            self.createVideoAction.setEnabled(True)
            self.saveChannelPlotsAction.setEnabled(True)
            self.saveMeaWithPlotsAction.setEnabled(True)
            self.updateRasterPlotAction.setEnabled(True)
            self.toggleLinesAction.setEnabled(True)
            self.toggleRegionsAction.setEnabled(True)
        else:
            self.clear_button.setEnabled(False)
            self.skip_backward_button.setEnabled(False)
            self.prev_frame_button.setEnabled(False)
            self.play_pause_button.setEnabled(False)
            self.next_frame_button.setEnabled(False)
            self.skip_forward_button.setEnabled(False)
            self.progress_bar.setEnabled(False)
            self.speed_combo.setEnabled(False)
            self.order_combo.setEnabled(False)
            self.saveGridAction.setEnabled(False)
            self.createVideoAction.setEnabled(False)
            self.saveChannelPlotsAction.setEnabled(False)
            self.saveMeaWithPlotsAction.setEnabled(False)
            self.updateRasterPlotAction.setEnabled(False)
            self.show_order_checkbox.setEnabled(False)
            self.toggleLinesAction.setEnabled(False)
            self.toggleRegionsAction.setEnabled(False)

    def openFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            directory="/Users/booka66/Jake-Squared/Sz_SE_Detection/",
            filter="BRW Files (*.brw)",
        )

        if file_path:
            print("Selected file path:", file_path)
            file_path = os.path.normpath(file_path)
            self.file_path = file_path

            try:
                baseName = os.path.basename(file_path)

                self.setWindowTitle(f"BRW Viewer - {baseName}")
                brwFileName = os.path.basename(file_path)
                dateSlice = "_".join(brwFileName.split("_")[:4])
                dateSliceNumber = (
                    dateSlice.split("slice")[0]
                    + "slice"
                    + dateSlice.split("slice")[1][:1]
                )
                imageName = f"{dateSliceNumber}_pic_cropped.jpg"
                print(f"Trying to find image: {imageName}")

                imageFolder = os.path.dirname(file_path)
                image_pattern = os.path.join(
                    imageFolder,
                    f"{dateSliceNumber}_*[pP][iI][cC]_*[cC][rR][oO][pP][pP][eE][dD].jpg",
                )
                image_files = glob.glob(image_pattern, recursive=True)

                if image_files:
                    image_path = image_files[0]
                    self.grid_widget.setBackgroundImage(image_path)
                else:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    msg.setText(f"No image found, manually select image for {baseName}")
                    msg.setWindowTitle("Image Not Found")
                    msg.exec_()

                    imageFileName, _ = QFileDialog.getOpenFileName(
                        self,
                        "Upload Slice Image",
                        "",
                        "Image Files (*.jpg *.png)",
                    )

                    if imageFileName:
                        imageFileName = os.path.normpath(imageFileName)
                        self.grid_widget.setBackgroundImage(imageFileName)
                    else:
                        print("No image selected")

            except Exception as e:
                print(f"Error: {e}")

        self.set_widgets_enabled()

    def get_channels(self):
        with h5py.File(self.file_path, "r") as f:
            recElectrodeList = f["/3BRecInfo/3BMeaStreams/Raw/Chs"]
            rows = recElectrodeList["Row"][()]
            cols = recElectrodeList["Col"][()]
        return rows, cols

    def create_grid(self):
        for row in self.grid_widget.cells:
            for cell in row:
                cell.setColor(BACKGROUND, 1, self.opacity)
        for row, col in self.active_channels:
            self.grid_widget.cells[row - 1][col - 1].setColor(ACTIVE, 1, self.opacity)

    def get_min_max_strengths(self):
        self.min_strength = None
        self.max_strength = None

        for row, col in self.active_channels:
            seizure_times = self.data[row - 1, col - 1]["SzTimes"]
            se_times = self.data[row - 1, col - 1]["SETimes"]

            if seizure_times.size == 0 and se_times.size == 0:
                continue

            if seizure_times.size > 0:
                if seizure_times.ndim == 1:
                    seizure_times = seizure_times.reshape(1, -1)
                elif seizure_times.ndim == 0:
                    seizure_times = seizure_times.reshape(1, 1)
            else:
                seizure_times = np.empty((0, 3))

            if se_times.size > 0:
                if se_times.ndim == 1:
                    se_times = se_times.reshape(1, -1)
                elif se_times.ndim == 0:
                    se_times = se_times.reshape(1, 1)
            else:
                se_times = np.empty((0, 3))

            times = np.concatenate((seizure_times, se_times), axis=0)

            for timerange in times:
                if len(timerange) >= 3:
                    start, stop, strength = timerange[:3]
                    if self.min_strength is None or strength < self.min_strength:
                        self.min_strength = strength
                    if self.max_strength is None or strength > self.max_strength:
                        self.max_strength = strength

    def normalize_strength(self, strength):
        strength = float(strength)
        return math.sqrt(
            (strength - self.min_strength) / (self.max_strength - self.min_strength)
        )

    def save_discharges_to_hdf5(self, row, col, start_time, stop_time):
        with h5py.File(self.file_path, "a") as f:
            if len(self.discharges[(row, col)][0]) == 0:
                return
            if "Discharges" not in f:
                f.create_group("Discharges")
            discharge_group = f["Discharges"]

            timeframe_group_name = f"Timeframe_{start_time:.2f}_{stop_time:.2f}"
            if timeframe_group_name not in discharge_group:
                timeframe_group = discharge_group.create_group(timeframe_group_name)
            else:
                timeframe_group = discharge_group[timeframe_group_name]

            channel_group_name = f"{row}_{col}"
            if channel_group_name not in timeframe_group:
                channel_group = timeframe_group.create_group(channel_group_name)
            else:
                channel_group = timeframe_group[channel_group_name]

            channel_group.create_dataset(
                "DischargeTimes", data=self.discharges[(row, col)][0]
            )
            channel_group.create_dataset(
                "DischargeStrengths", data=self.discharges[(row, col)][1]
            )

            channel_group.attrs["start_time"] = start_time
            channel_group.attrs["stop_time"] = stop_time

    def find_discharges(self):
        self.set_custom_region()
        start, stop = self.custom_region
        for i, (row, col) in enumerate(self.active_channels):
            volt_signal = self.data[row - 1, col - 1]["signal"]
            peak_x, peak_y, discharge_start_x, discharge_start_y = (
                self.signal_analyzer.analyze_signal(volt_signal, start, stop)
            )

            self.discharges[(row - 1, col - 1)] = (
                discharge_start_x,
                discharge_start_y,
            )

        for i in range(4):
            if self.plotted_channels[i] is not None:
                row, col = (
                    self.plotted_channels[i].row,
                    self.plotted_channels[i].col,
                )

                discharge_start_x, discharge_start_y = self.discharges[(row, col)]

                for item in self.graph_widget.plot_widgets[i].items():
                    if isinstance(item, pg.ScatterPlotItem):
                        self.graph_widget.plot_widgets[i].removeItem(item)

                discharge_plot = pg.ScatterPlotItem(
                    x=discharge_start_x,
                    y=discharge_start_y,
                    symbol="o",
                    size=8,
                    brush=pg.mkBrush(color=(255, 165, 0)),
                    pen=pg.mkPen(color=(255, 165, 0), width=STROKE_WIDTH),
                )
                self.graph_widget.plot_widgets[i].addItem(discharge_plot)

    def update_grid(self):
        current_time = self.progress_bar.value() / self.sampling_rate

        if self.do_show_prop_lines and self.custom_region:
            start, stop = self.custom_region
            newly_discharged_cells = []
            cells_to_remove = []
            discharged_cells = []
            for row, col in self.active_channels:
                if (row - 1, col - 1) in self.discharges:
                    discharge_times, _ = self.discharges[(row - 1, col - 1)]
                    discharge_found = False
                    for discharge_time in discharge_times:
                        if (
                            start <= discharge_time <= stop
                            and abs(discharge_time - current_time) < self.bin_size
                        ):
                            newly_discharged_cells.append((row, col))
                            discharged_cells.append((row, col))
                            discharge_found = True
                            break
                    if not discharge_found and (row, col) in self.prop_cells:
                        cells_to_remove.append((row, col))

            if discharged_cells:
                X = np.array(discharged_cells)
                db = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(X)
                labels = db.labels_

                for item in self.centroids:
                    self.grid_widget.scene.removeItem(item)
                self.centroids.clear()

                unique_labels = set(labels)
                centroids = []
                for label in unique_labels:
                    if label != -1:
                        cluster_points = X[labels == label]
                        centroid = np.mean(cluster_points, axis=0)
                        centroids.append(centroid)

                        centroid_row, centroid_col = centroid
                        centroid_item = QGraphicsEllipseItem(0, 0, 10, 10)
                        centroid_item.setBrush(Qt.red)
                        centroid_item.setPos(
                            centroid_col * self.grid_widget.cells[0][0].rect().width()
                            - 5,
                            centroid_row * self.grid_widget.cells[0][0].rect().height()
                            - 5,
                        )
                        self.grid_widget.scene.addItem(centroid_item)
                        self.centroids.append(centroid_item)

                self.cluster_tracker.update(centroids, current_time)

                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.draw_cluster_lines(
                    self.grid_widget.scene, cell_width, cell_height
                )

                cluster_stats = self.cluster_tracker.get_cluster_stats()
                self.cluster_legend.update(cluster_stats)
            else:
                self.cluster_tracker.update([], current_time)
                self.cluster_legend.update([])
                cell_width = self.grid_widget.cells[0][0].rect().width()
                cell_height = self.grid_widget.cells[0][0].rect().height()
                self.cluster_tracker.draw_cluster_lines(
                    self.grid_widget.scene, cell_width, cell_height
                )

            for row, col in newly_discharged_cells:
                if (row, col) not in self.prop_cells:
                    self.draw_prop_arrows(row, col)
                    self.prop_cells.append((row, col))

            for row, col in cells_to_remove:
                self.remove_prop_arrows(row, col)
                self.prop_cells.remove((row, col))
        else:
            # If prop lines are not being shown or there's no custom region, remove all prop arrows
            for row, col in list(self.prop_cells):
                self.remove_prop_arrows(row, col)
            self.prop_cells.clear()

            for item in self.centroids:
                self.grid_widget.scene.removeItem(item)
            self.centroids.clear()

            self.cluster_tracker.update([], current_time)
            cell_width = self.grid_widget.cells[0][0].rect().width()
            cell_height = self.grid_widget.cells[0][0].rect().height()
            self.cluster_tracker.draw_cluster_lines(
                self.grid_widget.scene, cell_width, cell_height
            )

        if self.do_show_spread_lines:
            newly_seized_cells = []
            newly_se_cells = []
            cells_to_remove = []
        if self.min_strength is None or self.max_strength is None:
            self.get_min_max_strengths()

        rows, cols = zip(*self.active_channels)
        cells = [
            self.grid_widget.cells[row - 1][col - 1]
            for row, col in self.active_channels
        ]
        signals = [
            self.data[row - 1, col - 1]["signal"] for row, col in self.active_channels
        ]
        se_times_list = [
            self.data[row - 1, col - 1]["SETimes"] for row, col in self.active_channels
        ]
        seizure_times_list = [
            self.data[row - 1, col - 1]["SzTimes"] for row, col in self.active_channels
        ]

        if self.do_show_false_color_map:
            bin_start = int((current_time - self.bin_size) * self.sampling_rate)
            bin_end = int((current_time + self.bin_size) * self.sampling_rate)
            bin_voltages = [signal[bin_start:bin_end] for signal in signals]

            if self.overall_min_voltage is None or self.overall_max_voltage is None:
                ignore_samples = int(10 * self.sampling_rate)
                trimmed_signals = [
                    signal[ignore_samples:-ignore_samples] for signal in signals
                ]
                self.overall_min_voltage = min(
                    min(signal) for signal in trimmed_signals
                )
                self.overall_max_voltage = max(
                    max(signal) for signal in trimmed_signals
                )

            voltage_ranges = []
            for voltages in bin_voltages:
                if voltages.size > 0:
                    min_voltage = np.min(voltages)
                    max_voltage = np.max(voltages)
                    normalized_range = (max_voltage - min_voltage) / (
                        self.overall_max_voltage - self.overall_min_voltage
                    )
                    voltage_ranges.append(normalized_range)
                else:
                    voltage_ranges.append(None)

            colors = [
                self.voltage_range_to_color(voltage_range)
                if voltage_range is not None
                else ACTIVE
                for voltage_range in voltage_ranges
            ]
        else:
            colors = [ACTIVE] * len(self.active_channels)

        found_se = [False] * len(self.active_channels)
        found_seizure = [False] * len(self.active_channels)

        for i, (row, col) in enumerate(self.active_channels):
            se_times = np.array(se_times_list[i])
            seizure_times = np.array(seizure_times_list[i])

            if self.do_show_events:
                if se_times.size > 0:
                    se_mask = (se_times[:, 0] <= current_time) & (
                        current_time <= se_times[:, 1]
                    )
                    if np.any(se_mask):
                        se_index = np.where(se_mask)[0][0]
                        strength = self.normalize_strength(se_times[se_index, 2])
                        if self.do_show_false_color_map:
                            se_color = self.blend_colors(colors[i], SE, strength)
                        else:
                            se_color = SE
                        cells[i].setColor(se_color, strength**0.25, self.opacity)
                        found_se[i] = True
                        if (
                            self.do_show_spread_lines
                            and (row, col) not in self.seized_cells
                        ):
                            newly_se_cells.append((row, col))

                if not found_se[i] and seizure_times.size > 0:
                    seizure_mask = (seizure_times[:, 0] <= current_time) & (
                        current_time <= seizure_times[:, 1]
                    )
                    if np.any(seizure_mask):
                        seizure_index = np.where(seizure_mask)[0][0]
                        strength = self.normalize_strength(
                            seizure_times[seizure_index, 2]
                        )
                        if self.do_show_false_color_map:
                            seizure_color = self.blend_colors(
                                colors[i], SEIZURE, strength
                            )
                        else:
                            seizure_color = SEIZURE
                        cells[i].setColor(seizure_color, strength, self.opacity)
                        found_seizure[i] = True
                        if (
                            self.do_show_spread_lines
                            and (row, col) not in self.seized_cells
                        ):
                            newly_seized_cells.append((row, col))

            if not found_se[i] and not found_seizure[i]:
                cells[i].setColor(colors[i], 1, self.opacity)
                if self.do_show_spread_lines and (row, col) in self.seized_cells:
                    cells_to_remove.append((row, col))

        if self.do_show_spread_lines:
            for row, col in newly_seized_cells:
                self.seized_cells.append((row, col))
                self.draw_spread_arrows(row, col, "seizure")
            for row, col in newly_se_cells:
                self.seized_cells.append((row, col))
                self.draw_spread_arrows(row, col, "SE")
            for row, col in cells_to_remove:
                self.seized_cells.remove((row, col))
                self.remove_seizure_arrows(row, col)

        self.grid_widget.update()

    def blend_colors(self, color1, color2, strength):
        r1, g1, b1, _ = color1.getRgb()
        r2, g2, b2, _ = color2.getRgb()

        blended_color = QColor(
            int(r1 + (r2 - r1) * 0.5),
            int(g1 + (g2 - g1) * 0.5),
            int(b1 + (b2 - b1) * 0.5),
        )

        return blended_color

    def voltage_range_to_color(self, normalized_range):
        if normalized_range is None:
            return ACTIVE
        hue = int((1 - normalized_range) * 240)
        saturation = 255
        value = 255 if normalized_range > 0 else 128
        return QColor.fromHsv(hue, saturation, value)

    def remove_seizure_arrows(self, row, col):
        arrows_to_remove = []
        for arrow_item in self.arrow_items:
            if arrow_item["end_cell"] == (row, col):
                self.grid_widget.scene.removeItem(arrow_item["arrow"])
                self.grid_widget.scene.removeItem(arrow_item["arrow_head"])
                arrows_to_remove.append(arrow_item)
            elif arrow_item["start_cell"] == (row, col):
                self.grid_widget.scene.removeItem(arrow_item["arrow"])
                self.grid_widget.scene.removeItem(arrow_item["arrow_head"])
                arrows_to_remove.append(arrow_item)

        for arrow_item in arrows_to_remove:
            self.arrow_items.remove(arrow_item)

    def redraw_arrows(self):
        for arrow_item in self.arrow_items + self.prop_arrow_items:
            start_cell = self.grid_widget.cells[arrow_item["start_cell"][0]][
                arrow_item["start_cell"][1]
            ]
            end_cell = self.grid_widget.cells[arrow_item["end_cell"][0]][
                arrow_item["end_cell"][1]
            ]

            cell_width = start_cell.rect().width()
            cell_height = start_cell.rect().height()

            offset = QPointF(cell_width * 1, cell_height * 1)

            start_center = (
                start_cell.scenePos()
                + QPointF(cell_width / 2, cell_height / 2)
                - offset
            )
            end_center = (
                end_cell.scenePos() + QPointF(cell_width / 2, cell_height / 2) - offset
            )

            arrow_item["arrow"].setLine(QLineF(start_center, end_center))

            angle = math.degrees(
                math.atan2(
                    end_center.y() - start_center.y(), end_center.x() - start_center.x()
                )
            )
            arrow_item["arrow_head"].setRotation(angle)

            arrow_offset = 0.5
            arrow_item["arrow_head"].setPos(
                end_center
                - QPointF(
                    arrow_offset * math.cos(math.radians(angle)),
                    arrow_offset * math.sin(math.radians(angle)),
                )
            )

    def remove_prop_arrows(self, row, col):
        arrows_to_remove = []
        for arrow_item in self.prop_arrow_items:
            if arrow_item["end_cell"] == (row, col) or arrow_item["start_cell"] == (
                row,
                col,
            ):
                self.grid_widget.scene.removeItem(arrow_item["arrow"])
                self.grid_widget.scene.removeItem(arrow_item["arrow_head"])
                arrows_to_remove.append(arrow_item)

        for arrow_item in arrows_to_remove:
            self.prop_arrow_items.remove(arrow_item)

        print(f"Removed propagation arrows for cell ({row}, {col})")

    def print_propagation_state(self):
        print("\nCurrent Propagation State:")
        print(f"do_show_prop_lines: {self.do_show_prop_lines}")
        print(f"custom_region: {self.custom_region}")
        print(f"prop_cells: {self.prop_cells}")
        print(f"prop_arrow_items: {len(self.prop_arrow_items)}")
        print(f"Number of discharges: {len(self.discharges)}")

    def draw_prop_arrows(self, row, col):
        print(f"Drawing propagation arrow for cell ({row}, {col})")
        if len(self.prop_cells) > 1:
            min_distance = float("inf")
            closest_cell = None
            for prop_row, prop_col in self.prop_cells:
                distance = math.sqrt((row - prop_row) ** 2 + (col - prop_col) ** 2)

                if distance < min_distance and distance > 0:
                    min_distance = distance
                    closest_cell = (prop_row, prop_col)

            print(f"Closest cell: {closest_cell}, distance: {min_distance}")

            if closest_cell and min_distance <= 10:
                start_cell = self.grid_widget.cells[closest_cell[0]][closest_cell[1]]
                end_cell = self.grid_widget.cells[row][col]

                cell_width = start_cell.rect().width()
                cell_height = start_cell.rect().height()

                offset = QPointF(cell_width * 1, cell_height * 1)

                start_center = (
                    start_cell.scenePos()
                    + QPointF(cell_width / 2, cell_height / 2)
                    - offset
                )
                end_center = (
                    end_cell.scenePos()
                    + QPointF(cell_width / 2, cell_height / 2)
                    - offset
                )

                arrow = QGraphicsLineItem(QLineF(start_center, end_center))
                arrow.setPen(
                    QPen(PROPAGATION, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                )

                arrow_head = QPolygonF()
                arrow_head << QPointF(0, 0) << QPointF(-6, -5) << QPointF(-6, 5)
                arrow_head_item = QGraphicsPolygonItem(arrow_head)
                arrow_head_item.setBrush(PROPAGATION)
                arrow_head_item.setPen(QPen(PROPAGATION))

                angle = math.degrees(
                    math.atan2(
                        end_center.y() - start_center.y(),
                        end_center.x() - start_center.x(),
                    )
                )
                arrow_head_item.setRotation(angle)

                arrow_offset = 0.5

                arrow_head_item.setPos(
                    end_center
                    - QPointF(
                        arrow_offset * math.cos(math.radians(angle)),
                        arrow_offset * math.sin(math.radians(angle)),
                    )
                )

                self.grid_widget.scene.addItem(arrow)
                self.grid_widget.scene.addItem(arrow_head_item)

                self.prop_arrow_items.append(
                    {
                        "arrow": arrow,
                        "arrow_head": arrow_head_item,
                        "start_cell": closest_cell,
                        "end_cell": (row, col),
                    }
                )

                self.prop_cells.append((row, col))
                print(f"Added new cell to prop_cells: ({row}, {col})")

                if self.do_show_prop_lines:
                    arrow.show()
                    arrow_head_item.show()
                    print("Arrow shown")
                else:
                    arrow.hide()
                    arrow_head_item.hide()
                    print("Arrow hidden")
            else:
                print("No suitable cell found for drawing arrow")
        else:
            print("Not enough cells in prop_cells to draw arrow")

    def draw_spread_arrows(self, row, col, event_type):
        if len(self.seized_cells) > 1:
            min_distance = float("inf")
            max_strength = 0
            closest_cell = None
            for seized_row, seized_col in self.seized_cells[:-1]:
                distance = math.sqrt((row - seized_row) ** 2 + (col - seized_col) ** 2)

                current_strength = self.get_seizure_strength(seized_row, seized_col)

                if distance < min_distance or (
                    distance == min_distance and current_strength > max_strength
                ):
                    min_distance = distance
                    max_strength = current_strength
                    closest_cell = (seized_row, seized_col)

            if closest_cell and min_distance <= 15:
                start_cell = self.grid_widget.cells[closest_cell[0]][closest_cell[1]]
                end_cell = self.grid_widget.cells[row][col]

                cell_width = start_cell.rect().width()
                cell_height = start_cell.rect().height()

                offset = QPointF(cell_width * 1, cell_height * 1)

                start_center = (
                    start_cell.scenePos()
                    + QPointF(cell_width / 2, cell_height / 2)
                    - offset
                )
                end_center = (
                    end_cell.scenePos()
                    + QPointF(cell_width / 2, cell_height / 2)
                    - offset
                )

                arrow = QGraphicsLineItem(QLineF(start_center, end_center))
                if event_type == "SE":
                    arrow_color = SE.darker(150)
                else:
                    TEST = QColor("#fb6f92")
                    arrow_color = TEST
                arrow.setPen(
                    QPen(arrow_color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                )

                arrow_head = QPolygonF()
                arrow_head << QPointF(0, 0) << QPointF(-6, -5) << QPointF(-6, 5)
                arrow_head_item = QGraphicsPolygonItem(arrow_head)
                arrow_head_item.setBrush(arrow_color)
                arrow_head_item.setPen(QPen(arrow_color))

                angle = math.degrees(
                    math.atan2(
                        end_center.y() - start_center.y(),
                        end_center.x() - start_center.x(),
                    )
                )
                arrow_head_item.setRotation(angle)

                arrow_offset = 0.5
                arrow_head_item.setPos(
                    end_center
                    - QPointF(
                        arrow_offset * math.cos(math.radians(angle)),
                        arrow_offset * math.sin(math.radians(angle)),
                    )
                )

                self.grid_widget.scene.addItem(arrow)
                self.grid_widget.scene.addItem(arrow_head_item)

                self.arrow_items.append(
                    {
                        "arrow": arrow,
                        "arrow_head": arrow_head_item,
                        "start_cell": closest_cell,
                        "end_cell": (row, col),
                    }
                )
                if self.do_show_spread_lines:
                    arrow.show()
                    arrow_head_item.show()
                else:
                    arrow.hide()
                    arrow_head_item.hide()

    def get_seizure_strength(self, row, col):
        seizure_times = self.data[row - 1, col - 1]["SzTimes"]
        current_time = self.progress_bar.value() / self.sampling_rate
        for timerange in seizure_times:
            start, stop, strength = timerange
            if start <= current_time <= stop:
                return strength
        return 0

    def run_analysis(self):
        button_clicked = self.sender()
        if button_clicked is not None:
            if button_clicked.text().__contains__("Run"):
                print("Running analysis")
                do_analysis = True
            elif button_clicked.text().__contains__("RAM"):
                print(f"Button text: {button_clicked.text()}")
                print("Running view with low RAM")
                do_analysis = False
            else:
                print("Running view without analysis")
                do_analysis = False

        else:
            do_analysis = False

        try:
            if self.data is not None:
                alert = QMessageBox(self)
                alert.setText(
                    "Loaded analysis will be deleted. Are you sure you would like to continue?"
                )
                alert.setStandardButtons(QMessageBox.Yes | QMessageBox.Abort)
                alert.setIcon(QMessageBox.Warning)
                button = alert.exec()

                if button == QMessageBox.Abort:
                    return
                else:
                    self.graph_widget.update_red_lines(0, self.sampling_rate)
                    self.order_combo.setCurrentIndex(0)
                    self.show_order_checkbox.setCheckState(False)
                    self.toggle_order(self.show_order_checkbox.checkState())
                    self.raster_plot = None
                    self.analysis_thread = AnalysisThread(self)
                    self.analysis_thread.progress_updated.connect(
                        self.loading_dialog.update_progress
                    )
                    self.analysis_thread.analysis_completed.connect(
                        self.on_analysis_completed
                    )
                    self.hide_spread_lines()
                    self.arrow_items = []
                    self.prop_arrow_items = []
                    self.seized_cells = []
                    self.clear_plots()
                    self.min_strength = None
                    self.max_strength = None
                    self.recording_length = None
                    self.time_vector = None
                    del self.data
                    self.data = None
                    self.active_channels = []
                    self.selected_channel = []
                    self.plotted_channels = [None] * 4
                    self.selected_subplot = None
                    self.min_voltage = None
                    self.max_voltage = None
                    self.overall_min_voltage = None
                    self.overall_max_voltage = None
                    self.prop_cells = []
                    self.centroids = []
                    self.cluster_tracker.clear_plot(self.grid_widget.scene)
                    self.cluster_tracker.clear()
                    self.create_grid()
                    self.set_widgets_enabled()
                    gc.collect()

            self.run_button.setEnabled(False)
            self.update()

            available_drives = self.get_available_drives()
            if len(available_drives) > 1:
                drive_dialog = QDialog(self)
                drive_dialog.setWindowTitle("Select Drive")
                drive_layout = QVBoxLayout()

                drive_label = QLabel("Select the drive to store temp_data:")
                drive_layout.addWidget(drive_label)

                drive_combo = QComboBox()
                drive_combo.addItems(available_drives)
                drive_layout.addWidget(drive_combo)

                button_layout = QHBoxLayout()
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(drive_dialog.accept)
                button_layout.addWidget(ok_button)
                cancel_button = QPushButton("Cancel")
                cancel_button.clicked.connect(drive_dialog.reject)
                button_layout.addWidget(cancel_button)

                drive_layout.addLayout(button_layout)
                drive_dialog.setLayout(drive_layout)

                if drive_dialog.exec() == QDialog.Accepted:
                    print("Selected drive:", drive_combo.currentText())
                    selected_drive = drive_combo.currentText()
                    temp_data_path = os.path.join(selected_drive, "temp_data")
                else:
                    temp_data_path = os.path.expanduser("~/temp_data")
            else:
                temp_data_path = os.path.expanduser("~/temp_data")

            print("Temp data path:", temp_data_path)

            with h5py.File(self.file_path, "r") as f:
                channels = f["/3BRecInfo/3BMeaStreams/Raw/Chs"][()]
                num_channels = len(channels)
                print(f"Number of channels: {num_channels}")
                self.loading_dialog.progress_bar.setRange(0, num_channels)
            self.analysis_thread.file_path = self.file_path
            self.analysis_thread.do_analysis = do_analysis
            self.analysis_thread.use_low_ram = (
                True if self.low_ram_checkbox.isChecked() else False
            )
            self.analysis_thread.eng = self.eng
            self.analysis_thread.use_cpp = self.use_cpp
            self.analysis_thread.temp_data_path = temp_data_path
            self.loading_dialog.show()
            self.analysis_thread.start()

        except Exception as e:
            print(f"Error: {e}")

    def get_available_drives(self):
        drives = []
        for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if os.path.exists(f"{drive}:"):
                drives.append(f"{drive}:")
        return drives

    def set_low_pass_filter(self):
        cutoff, ok = QInputDialog.getDouble(
            self,
            "Set Low Pass Filter",
            "Cutoff frequency (Hz):",
            value=self.low_pass_cutoff,
            min=0.00001,
            max=1000000,
            decimals=10,
        )
        if ok:
            self.low_pass_cutoff = cutoff
            self.interpolate_steep_slopes()
            self.update_grid()

    def interpolate_steep_slopes(self):
        """
        Interpolate points in the EEG signal where the slope exceeds a physiological threshold.

        :param max_slope_threshold: The maximum allowable slope (in voltage units per sample)
        """
        for row in range(64):
            for col in range(64):
                if self.data[row, col] is not None:
                    signal = self.data_cache[row, col]["signal"]
                    time = np.arange(len(signal)) / self.sampling_rate

                    slopes = np.diff(signal) / np.diff(time)

                    extreme_slopes = np.abs(slopes) > self.low_pass_cutoff
                    extreme_indices = np.where(extreme_slopes)[0]

                    if len(extreme_indices) > 0:
                        valid_mask = np.ones(len(signal), dtype=bool)
                        valid_mask[extreme_indices] = False
                        valid_mask[extreme_indices + 1] = False

                        interp_func = interp1d(
                            time[valid_mask],
                            signal[valid_mask],
                            kind="linear",
                            fill_value="extrapolate",
                        )

                        signal[~valid_mask] = interp_func(time[~valid_mask])

                        self.data[row, col]["signal"] = signal

                        self.min_voltage = min(self.min_voltage, np.min(signal))
                        self.max_voltage = max(self.max_voltage, np.max(signal))

        print(
            f"Steep slopes interpolated. Max slope threshold: {self.low_pass_cutoff} V/s"
        )

    def apply_low_pass_filter(self):
        cutoff_frequency = self.low_pass_cutoff
        order = 4

        nyquist_frequency = 0.5 * self.sampling_rate
        normalized_cutoff = cutoff_frequency / nyquist_frequency

        b, a = butter(order, normalized_cutoff, btype="low", analog=False)

        for row in range(64):
            for col in range(64):
                if self.data[row, col] is not None:
                    signal = self.data_cache[row, col]["signal"]
                    filtered_signal = filtfilt(b, a, signal)
                    self.data[row, col]["signal"] = filtered_signal

                    self.min_voltage = min(self.min_voltage, np.min(filtered_signal))
                    self.max_voltage = max(self.max_voltage, np.max(filtered_signal))

        print(f"Low-pass filter applied. Cutoff frequency: {cutoff_frequency} Hz")

    def on_analysis_completed(self):
        self.loading_dialog.hide()
        self.data = self.analysis_thread.data

        self.min_strength = self.analysis_thread.min_strength
        self.max_strength = self.analysis_thread.max_strength
        self.recording_length = self.analysis_thread.recording_length
        self.sampling_rate = self.analysis_thread.sampling_rate
        self.distance = int(self.sampling_rate / 10)
        self.bin_size = 100 / self.sampling_rate
        self.db_scan_settings_widget.set_bin_size_range(1 / self.sampling_rate, 0.5)
        self.cluster_tracker.sampling_rate = self.sampling_rate
        self.fs_range = (0.5, self.sampling_rate / 2)
        self.time_vector = self.analysis_thread.time_vector
        self.active_channels = self.analysis_thread.active_channels
        self.min_voltage = float("inf")
        self.max_voltage = float("-inf")

        self.peak_settings_widget.threshold_slider.setValue(self.n_std_dev)
        self.peak_settings_widget.threshold_value.setText(str(self.n_std_dev))
        self.peak_settings_widget.distance_slider.setValue(self.distance)
        self.peak_settings_widget.distance_value.setText(str(self.distance))
        self.signal_analyzer = SignalAnalyzer(
            self.time_vector, sampling_rate=self.sampling_rate, distance=self.distance
        )

        delta_t = 1 / self.sampling_rate
        delta_t_str = str(delta_t)
        self.speed_combo.clear()
        self.speed_combo.addItems(
            [delta_t_str, "0.1", "0.25", "0.5", "1.0", "2.0", "4.0", "16.0"]
        )

        for row, col in self.active_channels:
            volt_signal = self.data[row - 1, col - 1]["signal"]
            voltages = np.abs(np.diff(volt_signal))
            min_range = np.min(voltages)
            max_range = np.max(voltages)
            self.min_voltage = min(self.min_voltage, min_range)
            self.max_voltage = max(self.max_voltage, max_range)

            self.grid_widget.cells[row - 1][col - 1].setCursor(Qt.PointingHandCursor)

        self.progress_bar.setSamplingRate(self.sampling_rate)
        self.progress_bar.setRange(0, int(self.recording_length * self.sampling_rate))

        self.create_grid()
        self.update_grid()
        self.raster_plot = RasterPlot(
            self.data,
            self.sampling_rate,
            self.active_channels,
            self.raster_downsample_factor,
        )
        self.raster_plot.generate_raster()
        self.raster_plot.create_raster_plot(self.second_plot_widget)
        self.raster_plot.set_main_window(self)

        title = "Select Channel"
        for i in range(4):
            self.graph_widget.plot(
                [],
                [],
                title,
                "sec",
                "mV",
                i,
                "",
                np.array([]),
                np.array([]),
            )

        for i in range(1, 4):
            self.graph_widget.plot_widgets[i].setXLink(
                self.graph_widget.plot_widgets[0]
            )
            self.graph_widget.plot_widgets[i].setYLink(
                self.graph_widget.plot_widgets[0]
            )

        self.set_widgets_enabled()

    def cancel_analysis(self):
        print("Cancelling Analysis")
        self.analysis_thread.requestInterruption()
        self.analysis_thread.wait()

        self.analysis_thread.eng = None
        self.loading_dialog.hide()
        print("Analysis Cancelled")

    def skipBackward(self):
        if self.data is None or self.plotted_channels == [None] * 4:
            return

        current_time = self.progress_bar.value() / self.sampling_rate
        start_time = 0

        for i in range(4):
            if self.plotted_channels[i] is not None:
                row, col = self.plotted_channels[i].row, self.plotted_channels[i].col
                seizures = self.data[row, col]["SzTimes"]
                se = self.data[row, col]["SETimes"]
                for seizure in seizures:
                    if seizure[0] < current_time:
                        start_time = max(start_time, seizure[0])
                for se_event in se:
                    if se_event[0] < current_time:
                        start_time = max(start_time, se_event[0])

        self.last_skip_time = start_time
        next_index = int(start_time * self.sampling_rate)

        if next_index > 0:
            self.progress_bar.setValue(next_index)
            for plot_widget in self.graph_widget.plot_widgets:
                view_box = plot_widget.getPlotItem().getViewBox()
                x_range = view_box.viewRange()[0]
                x_width = x_range[1] - x_range[0]
                x_min = start_time - x_width / 2
                x_max = start_time + x_width / 2
                view_box.setRange(xRange=(x_min, x_max), padding=0)
            self.update_grid()
        else:
            self.progress_bar.setValue(0)

    def stepBackward(self):
        speed = float(self.speed_combo.currentText())
        current_value = self.progress_bar.value()
        next_value = current_value - int(speed * self.sampling_rate)

        if next_value >= 0:
            self.progress_bar.setValue(next_value)
            self.update_grid()
        else:
            self.progress_bar.setValue(0)

    def playPause(self):
        if self.play_pause_button.text() == "":
            self.play_pause_button.setText("")
            self.playback_timer.start(100)
        else:
            self.play_pause_button.setText("")
            self.playback_timer.stop()

    def updatePlayback(self):
        speed = float(self.speed_combo.currentText())
        skip_frames = int(speed * self.sampling_rate)

        current_value = self.progress_bar.value()
        next_value = current_value + skip_frames

        if next_value <= self.progress_bar.maximum():
            self.progress_bar.setValue(next_value)
            if self.lock_to_playhead:
                self.lock_plots_to_playhead()
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.playback_timer.stop()
            self.play_pause_button.setText("")

    def lock_plots_to_playhead(self):
        current_time = self.progress_bar.value() / self.sampling_rate
        for plot_widget in self.graph_widget.plot_widgets:
            view_box = plot_widget.getPlotItem().getViewBox()
            x_range = view_box.viewRange()[0]
            x_width = x_range[1] - x_range[0]
            x_min = current_time - x_width / 2
            x_max = current_time + x_width / 2
            view_box.setRange(xRange=(x_min, x_max), padding=0)

    def stepForward(self):
        speed = float(self.speed_combo.currentText())
        current_value = self.progress_bar.value()
        next_value = current_value + int(speed * self.sampling_rate)

        if next_value <= self.progress_bar.maximum():
            self.progress_bar.setValue(next_value)
            self.update_grid()
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())

    def skipForward(self):
        if self.data is None or self.plotted_channels == [None] * 4:
            return

        current_time = self.progress_bar.value() / self.sampling_rate
        start_time = self.recording_length

        for i in range(4):
            if self.plotted_channels[i] is not None:
                row, col = self.plotted_channels[i].row, self.plotted_channels[i].col
                seizures = self.data[row, col]["SzTimes"]
                se = self.data[row, col]["SETimes"]
                for seizure in seizures:
                    if seizure[0] > current_time and self.last_skip_time != seizure[0]:
                        start_time = min(start_time, seizure[0])
                for se_event in se:
                    if (
                        se_event[0] > current_time
                        and self.last_skip_time != se_event[0]
                    ):
                        start_time = min(start_time, se_event[0])

        self.last_skip_time = start_time
        next_index = int(start_time * self.sampling_rate)

        if next_index < self.progress_bar.maximum():
            self.progress_bar.setValue(next_index)
            for plot_widget in self.graph_widget.plot_widgets:
                view_box = plot_widget.getPlotItem().getViewBox()
                x_range = view_box.viewRange()[0]
                x_width = x_range[1] - x_range[0]
                x_min = start_time - x_width / 2
                x_max = start_time + x_width / 2
                view_box.setRange(xRange=(x_min, x_max), padding=0)

            self.update_grid()
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())

    def setPlaybackSpeed(self, index):
        interval = 100
        self.playback_timer.setInterval(interval)

    def seekPosition(self, value):
        self.graph_widget.update_red_lines(value, self.sampling_rate)
        if self.raster_plot is not None:
            if self.raster_plot.raster_red_line is not None:
                percentage = value / self.progress_bar.maximum()

                scaled_percentage = percentage * len(self.active_channels)

                self.raster_plot.raster_red_line.setPos(scaled_percentage)

        if self.lock_to_playhead:
            self.lock_plots_to_playhead()

        self.update_grid()

    def show_video_editor(self):
        editor = VideoEditor(self)
        editor.set_markers(self.markers)
        editor.exec_()

    def save_channel_plots(self):
        dialog = SaveChannelPlotsDialog(self)
        dialog.exec_()

    def save_channel_plot(self, plot_index):
        dialog = SaveChannelPlotsDialog(self, plot_index)
        dialog.exec_()


font_name = "Hack Nerd Font Mono"
font_url = "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.2.1/Hack.zip"

if sys.platform == MAC:
    font_dir = "/Library/Fonts/"
elif sys.platform == WIN:
    font_dir = os.path.join(os.environ["WINDIR"], "Fonts")
else:
    print("Unsupported operating system.")
    sys.exit(1)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    if not any(font_name in font for font in QFontDatabase().families()):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f"Please install the font: {font_name}. Go to the release page to download the font.\nhttps://github.com/booka66/mea-gui/releases/"
        )
        msg.setWindowTitle("Font Installation")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    else:
        print(f"Font already installed: {font_name}")
        font = QFont(font_name, 13)
        app.setFont(font)

    window = MainWindow()
    window.showMaximized()
    window.confirm_latest_version()
    try:
        if sys.argv[1]:
            window.file_path = sys.argv[1]
            window.set_widgets_enabled()

            while not window.engine_started:
                app.processEvents()
            window.run_analysis()
    except IndexError:
        print("No file path provided")
    sys.exit(app.exec_())
