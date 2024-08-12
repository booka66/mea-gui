import colorsys
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QFileDialog, QGraphicsDropShadowEffect, QMessageBox
from scipy.signal import find_peaks
import os
from widgets.CustomViewBox import RasterViewBoxMenu
from widgets.GroupSelectionDialog import Group


class RasterPlot:
    def __init__(self, data, sampling_rate, active_channels, downsample_factor):
        self.data = data
        self.sampling_rate = sampling_rate
        self.active_channels = active_channels
        self.downsample_factor = downsample_factor
        self.spike_data = []
        self.plot_widget = None
        self.raster_red_line = None
        self.spike_threshold = 0.06
        self.groups = []
        self.show_group_colors = False
        self.legend = None
        self.scatter_plot = None
        self.tooltip = None
        self.tooltip_text = None
        self.tooltip_line_vert = None
        self.tooltip_line_horiz = None
        self.selected_channel = None
        self.selected_channel_dot = None
        self.plotted_channels = []
        self.plotted_channels_highlights: list[pg.LinearRegionItem] = []
        self.main_window = None
        self.symbol = "o"
        self.size = 5
        self.color_index = 0
        self.predefined_colors = [
            (211, 31, 17),
            (98, 200, 211),
            (244, 122, 0),
            (0, 113, 145),
            (106, 153, 78),
        ]

    def set_main_window(self, main_window):
        self.main_window = main_window

    def toggle_red_line(self):
        self.main_window.toggle_playheads(not self.raster_red_line.isVisible())
        self.main_window.togglePlayheadsActions.setChecked(
            self.raster_red_line.isVisible()
        )

    def mouse_clicked(self, event):
        try:
            if event.button() == Qt.LeftButton:
                scene_pos = event.scenePos()

                view_pos = self.plot_widget.getViewBox().mapSceneToView(scene_pos)

                if self.selected_channel_dot:
                    self.plot_widget.removeItem(self.selected_channel_dot)

                nearest_point = self.find_nearest_point(view_pos.x(), view_pos.y())

                if nearest_point is not None:
                    x, y, row, col, time = nearest_point
                    self.selected_channel = (
                        row - 1,
                        col - 1,
                    )

                    if self.main_window:
                        self.main_window.selected_channel = self.selected_channel

                    self.selected_channel_dot = pg.ScatterPlotItem(
                        x=[x], y=[y], pen=None, brush=pg.mkBrush(0, 255, 0), size=7
                    )
                    self.plot_widget.addItem(self.selected_channel_dot)

                    self.raster_red_line.setPos(x)
                    self.main_window.progress_bar.setValue(
                        int(time * self.sampling_rate)
                    )
        except Exception:
            pass

    def set_plotted_channels(self, channels):
        if self.plot_widget is None:
            return
        self.plotted_channels = channels

        if self.plotted_channels_highlights:
            for line in self.plotted_channels_highlights:
                self.plot_widget.removeItem(line)

        self.plotted_channels_highlights = []

        print(self.plotted_channels)

        for row, col in self.plotted_channels:
            y = len(self.active_channels) - self.active_channels.index((row, col)) - 1
            region = pg.LinearRegionItem(
                [y - 0.5, y + 0.5],
                orientation=pg.LinearRegionItem.Horizontal,
                brush=pg.mkBrush(color=(255, 0, 0, 100)),
                pen=pg.mkPen(color=(255, 0, 0, 0)),
                movable=False,
            )

            self.plot_widget.addItem(region)
            self.plotted_channels_highlights.append(region)

    def set_groups(self, groups):
        self.groups = groups
        self.sort_channels_by_group()
        self.generate_raster()
        self.update_raster_plot_data()
        self.set_plotted_channels(self.plotted_channels)

    def toggle_color_mode(self):
        self.show_group_colors = not self.show_group_colors
        self.update_raster_plot_data()

    def sort_channels_by_group(self):
        grouped_channels = []
        for group in self.groups:
            grouped_channels.extend(group.channels)

        ungrouped_channels = [
            ch for ch in self.active_channels if ch not in grouped_channels
        ]
        grouped_channels.extend(ungrouped_channels)

        self.active_channels = grouped_channels

    def generate_raster(self):
        self.spike_data = [
            self.detect_spikes(self.data[row - 1, col - 1]) / self.sampling_rate
            for row, col in self.active_channels
        ]

    def detect_spikes(self, channel_data):
        voltage_data = np.asarray(channel_data["signal"]).squeeze()[
            :: self.downsample_factor
        ]
        peaks, _ = find_peaks(
            voltage_data,
            height=self.spike_threshold,
            distance=self.sampling_rate // 10,
        )
        return peaks * self.downsample_factor

    def setup_tooltip(self):
        self.tooltip = pg.TextItem(
            text="", anchor=(0.5, 1), fill=QColor(255, 255, 255, 200), color=(0, 0, 0)
        )
        self.tooltip.setZValue(1000)
        self.tooltip.hide()

        # Add blur effect
        blur_effect = QGraphicsDropShadowEffect()
        blur_effect.setBlurRadius(25)
        blur_effect.setColor(QColor(0, 0, 0, 100))
        blur_effect.setOffset(0, 0)
        self.tooltip.setGraphicsEffect(blur_effect)

        self.plot_widget.addItem(self.tooltip)

        self.tooltip_line_vert = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=(100, 100, 100), width=1, style=Qt.DashLine),
        )
        self.tooltip_line_vert.hide()
        self.plot_widget.addItem(self.tooltip_line_vert)

        self.tooltip_line_horiz = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(color=(100, 100, 100), width=1, style=Qt.DashLine),
        )
        self.tooltip_line_horiz.hide()
        self.plot_widget.addItem(self.tooltip_line_horiz)

        self.plot_widget.scene().sigMouseMoved.connect(self.update_tooltip)

    def find_nearest_point(self, x, y):
        if self.scatter_plot is None or len(self.scatter_plot.data) == 0:
            return None

        points = self.scatter_plot.data
        distances = np.sqrt((points["x"] - x) ** 2 + (points["y"] - y) ** 2)
        nearest_idx = np.argmin(distances)

        if distances[nearest_idx] > 1:  # Set a maximum distance for showing tooltip
            return None

        nearest_x = points["x"][nearest_idx]
        nearest_y = points["y"][nearest_idx]

        channel_idx = len(self.active_channels) - int(nearest_y) - 1
        row, col = self.active_channels[channel_idx]
        time = (
            nearest_x
            * max(max(times) if times.size > 0 else 0 for times in self.spike_data)
            / len(self.active_channels)
        )

        return nearest_x, nearest_y, row, col, time

    def update_tooltip(self, pos):
        mousePoint = self.plot_widget.getPlotItem().vb.mapSceneToView(pos)
        nearest_point = self.find_nearest_point(mousePoint.x(), mousePoint.y())

        if nearest_point is not None:
            self.plot_widget.setCursor(Qt.PointingHandCursor)
            x, y, row, col, time = nearest_point

            group_num = self.get_group_number(row, col)

            tooltip_text = f"Channel: ({row}, {col})\n"
            tooltip_text += f"Time: {time:.3f} s\n"
            if group_num is not None:
                tooltip_text += f"Group: {group_num}"

            self.tooltip.setText(tooltip_text)

            # Calculate position to keep tooltip at constant height above cursor
            view_range = self.plot_widget.getViewBox().viewRange()
            y_range = view_range[1][1] - view_range[1][0]
            constant_offset = y_range * 0.02  # 2% of the view height
            tooltip_y = y + constant_offset

            self.tooltip.setPos(x, tooltip_y)
            self.tooltip.show()

            self.tooltip_line_vert.setPos(x)
            self.tooltip_line_vert.show()
            self.tooltip_line_horiz.setPos(y)
            self.tooltip_line_horiz.show()
        else:
            self.plot_widget.setCursor(Qt.ArrowCursor)
            self.tooltip.hide()
            self.tooltip_line_vert.hide()
            self.tooltip_line_horiz.hide()

    def create_raster_plot(self, plot_widget):
        self.plot_widget: pg.PlotWidget = plot_widget
        self.plot_widget.clear()

        view_box = self.plot_widget.getPlotItem().getViewBox()
        custom_menu = RasterViewBoxMenu(view_box, self)
        custom_menu.save_raster.connect(self.save_raster_plot)
        custom_menu.cluster.connect(self.cluster_channels_by_se_onset)
        view_box.menu = custom_menu

        self.plot_widget.getPlotItem().getViewBox().enableAutoRange(
            axis="y", enable=True
        )
        self.plot_widget.getPlotItem().getViewBox().enableAutoRange(
            axis="x", enable=False
        )

        self.scatter_plot = pg.ScatterPlotItem(pxMode=True)
        self.plot_widget.addItem(self.scatter_plot)

        axis_label_style = {
            "color": "#000000",
            "font-size": "14pt",
            "font-weight": "bold",
        }
        self.plot_widget.setLabel("bottom", "Time (s)", **axis_label_style)
        self.plot_widget.setLabel("left", "Channel", **axis_label_style)
        self.plot_widget.getAxis("bottom").setTextPen(
            pg.mkPen(color=(0, 0, 0), width=2)
        )
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen(color=(0, 0, 0), width=2))

        self.raster_red_line = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen(color=(255, 0, 0), width=2)
        )
        self.plot_widget.addItem(self.raster_red_line)

        self.legend = self.plot_widget.addLegend(
            offset=(10, 10),
            pen=pg.mkPen(pg.mkColor(0, 0, 0)),
            brush=pg.mkBrush(255, 255, 255, 200),
        )

        self.setup_tooltip()

        self.update_raster_plot_data()

        # Connect mouse click event
        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)

    def update_raster_plot_data(self):
        if not self.spike_data:
            return

        if self.plotted_channels:
            self.set_plotted_channels(self.plotted_channels)

        num_channels = len(self.active_channels)
        max_spike_time = max(
            np.max(times) if times.size > 0 else 0 for times in self.spike_data
        )

        all_x = []
        all_y = []
        all_colors = []

        for i, (spike_times, (row, col)) in enumerate(
            zip(self.spike_data, self.active_channels)
        ):
            if spike_times.size == 0:
                continue

            scaled_spike_times = spike_times * num_channels / max_spike_time
            y_position = num_channels - i - 1

            all_x.extend(scaled_spike_times)
            all_y.extend(np.full(len(spike_times), y_position))

            if self.show_group_colors:
                color = self.get_group_color(row, col)
                all_colors.extend([color] * len(spike_times))
            else:
                channel_data = self.data[row - 1, col - 1]
                colors = self.get_event_colors(channel_data, spike_times)
                all_colors.extend(colors)

        self.scatter_plot.setData(
            x=all_x,
            y=all_y,
            pen=None,
            brush=all_colors,
            size=self.size,
            pxMode=True,
            symbol=self.symbol,
        )

        self.plot_widget.getPlotItem().getViewBox().autoRange()
        self.update_axes(num_channels, max_spike_time)
        self.update_legend()

        # Update plotted channel highlight positions
        for i, (row, col) in enumerate(self.plotted_channels):
            y = num_channels - self.active_channels.index((row, col)) - 1
            self.plotted_channels_highlights[i].setRegion([y - 0.5, y + 0.5])

        # Set x and y limits for the plot
        self.plot_widget.getPlotItem().getViewBox().setLimits(
            xMin=0, xMax=max(scaled_spike_times), yMin=-5, yMax=num_channels + 5
        )

    def get_event_colors(self, channel_data, spike_times):
        colors = np.full(len(spike_times), pg.mkBrush(0, 0, 0))  # Default color (black)

        for start, stop, _ in channel_data["SETimes"]:
            mask = (start <= spike_times) & (spike_times <= stop)
            colors[mask] = pg.mkBrush(255, 165, 0)  # Orange for SE

        for start, stop, _ in channel_data["SzTimes"]:
            mask = (start <= spike_times) & (spike_times <= stop)
            colors[mask] = pg.mkBrush(0, 0, 255)  # Blue for seizure

        return colors

    def get_group_color(self, row, col):
        group = self.get_group(row, col)
        if group:
            return pg.mkBrush(*[int(255 * c) for c in group.color])
        return pg.mkBrush(0, 0, 0)  # Default color for ungrouped channels

    def update_axes(self, num_channels, max_spike_time):
        ax = self.plot_widget.getAxis("bottom")
        num_ticks = 5
        tick_positions = np.linspace(0, num_channels, num_ticks)
        tick_strings = [
            f"{pos * max_spike_time / num_channels:.2f}" for pos in tick_positions
        ]
        ax.setTicks([list(zip(tick_positions, tick_strings))])
        ax.setLabel("Time (s)")

        ay = self.plot_widget.getAxis("left")
        channel_positions = np.linspace(0, num_channels - 1, min(num_channels, 10))
        channel_labels = [f"{num_channels - int(pos)}" for pos in channel_positions]
        ay.setTicks([list(zip(channel_positions, channel_labels))])
        ay.setLabel("Channel")

    def update_legend(self):
        if self.legend is not None:
            self.legend.clear()

        font = QFont()
        font.setPointSize(14)

        if not self.show_group_colors:
            self.legend.addItem(
                pg.ScatterPlotItem(
                    symbol=self.symbol, size=self.size, pen="k", brush="k"
                ),
                "Normal",
            )
            self.legend.addItem(
                pg.ScatterPlotItem(
                    symbol=self.symbol, size=self.size, pen="b", brush="b"
                ),
                "Seizure",
            )
            self.legend.addItem(
                pg.ScatterPlotItem(
                    symbol=self.symbol, size=self.size, pen="orange", brush="orange"
                ),
                "SE",
            )
        else:
            for group in self.groups:
                color = QColor(*[int(255 * c) for c in group.color])
                self.legend.addItem(
                    pg.ScatterPlotItem(
                        symbol=self.symbol, size=self.size, pen=color, brush=color
                    ),
                    f"Group {group.number}",
                )

        for item in self.legend.items:
            item[1].setText(item[1].text, color=(0, 0, 0))
            item[1].setFont(font)

    def set_raster_order(self, order):
        if order == "default":
            self.active_channels.sort(key=lambda x: (x[0], x[1]))
        elif order == "seizure":
            self.active_channels.sort(
                key=lambda x: self.get_first_event_time(x[0] - 1, x[1] - 1, "SzTimes")
            )
        elif order == "SE":
            self.active_channels.sort(
                key=lambda x: self.get_first_event_time(x[0] - 1, x[1] - 1, "SETimes")
            )

        self.update_raster_plot_data()

    def save_raster_plot(self):
        file_dialog = QFileDialog()
        default_file = os.path.join(os.path.expanduser("~/Downloads"), "raster_plot")
        file_path, _ = file_dialog.getSaveFileName(
            self.main_window,
            "Save Raster Plot",
            default_file,
            "PNG Files (*.png);;SVG Files (*.svg)",
        )
        if file_path:
            if file_path.lower().endswith(".svg"):
                self.export_as_svg(file_path)
            elif file_path.lower().endswith(".png"):
                self.export_as_png(file_path)
            else:
                QMessageBox.warning(
                    self.main_window,
                    "Invalid File Format",
                    "Please choose either .svg or .png file format.",
                )

    def export_as_svg(self, file_path):
        exporter = pg.exporters.SVGExporter(self.plot_widget.plotItem)
        exporter.export(file_path)
        QMessageBox.information(
            self.main_window,
            "Export Successful",
            f"Raster plot saved as SVG: {file_path}",
        )

    def export_as_png(self, file_path):
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        # Make it higher resolution (4x the orginal plot size)
        height = self.plot_widget.height() * 4
        width = self.plot_widget.width() * 4
        exporter.parameters()["height"] = height
        exporter.parameters()["width"] = width
        exporter.export(file_path)
        QMessageBox.information(
            self.main_window,
            "Export Successful",
            f"Raster plot saved as PNG: {file_path}",
        )

    def get_first_event_time(self, row, col, event_type):
        if (
            self.data is None
            or row < 0
            or row >= self.data.shape[0]
            or col < 0
            or col >= self.data.shape[1]
        ):
            return float("inf")

        channel_data = self.data[row, col]
        event_times = channel_data[event_type]

        return event_times[0][0] if event_times.size > 0 else float("inf")

    def get_group_number(self, row, col):
        for i, group in enumerate(self.groups):
            if (row, col) in group.channels:
                return i + 1
        return None

    def get_group(self, row, col):
        for group in self.groups:
            if (row, col) in group.channels:
                return group
        return None

    def cluster_channels_by_se_onset(self, time_window=60):
        # Dictionary to store first SE onset time for each channel
        se_onset_times = {}
        channels_without_se = []

        # Find the first SE onset time for each channel
        for row, col in self.active_channels:
            channel_data = self.data[row - 1, col - 1]
            se_times = channel_data["SETimes"]
            if se_times.size > 0:
                se_onset_times[(row, col)] = se_times[0][0]
            else:
                channels_without_se.append((row, col))

        # Sort channels by their SE onset times
        sorted_channels = sorted(se_onset_times.items(), key=lambda x: x[1])

        # Cluster channels with SE
        clusters = []
        current_cluster = []
        current_cluster_start_time = None

        for channel, onset_time in sorted_channels:
            if (
                current_cluster_start_time is None
                or onset_time - current_cluster_start_time <= time_window
            ):
                current_cluster.append(channel)
                if current_cluster_start_time is None:
                    current_cluster_start_time = onset_time
            else:
                clusters.append(current_cluster)
                current_cluster = [channel]
                current_cluster_start_time = onset_time

        # Add the last cluster if it's not empty
        if current_cluster:
            clusters.append(current_cluster)

        # Add a NEW group for all channels without SE
        if channels_without_se:
            clusters.append(channels_without_se)

        # Update the active_channels list to reflect the new clustering
        self.active_channels = [channel for cluster in clusters for channel in cluster]

        # Update the groups based on the new clusters
        self.groups = []
        for i, cluster in enumerate(clusters):
            color = self.get_next_color()
            self.groups.append(Group(cluster, None, color, i + 1))  # Set image to None

        # Regenerate and update the raster plot
        self.generate_raster()
        self.update_raster_plot_data()

        return clusters

    def get_next_color(self):
        if self.color_index < len(self.predefined_colors):
            color = self.predefined_colors[self.color_index]
            # Normalize the rgb values to be between 0 and 1
            color = tuple([val / 255 for val in color])
            self.color_index += 1
        else:
            color = self.generate_random_color()
        return color

    def generate_random_color(self):
        hue = np.random.rand()
        saturation = 0.7 + np.random.rand() * 0.3  # 0.7 to 1.0
        value = 0.7 + np.random.rand() * 0.3  # 0.7 to 1.0
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        return rgb
