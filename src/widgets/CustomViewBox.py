from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import pyqtSignal
from pyqtgraph.Qt.QtWidgets import QMessageBox


class TraceViewBoxMenu(QMenu):
    save_single_plot = pyqtSignal()
    save_all_plots = pyqtSignal()

    def __init__(self, view, parent=None):
        super().__init__()
        self.view = view
        self.parent = parent
        self.setTitle("ViewBox options")

        find_discharges_action = QAction("Find discharges", self)
        track_discharges_action = QAction("Track discharges", self)
        stop_tracking_discharges_action = QAction("Stop tracking discharges", self)
        load_discharges_action = QAction("Load discharges", self)
        clear_discharges_action = QAction("Clear discharges", self)
        clear_tracked_discharges_action = QAction("Clear tracked discharges", self)
        save_tracked_discharges_action = QAction("Save tracked discharges", self)
        export_discharge_stats_action = QAction("Export discharge stats", self)
        save_single_plot_action = QAction("Save this plot", self)
        save_all_plots_action = QAction("Save all plots", self)
        toggle_regions_action = QAction("Toggle regions", self)
        toggle_red_lines_action = QAction("Toggle red lines", self)
        toggle_mini_map_action = QAction("Toggle mini-map", self)

        find_discharges_action.triggered.connect(
            self.parent.main_window.find_discharges
        )
        track_discharges_action.triggered.connect(self.parent.main_window.auto_analyze)
        stop_tracking_discharges_action.triggered.connect(self.stop_tracking_discharges)
        load_discharges_action.triggered.connect(
            self.parent.main_window.load_discharges
        )
        clear_discharges_action.triggered.connect(
            self.parent.main_window.clear_found_discharges
        )
        clear_tracked_discharges_action.triggered.connect(self.clear_tracked_discharges)
        save_tracked_discharges_action.triggered.connect(self.save_tracked_discharges)
        export_discharge_stats_action.triggered.connect(
            self.parent.main_window.export_discharge_stats
        )

        save_single_plot_action.triggered.connect(self.save_single_plot.emit)
        save_all_plots_action.triggered.connect(self.save_all_plots.emit)

        toggle_regions_action.triggered.connect(self.toggle_regions)
        toggle_red_lines_action.triggered.connect(self.toggle_red_lines)
        toggle_mini_map_action.triggered.connect(self.toggle_mini_map)

        self.addAction(find_discharges_action)
        self.addAction(track_discharges_action)
        self.addAction(stop_tracking_discharges_action)
        self.addAction(load_discharges_action)
        self.addAction(clear_discharges_action)
        self.addAction(clear_tracked_discharges_action)
        self.addAction(save_tracked_discharges_action)
        self.addAction(export_discharge_stats_action)
        self.addSeparator()
        self.addAction(save_single_plot_action)
        self.addAction(save_all_plots_action)
        self.addSeparator()
        self.addAction(toggle_regions_action)
        self.addAction(toggle_red_lines_action)
        self.addAction(toggle_mini_map_action)

    def toggle_regions(self):
        self.parent.toggle_regions()

    def toggle_red_lines(self):
        self.parent.toggle_red_lines()

    def toggle_mini_map(self):
        self.parent.toggle_mini_map_from_context_menu()

    def stop_tracking_discharges(self):
        if self.parent.main_window.is_auto_analyzing:
            self.parent.main_window.is_auto_analyzing = False

    def clear_tracked_discharges(self):
        self.parent.main_window.cluster_tracker.seizure_graphics_items.clear()
        self.parent.main_window.cluster_tracker.seizures.clear()

    def save_tracked_discharges(self):
        file_path = self.parent.main_window.file_path
        if file_path is None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("No file loaded")
            msg.setInformativeText("Please load a file before saving.")
            msg.setWindowTitle("No file loaded")
            msg.exec_()
            return

        custom_region = self.parent.main_window.custom_region
        if custom_region is None or len(self.parent.main_window.discharges) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("No discharges detected")
            msg.setInformativeText("Please detect discharges before saving.")
            msg.setWindowTitle("No discharges detected")
            msg.exec_()
            return

        cluster_tracker = self.parent.main_window.cluster_tracker
        if cluster_tracker.seizures is None or len(cluster_tracker.seizures) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("No tracked discharges")
            msg.setInformativeText("Please track discharges before saving.")
            msg.setWindowTitle("No tracked discharges")
            msg.exec_()
            return

        cluster_tracker.save_discharges_to_hdf5(file_path, *custom_region)


class RasterViewBoxMenu(QMenu):
    save_raster = pyqtSignal()
    order = pyqtSignal(str)
    toggle_color_mode = pyqtSignal()

    def __init__(self, view, parent=None):
        super().__init__()
        self.view = view
        self.parent = parent
        self.setTitle("ViewBox options")

        toggle_color_mode_action = QAction("Toggle color mode", self)

        save_raster_action = QAction("Save raster", self)

        row_order_menu = QMenu("Row Order", self)
        default_order_action = QAction("Default", self)
        cluster_order_action = QAction("SE Entrance Cluster", self)
        se_entrance_order_action = QAction("SE Entrance", self)
        sz_entrance_order_action = QAction("Seizure Entrance", self)

        toggle_color_mode_action.triggered.connect(self.toggle_color_mode.emit)
        save_raster_action.triggered.connect(self.save_raster.emit)

        default_order_action.triggered.connect(lambda: self.order.emit("default"))
        cluster_order_action.triggered.connect(lambda: self.order.emit("cluster"))
        se_entrance_order_action.triggered.connect(lambda: self.order.emit("SE"))
        sz_entrance_order_action.triggered.connect(lambda: self.order.emit("seizure"))

        self.addAction(toggle_color_mode_action)
        self.addAction(save_raster_action)
        row_order_menu.addAction(default_order_action)
        row_order_menu.addAction(cluster_order_action)
        row_order_menu.addAction(se_entrance_order_action)
        row_order_menu.addAction(sz_entrance_order_action)
        self.addMenu(row_order_menu)
