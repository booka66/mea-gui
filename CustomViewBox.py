from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import pyqtSignal


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
        load_discharges_action = QAction("Load discharges", self)
        save_single_plot_action = QAction("Save this plot", self)
        save_all_plots_action = QAction("Save all plots", self)
        toggle_regions_action = QAction("Toggle regions", self)
        toggle_red_lines_action = QAction("Toggle red lines", self)
        toggle_mini_map_action = QAction("Toggle minimap", self)

        find_discharges_action.triggered.connect(
            self.parent.main_window.find_discharges
        )
        track_discharges_action.triggered.connect(self.parent.main_window.auto_analyze)
        load_discharges_action.triggered.connect(
            self.parent.main_window.load_discharges
        )

        save_single_plot_action.triggered.connect(self.save_single_plot.emit)
        save_all_plots_action.triggered.connect(self.save_all_plots.emit)

        toggle_regions_action.triggered.connect(self.toggle_regions)
        toggle_red_lines_action.triggered.connect(self.toggle_red_lines)
        toggle_mini_map_action.triggered.connect(self.toggle_mini_map)

        self.addAction(find_discharges_action)
        self.addAction(track_discharges_action)
        self.addAction(load_discharges_action)
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


class RasterViewBoxMenu(QMenu):
    save_raster = pyqtSignal()
    cluster = pyqtSignal()

    def __init__(self, view, parent=None):
        super().__init__()
        self.view = view
        self.parent = parent
        self.setTitle("ViewBox options")

        save_raster_action = QAction("Save raster", self)
        cluster_action = QAction("Cluster", self)

        save_raster_action.triggered.connect(self.save_raster.emit)
        cluster_action.triggered.connect(self.cluster.emit)

        self.addAction(save_raster_action)
        self.addAction(cluster_action)
