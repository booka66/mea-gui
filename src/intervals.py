import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import h5py
import numpy as np


class ClickableBarGraphItem(pg.BarGraphItem):
    def __init__(self, **opts):
        super().__init__(**opts)
        self.main_window = opts.get("main_window")
        self.current_popup = None

    def mouseClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = np.round(event.pos().x()).astype(int)
            if 0 <= index < len(self.main_window.times):
                time = self.main_window.times[index]
                self.create_popup_graph(index, time, event.screenPos())

    def create_popup_graph(self, index, time, mouse_pos):
        if self.current_popup:
            self.current_popup.close()

        prev_start_point = self.main_window.start_points[index - 1]
        curr_start_point = self.main_window.start_points[index]
        y = [prev_start_point[0], curr_start_point[0]]
        x = [prev_start_point[1], curr_start_point[1]]

        print(f"Discharge {index} start point: {curr_start_point}")
        print(f"Discharge {index - 1} start point: {prev_start_point}")
        print(f"Time since last discharge: {time}")

        popup = pg.PlotWidget()
        popup.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        popup.setBackground("w")
        popup.getPlotItem().invertY(True)  # Invert the y-axis
        scatter_plot = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen(None), brush=pg.mkBrush("r")
        )
        scatter_plot.setData(x=x, y=y)
        popup.addItem(scatter_plot)

        # Set a fixed graph window view size (64x64)
        popup.setRange(xRange=[0, 64], yRange=[0, 64])
        popup.setTitle(f"Discharge {index + 1}")
        popup.setLabel("left", "Time (s)")
        popup.setLabel("bottom", "Discharge")
        popup.setFixedSize(300, 200)
        popup.move(
            self.main_window.pos().x() + self.main_window.width() - popup.width(),
            self.main_window.pos().y(),
        )

        popup.show()

        self.current_popup = popup


class IntervalViewer(QDialog):
    def __init__(self, x, y, start_points):
        super().__init__()
        self.times = y
        self.start_points = start_points
        self.graph_widget = pg.PlotWidget()
        self.setCentralWidget(self.graph_widget)

        # Create the bar graph
        bargraph = ClickableBarGraphItem(
            x=x, height=y, width=0.6, brush="b", main_window=self
        )
        self.graph_widget.addItem(bargraph)

        # Set labels
        self.graph_widget.setLabel("left", "Time since last discharge (s)")
        self.graph_widget.setLabel("bottom", "Discharge number")
        self.graph_widget.setTitle("Time Between Discharges")


def get_discharge_data(file_path):
    eps = 100  # ms
    with h5py.File(file_path, "r") as f:
        tracked_discharges = f["tracked_discharges"]
        for key in tracked_discharges.keys():
            if key != "1985.71_2985.36":
                continue
            time_range = tracked_discharges[key]
            discharge_data = [data for data in time_range.values() if data is not None]
            sorted_discharge_data = sorted(
                discharge_data, key=lambda x: x["start_time"][()]
            )
            sorted_times = [
                data["time_since_last_discharge"][()] for data in sorted_discharge_data
            ]
            indices_to_remove = []
            for i in range(1, len(sorted_times) - 1):
                if sorted_times[i] < eps:
                    print(f"Discharge {i} is too close to discharge {i - 1}")
                    sorted_times[i] = sorted_times[i - 1]
                    print("Removing discharge", i)
                    indices_to_remove.append(i)

            sorted_times = [
                time
                for i, time in enumerate(sorted_times)
                if i not in indices_to_remove
            ]

            sorted_start_points = [
                data["start_point"][()]
                for i, data in enumerate(sorted_discharge_data)
                if i not in indices_to_remove
            ]
    return sorted_times, sorted_start_points


if __name__ == "__main__":
    file_path = "/Users/booka66/Jake-Squared/Sz_SE_Detection/Slice1_11-9-20_Neo_hipp_resample_300.brw"

    # Get discharge data
    times, start_points = get_discharge_data(file_path)

    # Create x-axis values (discharge numbers)
    x = np.arange(len(times))

    # Create the application and window
    app = QApplication(sys.argv)
    main = IntervalViewer(x, times, start_points)
    main.show()

    # Print average time between discharges
    print(f"Average time between discharges: {sum(times) / len(times)}")

    sys.exit(app.exec_())
