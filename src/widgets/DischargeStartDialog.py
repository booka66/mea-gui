from PyQt5.QtGui import QBrush, QColor, QPen, QRadialGradient
import h5py
from typing_extensions import List
from PyQt5.QtWidgets import (
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtCore import Qt
import numpy as np
from widgets.DischargeStartArea import DischargeStartArea


class DischargeStartDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window, Qt.Window)
        self.main_window = main_window
        self.setWindowTitle("Discharge Start Viewer")
        self.setMinimumSize(400, 300)

        self.discharge_start_areas: List[DischargeStartArea] = []
        self.discharge_start_items = []

        # Set window flags to keep it on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        bin_layout = QHBoxLayout()
        main_layout.addLayout(bin_layout)

        num_bins_label = QLabel("Number of Bins:")
        bin_layout.addWidget(num_bins_label)
        self.num_bins = QSpinBox()
        self.num_bins.setMinimum(1)
        self.num_bins.setMaximum(10000)
        bin_layout.addWidget(self.num_bins)

        bins_size_label = QLabel("Bins Size (s):")
        bin_layout.addWidget(bins_size_label)
        self.bins_size = QSpinBox()
        self.bins_size.setMinimum(1)
        self.bins_size.setMaximum(10000)
        bin_layout.addWidget(self.bins_size)

        self.num_discharge_label = QLabel("Number of Discharges: 0")
        main_layout.addWidget(self.num_discharge_label)

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Bins", "Discharges"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        main_layout.addWidget(self.table)

        self.num_bins.valueChanged.connect(self.update_bins_size)
        self.bins_size.valueChanged.connect(self.update_num_bins)
        self.num_bins.valueChanged.connect(self.update_table)
        self.bins_size.valueChanged.connect(self.update_table)

        self.num_bins.setValue(10)
        num_bins = self.num_bins.value()
        if num_bins > 0:
            new_bins_size = self.main_window.recording_length / num_bins
            self.bins_size.blockSignals(True)
            self.bins_size.setValue(int(new_bins_size))
            self.bins_size.blockSignals(False)

        # Initial table update
        self.update_table()

    def show(self):
        super().show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def update_discharges(self):
        if len(self.discharge_start_areas) == 0:
            self.num_discharge_label.setText("Number of Discharges: 0")
            return
        print("Updating discharges")
        self.num_discharge_label.setText(
            f"Number of Discharges: {len(self.discharge_start_areas)}"
        )
        self.update_table()
        self.draw_discharge_start_areas()

    def update_bins_size(self):
        if not self.num_bins.hasFocus():
            return
        num_bins = self.num_bins.value()
        if num_bins > 0:
            new_bins_size = self.main_window.recording_length / num_bins
            self.bins_size.blockSignals(True)
            self.bins_size.setValue(int(new_bins_size))
            self.bins_size.blockSignals(False)

    def update_num_bins(self):
        if not self.bins_size.hasFocus():
            return
        bins_size = self.bins_size.value()
        if bins_size > 0:
            new_num_bins = self.main_window.recording_length / bins_size
            self.num_bins.blockSignals(True)
            self.num_bins.setValue(int(new_num_bins))
            self.num_bins.blockSignals(False)

    def clear_discharge_start_areas_from_hdf5(self):
        try:
            with h5py.File(self.main_window.file_path, "a") as f:
                if "discharge_start_areas" in f:
                    del f["discharge_start_areas"]
        except Exception as e:
            print(f"Error clearing discharge start areas from HDF: {e}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Error clearing discharge start areas from HDF file. Double check that the file is not open in another program as that apparently is a big no-no."
            )
            msg.setInformativeText(f"Error: {e}")
            msg.setWindowTitle("Error")
            msg.exec_()

    def save_discharge_start_areas_to_hdf5(self):
        if len(self.discharge_start_areas) == 0:
            return
        try:
            with h5py.File(self.main_window.file_path, "a") as f:
                if "discharge_start_areas" not in f:
                    f.create_group("discharge_start_areas")
                areas_group = f["discharge_start_areas"]
                for discharge_start_area in self.discharge_start_areas:
                    if discharge_start_area.id in areas_group:
                        del areas_group[discharge_start_area.id]
                    area_dataset = areas_group.create_dataset(
                        discharge_start_area.id, data=[0], shape=(1,)
                    )
                    area_dataset.attrs["timestamp"] = discharge_start_area.timestamp
                    area_dataset.attrs["centroid_x"] = discharge_start_area.x
                    area_dataset.attrs["centroid_y"] = discharge_start_area.y
                    area_dataset.attrs["width"] = discharge_start_area.width
                    area_dataset.attrs["height"] = discharge_start_area.height
                    area_dataset.attrs["involved_channels"] = [
                        [cell.row, cell.col]
                        for cell in discharge_start_area.involved_channels
                    ]
        except Exception as e:
            print(f"Error saving discharge start areas to HDF: {e}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Error saving discharge start areas to HDF file. Double check that the file is not open in another program as that apparently is a big no-no."
            )
            msg.setInformativeText(f"Error: {e}")
            msg.setWindowTitle("Error")
            msg.exec_()

    def update_table(self):
        num_bins = self.num_bins.value()
        bins_size = self.bins_size.value()
        self.table.setRowCount(num_bins)

        for i in range(num_bins):
            start_time = i * bins_size
            end_time = (i + 1) * bins_size
            bin_item = QTableWidgetItem(f"{start_time}-{end_time} s")
            bin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, bin_item)

            discharge_count = 0
            for discharge in self.discharge_start_areas:
                if start_time < discharge.timestamp < end_time:
                    discharge_count += 1

            discharge_item = QTableWidgetItem(f"{discharge_count}")
            discharge_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, discharge_item)

        self.table.resizeColumnsToContents()

    def create_discharge_start_area(self, current_time, top_cells):
        points = np.array([(cell.row, cell.col) for cell in top_cells])
        new_centroid = np.average(
            points,
            axis=0,
            weights=[cell.get_luminance() for cell in top_cells],
        )
        highest_cell = max(top_cells, key=lambda cell: cell.row)
        lowest_cell = min(top_cells, key=lambda cell: cell.row)
        height = (highest_cell.row - lowest_cell.row + 1) * highest_cell.rect().height()

        leftmost_cell = min(top_cells, key=lambda cell: cell.col)
        rightmost_cell = max(top_cells, key=lambda cell: cell.col)
        width = (
            rightmost_cell.col - leftmost_cell.col + 1
        ) * rightmost_cell.rect().width()

        if width <= 400 and height <= 400:
            centroid_x = new_centroid[1] * rightmost_cell.rect().width()
            centroid_y = new_centroid[0] * highest_cell.rect().height()

            self.discharge_start_areas.append(
                DischargeStartArea(
                    current_time,
                    centroid_x,
                    centroid_y,
                    width,
                    height,
                    top_cells,
                )
            )

    def draw_discharge_start_areas(self):
        scene: QGraphicsScene = self.main_window.grid_widget.scene

        # Remove previous discharge start areas
        for item in self.discharge_start_items:
            scene.removeItem(item)
            self.discharge_start_items.remove(item)

        for discharge in self.discharge_start_areas:
            gradient = QRadialGradient(
                discharge.width / 2,
                discharge.height / 2,
                max(discharge.width, discharge.height) / 2,
            )
            gradient.setColorAt(0, QColor(255, 0, 0, int(255 * 0.03)))
            gradient.setColorAt(1, QColor(255, 0, 0, 0))

            discharge_point = QGraphicsEllipseItem(
                0, 0, discharge.width, discharge.height
            )
            discharge_point.setBrush(QBrush(gradient))
            discharge_point.setPen(QPen(Qt.NoPen))

            discharge_point.setPos(
                discharge.x - discharge.width / 2,
                discharge.y - discharge.height / 2,
            )

            scene.addItem(discharge_point)
