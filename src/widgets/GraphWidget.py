from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import pyqtgraph as pg
import numpy as np
from helpers.Constants import STROKE_WIDTH, GRAPH_DOWNSAMPLE
from widgets.CustomViewBox import TraceViewBoxMenu

failed_import = False
try:
    import lttbc
except ImportError:
    failed_import = True


class GraphWidget(QWidget):
    region_clicked = pyqtSignal(float, float, int)
    save_single_plot = pyqtSignal()
    save_all_plots = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.layout = QVBoxLayout(self)
        self.updating_from_minimap = False
        self.updating_from_plot = False
        self.current_stroke = 1
        self.graphs_downsampled = False

        self.minimap = pg.PlotWidget()
        self.minimap.hideAxis("bottom")
        self.minimap.hideAxis("left")
        self.minimap.setMouseEnabled(x=False, y=False)
        self.minimap.setBackground("w")
        self.minimap_plot = self.minimap.plot(pen=pg.mkPen(color=(0, 0, 0), width=1))
        self.minimap_region = pg.LinearRegionItem(
            values=(0, 1), movable=True, brush=(0, 0, 255, 50)
        )
        self.minimap.addItem(self.minimap_region)
        self.minimap.setContextMenuPolicy(3)

        self.minimap_region.sigRegionChanged.connect(self.minimap_region_changed)

        self.minimap.setFixedHeight(100)
        self.minimap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.layout.addWidget(self.minimap)

        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(0)
        self.layout.addWidget(self.plots_container)

        self.plot_widgets = [pg.PlotWidget() for _ in range(4)]
        self.red_lines = [
            pg.InfiniteLine(
                angle=90, movable=False, pen=pg.mkPen(color=(255, 0, 0), width=2)
            )
            for _ in range(4)
        ]
        self.do_show_regions = True
        self.x_data = [None] * 4
        self.y_data = [None] * 4
        self.trace_curves = [None] * 4
        self.active_plot_index = 0
        self.do_show_mini_map = True
        self.last_active_plot_index = -1

        for i in range(4):
            plot_widget = self.plot_widgets[i]
            red_line = self.red_lines[i]

            view_box = plot_widget.getPlotItem().getViewBox()
            custom_menu = TraceViewBoxMenu(view_box, self)
            custom_menu.save_single_plot.connect(self.save_single_plot)
            custom_menu.save_all_plots.connect(self.save_all_plots)
            view_box.menu = custom_menu

            plot_widget.showGrid(x=False, y=False)
            plot_widget.setMouseEnabled(x=True, y=True)
            plot_widget.setClipToView(True)
            plot_widget.setDownsampling(mode="peak")
            plot_widget.setXRange(0, 1000)
            plot_widget.enableAutoRange(axis="y")
            plot_widget.getPlotItem().getViewBox().setLimits(xMin=0, xMax=2**16)
            plot_widget.getPlotItem().getViewBox().setMouseEnabled(x=True, y=True)
            plot_widget.getPlotItem().getViewBox().setMouseMode(pg.ViewBox.RectMode)
            plot_widget.getPlotItem().getViewBox().enableAutoRange(
                axis="xy", enable=True
            )
            plot_widget.getPlotItem().showGrid(x=False, y=False)
            plot_widget.addItem(red_line)
            plot_widget.setObjectName(f"plot_{i}")
            plot_widget.setBackground("w")

            plot_widget.getPlotItem().getViewBox().sigRangeChanged.connect(
                lambda view_box, range_: self.sync_ranges(
                    i, range_[0], update_minimap=True
                )
            )

            plot_widget.scene().sigMouseMoved.connect(
                lambda pos, i=i: self.update_active_plot(pos, i)
            )

            self.plots_layout.addWidget(plot_widget)

        self.sync_timer = QTimer()
        self.sync_timer.setSingleShot(True)
        self.sync_timer.timeout.connect(self.apply_synced_range)

        self.synced_range = None

    def sync_ranges(self, source_index, x_range, update_minimap=False):
        if self.updating_from_minimap:
            return

        self.synced_range = x_range
        if not self.sync_timer.isActive():
            self.sync_timer.start(0)

        if update_minimap:
            self.update_minimap()

    def plot_peaks(self):
        for i, plot_widget in enumerate(self.plot_widgets):
            if self.main_window.plotted_channels[i] is not None:
                row, col = (
                    self.main_window.plotted_channels[i].row,
                    self.main_window.plotted_channels[i].col,
                )
                if len(self.main_window.discharges) > 0:
                    discharge_start_x, discharge_start_y = self.main_window.discharges[
                        (row, col)
                    ]
                    for item in self.plot_widgets[i].items():
                        if isinstance(item, pg.ScatterPlotItem):
                            self.plot_widgets[i].removeItem(item)

                    discharge_plot = pg.ScatterPlotItem(
                        x=discharge_start_x,
                        y=discharge_start_y,
                        symbol="o",
                        size=8,
                        brush=pg.mkBrush(color=(255, 165, 0)),
                        pen=pg.mkPen(color=(255, 165, 0), width=STROKE_WIDTH),
                    )
                    self.plot_widgets[i].addItem(discharge_plot)

                elif self.main_window.show_discharge_peaks:
                    volt_signal = self.main_window.data[row, col]["signal"]
                    start, stop = self.plot_widgets[i].viewRange()[0]

                    peak_x, peak_y, discharge_start_x, discharge_start_y = (
                        self.main_window.signal_analyzer.analyze_signal(
                            volt_signal, start, stop
                        )
                    )
                    for item in self.plot_widgets[i].items():
                        if isinstance(item, pg.ScatterPlotItem):
                            self.plot_widgets[i].removeItem(item)

                    peak_plot = pg.ScatterPlotItem(
                        x=peak_x,
                        y=peak_y,
                        symbol="o",
                        size=5,
                        brush=pg.mkBrush(color=(255, 0, 0)),
                        pen=pg.mkPen(color=(255, 0, 0), width=STROKE_WIDTH),
                    )
                    self.plot_widgets[i].addItem(peak_plot)

                    discharge_plot = pg.ScatterPlotItem(
                        x=discharge_start_x,
                        y=discharge_start_y,
                        symbol="o",
                        size=8,
                        brush=pg.mkBrush(color=(255, 165, 0)),
                        pen=pg.mkPen(color=(255, 165, 0), width=STROKE_WIDTH),
                    )
                    self.plot_widgets[i].addItem(discharge_plot)

    def apply_synced_range(self):
        if self.synced_range is None:
            return

        for i, plot_widget in enumerate(self.plot_widgets):
            if (
                plot_widget.getPlotItem().getViewBox().viewRange()[0]
                != self.synced_range
            ):
                plot_widget.getPlotItem().getViewBox().setXRange(
                    *self.synced_range, padding=0
                )
                plot_widget.enableAutoRange(axis="y")
        if self.main_window.show_discharge_peaks:
            self.plot_peaks()

        self.synced_range = None

    def update_minimap(self):
        if self.updating_from_minimap or not self.do_show_mini_map:
            return

        self.updating_from_plot = True
        active_x_data = self.x_data[self.active_plot_index]
        active_y_data = self.y_data[self.active_plot_index]

        if active_x_data is None or active_y_data is None:
            self.updating_from_plot = False
            return

        # Only update the minimap data if the active plot has changed
        if self.active_plot_index != self.last_active_plot_index:
            downsampled_x, downsampled_y = self.downsample_data(
                active_x_data, active_y_data, GRAPH_DOWNSAMPLE
            )
            curve = pg.PlotDataItem(
                downsampled_x, downsampled_y, pen=pg.mkPen(color=(0, 0, 0), width=1)
            )
            curve.setDownsampling(auto=True, method="peak")

            self.minimap.clear()
            self.minimap.addItem(curve)
            self.minimap.addItem(self.minimap_region)
            self.minimap_plot = curve

            self.last_active_plot_index = self.active_plot_index
            if len(active_x_data) > 0:
                self.minimap.getPlotItem().getViewBox().setLimits(
                    xMin=0, xMax=max(active_x_data)
                )

        # Always update the region
        view_range = (
            self.plot_widgets[self.active_plot_index]
            .getPlotItem()
            .getViewBox()
            .viewRange()
        )
        x_min, x_max = view_range[0]
        self.minimap_region.setRegion((x_min, x_max))
        self.updating_from_plot = False

    def minimap_region_changed(self):
        if self.updating_from_plot:
            return

        self.updating_from_minimap = True
        region_min, region_max = self.minimap_region.getRegion()

        for plot_widget in self.plot_widgets:
            plot_widget.getPlotItem().getViewBox().setXRange(
                region_min, region_max, padding=0
            )

        self.updating_from_minimap = False

    def toggle_regions(self):
        self.do_show_regions = not self.do_show_regions
        self.main_window.toggleRegionsAction.setChecked(self.do_show_regions)
        if self.do_show_regions:
            self.show_regions()
        else:
            self.hide_regions()

    def toggle_red_lines(self):
        self.main_window.toggle_playheads(not self.red_lines[0].isVisible())
        self.main_window.togglePlayheadsActions.setChecked(
            self.red_lines[0].isVisible()
        )

    def toggle_mini_map_from_context_menu(self):
        self.toggle_mini_map(not self.do_show_mini_map)

    def hide_red_lines(self):
        for red_line in self.red_lines:
            red_line.hide()

    def show_red_lines(self):
        for red_line in self.red_lines:
            red_line.show()

    def toggle_mini_map(self, checked):
        self.do_show_mini_map = checked
        if checked:
            self.minimap.show()
            self.layout.insertWidget(0, self.minimap)
        else:
            self.minimap.hide()
            self.layout.removeWidget(self.minimap)

    def update_active_plot(self, pos, plot_index):
        if self.do_show_mini_map and self.plot_widgets[
            plot_index
        ].sceneBoundingRect().contains(pos):
            self.active_plot_index = plot_index
            self.update_minimap()

    def update_red_lines(self, value, sampling_rate):
        for red_line in self.red_lines:
            red_line.setPos(value / sampling_rate)

    def get_regions(self, seizures, se):
        seizure_regions = []
        se_regions = []
        for timerange in se:
            start, stop, _ = timerange
            se_regions.append((start, stop))
        for timerange in seizures:
            start, stop, _ = timerange
            if not any(
                start <= se_start <= stop or se_start <= start <= se_stop
                for se_start, se_stop in se_regions
            ):
                seizure_regions.append((start, stop))

        return seizure_regions, se_regions

    def show_regions(self):
        for plot in self.plot_widgets:
            for item in plot.items():
                if isinstance(item, pg.LinearRegionItem):
                    item.show()

    def hide_regions(self):
        for plot in self.plot_widgets:
            for item in plot.items():
                if isinstance(item, pg.LinearRegionItem):
                    item.hide()

    def plot(self, x, y, title, xlabel, ylabel, plot_index, shape, seizures, se):
        self.plot_widgets[plot_index].clear()
        self.x_data[plot_index] = x
        self.y_data[plot_index] = y
        print(f"We have {len(x)} points to plot")
        seizure_regions, se_regions = self.get_regions(seizures, se)

        curve = self.plot_widgets[plot_index].plot(pen=pg.mkPen("k", width=3))
        curve.setData(x, y)
        curve.setDownsampling(auto=True, method="peak", ds=100)
        curve.setClipToView(True)
        self.trace_curves[plot_index] = curve

        self.plot_widgets[plot_index].addItem(self.red_lines[plot_index])

        if len(x) > 0:
            self.plot_widgets[plot_index].getPlotItem().getViewBox().setLimits(
                xMin=0, xMax=max(x)
            )

        if "(" in title:
            title_parts = title.split(" ", 1)
            shape_text = title_parts[0]
            remaining_title = title_parts[1] if len(title_parts) > 1 else ""
            title_text = f'<span style="color: #000000; font-size: 14pt; font-weight: bold;">{shape_text}</span> {remaining_title}'
            self.plot_widgets[plot_index].setTitle(title_text)
        else:
            self.plot_widgets[plot_index].setTitle(
                title, color="#000000", size="15pt", bold=True
            )

        axis_label_style = {
            "color": "#000000",
            "font-size": "13pt",
            "font-weight": "bold",
        }
        self.plot_widgets[plot_index].setLabel("bottom", xlabel, **axis_label_style)
        self.plot_widgets[plot_index].setLabel("left", ylabel, **axis_label_style)
        self.plot_widgets[plot_index].getAxis("bottom").setTextPen(
            pg.mkPen(color=(0, 0, 0), width=2)
        )
        self.plot_widgets[plot_index].getAxis("left").setTextPen(
            pg.mkPen(color=(0, 0, 0), width=2)
        )

        for start, stop in se_regions:
            region = pg.LinearRegionItem(
                values=(start, stop), brush="#ffb70380", movable=False
            )
            region.mouseClickEvent = (
                lambda event,
                start=start,
                stop=stop,
                plot_index=plot_index: self.region_clicked.emit(start, stop, plot_index)
                if event.button() == Qt.LeftButton
                else None
            )
            self.plot_widgets[plot_index].addItem(region)
            # Make it appear under the curve
            region.setZValue(-1)

        for start, stop in seizure_regions:
            region = pg.LinearRegionItem(
                values=(start, stop), brush="#0096c780", movable=False
            )
            region.mouseClickEvent = (
                lambda event,
                start=start,
                stop=stop,
                plot_index=plot_index: self.region_clicked.emit(start, stop, plot_index)
                if event.button() == Qt.LeftButton
                else None
            )
            self.plot_widgets[plot_index].addItem(region)
            region.setZValue(-1)

        if self.do_show_regions:
            self.show_regions()
        else:
            self.hide_regions()

        if plot_index == 0:
            self.update_minimap()

    def get_num_points(self, plot_index):
        return len(self.x_data[plot_index])

    def downsample_data(self, x, y, num_points):
        if x is None or y is None:
            return [], []
        if len(x) <= num_points:
            return x, y

        if not failed_import:
            downsample_x, downsample_y = lttbc.downsample(x, y, num_points)
        else:
            downsample_x = np.linspace(x[0], x[-1], num_points)
            downsample_y = np.interp(downsample_x, x, y)

        return downsample_x, downsample_y

    def change_view_mode(self, mode: str):
        if mode == "pan":
            for i in range(4):
                plot_widget = self.plot_widgets[i]
                view_box = plot_widget.getPlotItem().getViewBox()
                view_box.setMouseMode(pg.ViewBox.PanMode)
        else:
            for i in range(4):
                plot_widget = self.plot_widgets[i]
                view_box = plot_widget.getPlotItem().getViewBox()
                view_box.setMouseMode(pg.ViewBox.RectMode)
