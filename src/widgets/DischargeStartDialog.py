from PyQt5.QtGui import QBrush, QColor, QPainterPath, QRadialGradient
import h5py
from typing_extensions import List
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QGraphicsItem,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt5.QtCore import QEvent, QRectF, Qt
import numpy as np
from widgets.DischargeStartArea import DischargeStartArea
import pyqtgraph as pg


class TransparentEllipseItem(QGraphicsItem):
    def __init__(self, x, y, width, height, brush):
        super().__init__()
        self.rect = QRectF(0, 0, width, height)
        self.brush = brush
        self.setPos(x - width / 2, y - height / 2)

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect)

    def shape(self):
        return QPainterPath()


class DischargeStartDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window, Qt.Window)
        self.main_window = main_window
        self.setWindowTitle("Discharge Start Viewer")
        self.setMinimumSize(800, 500)  # Increased size to accommodate the histogram

        self.discharge_start_areas: List[DischargeStartArea] = []
        self.discharge_start_items = []

        # Set window flags to keep it on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        main_layout = QHBoxLayout()  # Changed to QHBoxLayout
        self.setLayout(main_layout)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget)

        bin_layout = QHBoxLayout()
        left_layout.addLayout(bin_layout)

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
        left_layout.addWidget(self.num_discharge_label)

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Bins", "Discharges"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.viewport().installEventFilter(self)
        left_layout.addWidget(self.table)

        # Add checkbox for filtering empty bins
        self.filter_empty_bins = QCheckBox("Filter empty bins")
        self.filter_empty_bins.setChecked(True)
        self.filter_empty_bins.stateChanged.connect(self.update_table)
        left_layout.addWidget(self.filter_empty_bins)

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

        # Create histogram widget
        self.histogram = pg.PlotWidget()
        self.histogram.setBackground("w")
        self.histogram.setTitle("Discharge Distribution")
        self.histogram.setLabel("left", "Number of Discharges")
        self.histogram.setLabel("bottom", "Time (s)")
        main_layout.addWidget(self.histogram)

        # Initial table and histogram update
        self.update_table()

    def show(self):
        super().show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def eventFilter(self, source, event):
        if source is self.table.viewport() and event.type() == QEvent.MouseButtonPress:
            item = self.table.itemAt(event.pos())
            if item is not None:
                row = self.table.row(item)
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ControlModifier:
                    self.table.setSelectionMode(QAbstractItemView.MultiSelection)
                elif modifiers == Qt.ShiftModifier:
                    self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
                else:
                    self.table.setSelectionMode(QAbstractItemView.SingleSelection)
                    self.table.clearSelection()
                self.table.selectRow(row)
                print(f"Row {row} selected")  # Debug print
                self.on_selection_changed()
                return True
        return super().eventFilter(source, event)

    def update_discharges(self):
        if len(self.discharge_start_areas) == 0:
            self.num_discharge_label.setText("Number of Discharges: 0")
            return
        print("Updating discharges")
        self.num_discharge_label.setText(
            f"Number of Discharges: {len(self.discharge_start_areas)}"
        )
        self.update_table()
        self.draw_selected_bins(
            sorted(set(index.row() for index in self.table.selectedIndexes()))
        )

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
        bin_data = self.get_bin_data()

        if self.filter_empty_bins.isChecked():
            bin_data = [data for data in bin_data if data[2] > 0]

        self.table.setRowCount(len(bin_data))

        for row, (start_time, end_time, discharge_count) in enumerate(bin_data):
            bin_item = QTableWidgetItem(f"{start_time}-{end_time} s")
            bin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, bin_item)

            discharge_item = QTableWidgetItem(f"{discharge_count}")
            discharge_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, discharge_item)

        self.table.resizeColumnsToContents()
        self.update_histogram(bin_data)

    def update_histogram(self, bin_data):
        self.histogram.clear()

        x = [data[0] for data in bin_data]
        y = [data[2] for data in bin_data]

        bar_graph = pg.BarGraphItem(
            x=x, height=y, width=self.bins_size.value() * 0.9, brush="b"
        )
        self.histogram.addItem(bar_graph)

    def get_bin_data(self):
        num_bins = self.num_bins.value()
        bins_size = self.bins_size.value()
        bin_data = []

        for i in range(num_bins):
            start_time = i * bins_size
            end_time = (i + 1) * bins_size
            discharge_count = sum(
                1
                for discharge in self.discharge_start_areas
                if start_time <= discharge.timestamp < end_time
            )
            bin_data.append((start_time, end_time, discharge_count))

        print(f"Bin data before filtering: {bin_data}")  # Debug print
        return bin_data

    def on_selection_changed(self):
        selected_rows = sorted(
            set(index.row() for index in self.table.selectedIndexes())
        )
        print(f"Selected rows: {selected_rows}")  # Debug print
        self.draw_selected_bins(selected_rows)

    def draw_selected_bins(self, selected_rows):
        scene = self.main_window.grid_widget.scene
        for item in self.discharge_start_items:
            scene.removeItem(item)
        self.discharge_start_items.clear()

        bin_data = self.get_bin_data()
        if self.filter_empty_bins.isChecked():
            bin_data = [data for data in bin_data if data[2] > 0]

        print(f"Drawing bins for rows: {selected_rows}")
        print(
            f"Total number of discharge start areas: {len(self.discharge_start_areas)}"
        )

        for row in selected_rows:
            start_time, end_time, _ = bin_data[row]
            print(f"Bin {row}: Start time: {start_time}, End time: {end_time}")

            matching_discharges = [
                discharge
                for discharge in self.discharge_start_areas
                if start_time <= discharge.timestamp < end_time
            ]
            print(
                f"Number of matching discharges in bin {row}: {len(matching_discharges)}"
            )

            for discharge in matching_discharges:
                self.draw_discharge_point(scene, discharge)

        print(f"Total discharge points drawn: {len(self.discharge_start_items)}")

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
            self.main_window.last_found_discharge_time = current_time
            self.main_window.pause_playback()
            self.save_discharge_start_areas_to_hdf5()

    def draw_discharge_point(self, scene, discharge):
        gradient = QRadialGradient(
            discharge.width / 2,
            discharge.height / 2,
            max(discharge.width, discharge.height) / 2,
        )
        gradient.setColorAt(
            0, QColor(255, 0, 0, int(255 * 0.3))
        )  # Increased opacity for visibility
        gradient.setColorAt(1, QColor(255, 0, 0, 0))

        discharge_point = TransparentEllipseItem(
            discharge.x,
            discharge.y,
            discharge.width,
            discharge.height,
            QBrush(gradient),
        )
        scene.addItem(discharge_point)
        self.discharge_start_items.append(discharge_point)
        print(
            f"Discharge point drawn at ({discharge.x}, {discharge.y}), time: {discharge.timestamp}"
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control or event.key() == Qt.Key_Meta:
            self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        elif event.key() == Qt.Key_Shift:
            self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in (Qt.Key_Control, Qt.Key_Meta, Qt.Key_Shift):
            self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        super().keyReleaseEvent(event)
