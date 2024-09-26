from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QRadialGradient
import h5py
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QGraphicsItem,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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
from matplotlib import cm

POINT_SIZE = 3


class TransparentEllipseItem(QGraphicsItem):
    def __init__(self, x, y, width, height, brush):
        super().__init__()
        self.rect = QRectF(0, 0, width, height)
        self.brush = brush
        self.setPos(x - width / 2, y - height / 2)
        self.color = brush.color()
        self.width = width
        self.height = height

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect)

    def shape(self):
        return QPainterPath()

    def get_color(self):
        return self.color


class DischargeStartDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window, Qt.Window)
        self.main_window = main_window
        self.setWindowTitle("Discharge Start Viewer")
        self.setMinimumSize(800, 500)

        self.current_time = None
        self.discharge_start_areas: list[DischargeStartArea] = []
        self.discharge_start_items = []
        self.colormap = cm.get_cmap("viridis")

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        main_layout = QHBoxLayout()
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

        discharge_row = QHBoxLayout()
        left_layout.addLayout(discharge_row)

        self.num_discharge_label = QLabel("Number of Discharges: 0")
        discharge_row.addWidget(self.num_discharge_label)

        self.draw_points_box = QCheckBox("Draw Points")
        self.draw_points_box.setChecked(True)
        discharge_row.addWidget(self.draw_points_box)

        self.draw_areas_box = QCheckBox("Draw Areas")
        self.draw_areas_box.setChecked(True)
        discharge_row.addWidget(self.draw_areas_box)

        self.load_discharge_start_areas_button = QPushButton("Load Discharges")
        self.load_discharge_start_areas_button.clicked.connect(
            self.load_discharge_start_areas_from_hdf5
        )
        discharge_row.addWidget(self.load_discharge_start_areas_button)

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

        self.filter_empty_bins = QCheckBox("Filter empty bins")
        self.filter_empty_bins.setChecked(True)
        self.filter_empty_bins.stateChanged.connect(self.update_table)
        left_layout.addWidget(self.filter_empty_bins)

        self.histogram = pg.PlotWidget()
        self.histogram.setBackground("w")
        self.histogram.setTitle("Discharge Distribution")
        self.histogram.setLabel("left", "Number of Discharges")
        self.histogram.setLabel("bottom", "Time (s)")
        main_layout.addWidget(self.histogram)

        self.num_bins.valueChanged.connect(self.update_bins_size)
        self.bins_size.valueChanged.connect(self.update_num_bins)
        self.num_bins.valueChanged.connect(self.update_table)
        self.bins_size.valueChanged.connect(self.update_table)
        self.draw_points_box.stateChanged.connect(self.on_selection_changed)
        self.draw_areas_box.stateChanged.connect(self.on_selection_changed)

        self.num_bins.setValue(10)
        num_bins = self.num_bins.value()
        if num_bins > 0:
            new_bins_size = self.main_window.recording_length / num_bins
            self.bins_size.blockSignals(True)
            self.bins_size.setValue(int(new_bins_size))
            self.bins_size.blockSignals(False)

        self.update_table()

    def show(self):
        super().show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.main_window.track_discharge_beginnings = True

    def closeEvent(self, event):
        self.main_window.track_discharge_beginnings = False
        self.clear_discharges_from_scene(self.main_window.grid_widget.scene)

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
                self.on_selection_changed()
                return True
        return super().eventFilter(source, event)

    def update_discharges(self):
        if len(self.discharge_start_areas) == 0:
            self.num_discharge_label.setText("Number of Discharges: 0")
            return
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

    def load_discharge_start_areas_from_hdf5(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "Loading discharge start areas from the file will clear the current ones."
        )
        msg.setWindowTitle("Warning")
        response = msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if response == QMessageBox.Cancel:
            return

        self.discharge_start_areas.clear()
        self.update_discharges()

        try:
            with h5py.File(self.main_window.file_path, "r") as f:
                if "discharge_start_areas" in f:
                    areas_group = f["discharge_start_areas"]
                    for id in areas_group:
                        try:
                            area_dataset = areas_group[id]
                            timestamp = area_dataset.attrs["timestamp"]
                            centroid_x = area_dataset.attrs["centroid_x"]
                            centroid_y = area_dataset.attrs["centroid_y"]
                            width = area_dataset.attrs["width"]
                            height = area_dataset.attrs["height"]
                            involved_channels = area_dataset.attrs["involved_channels"]
                            self.discharge_start_areas.append(
                                DischargeStartArea(
                                    timestamp,
                                    centroid_x,
                                    centroid_y,
                                    width,
                                    height,
                                    involved_channels,
                                )
                            )
                        except Exception as e:
                            print(f"Error loading discharge start area: {e}")
                            continue
            self.update_discharges()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Error loading discharge start areas from HDF file. Double check that the file is not open in another program as that apparently is a big no-no."
            )
            msg.setInformativeText(f"Error: {e}")
            msg.setWindowTitle("Error")
            msg.exec_()

    def clear_discharge_start_areas_from_hdf5(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "Are you sure you want to clear all discharge start areas from the HDF file? This action cannot be undone"
        )
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Abort)
        response = msg.exec_()
        if response == QMessageBox.Abort:
            return
        try:
            with h5py.File(self.main_window.file_path, "a") as f:
                if "discharge_start_areas" in f:
                    del f["discharge_start_areas"]
        except Exception as e:
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
                    try:
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
                        del areas_group[discharge_start_area.id]
                        print(f"Error saving discharge start area: {e}")
                        continue
        except Exception as e:
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

        return bin_data

    def on_selection_changed(self):
        selected_rows = sorted(
            set(index.row() for index in self.table.selectedIndexes())
        )
        self.draw_selected_bins(selected_rows)

    def clear_discharges_from_scene(self, scene):
        for item in self.discharge_start_items:
            if item.scene() == scene:
                scene.removeItem(item)
        self.discharge_start_items.clear()

    def draw_bin(self, bin_index, scene=False):
        color = self.colormap(0)
        if not scene:
            scene = self.main_window.grid_widget.scene

        self.clear_discharges_from_scene(scene)

        bin_data = self.get_bin_data()
        if self.filter_empty_bins.isChecked():
            bin_data = [data for data in bin_data if data[2] > 0]

        start_time, end_time, _ = bin_data[bin_index]
        matching_discharges = [
            discharge
            for discharge in self.discharge_start_areas
            if start_time <= discharge.timestamp < end_time
        ]

        for discharge in matching_discharges:
            self.draw_discharge_point(scene, discharge, color)

    def draw_selected_bins(self, selected_rows, scene=False):
        if not scene:
            scene = self.main_window.grid_widget.scene

        self.clear_discharges_from_scene(scene)

        bin_data = self.get_bin_data()
        if self.filter_empty_bins.isChecked():
            bin_data = [data for data in bin_data if data[2] > 0]

        for i, row in enumerate(selected_rows):
            start_time, end_time, _ = bin_data[row]
            if len(selected_rows) == 1:
                color = self.colormap(0)
            else:
                color = self.colormap(i / (len(selected_rows) - 1))

            matching_discharges = [
                discharge
                for discharge in self.discharge_start_areas
                if start_time <= discharge.timestamp < end_time
            ]

            for discharge in matching_discharges:
                self.draw_discharge_point(scene, discharge, color)

    def draw_discharge_point(self, scene, discharge, color):
        rgba_color = [int(c * 255) for c in color]
        if self.draw_areas_box.isChecked():
            gradient = QRadialGradient(
                discharge.width / 2,
                discharge.height / 2,
                max(discharge.width, discharge.height) / 2,
            )
            gradient.setColorAt(0, QColor(*rgba_color[:3], int(255 * 0.1)))
            gradient.setColorAt(1, QColor(*rgba_color[:3], 0))

            discharge_area = TransparentEllipseItem(
                discharge.x,
                discharge.y,
                discharge.width,
                discharge.height,
                QBrush(gradient),
            )
            scene.addItem(discharge_area)
            self.discharge_start_items.append(discharge_area)

        if self.draw_points_box.isChecked():
            discharge_point = TransparentEllipseItem(
                discharge.x,
                discharge.y,
                POINT_SIZE,
                POINT_SIZE,
                QBrush(QColor(*rgba_color)),
            )
            scene.addItem(discharge_point)
            self.discharge_start_items.append(discharge_point)

    def draw_discharge_starts_on_image(self, painter: QPainter):
        # Save the visible items to the scene
        print(f"Total discharge start items: {len(self.discharge_start_items)}")
        for item in self.discharge_start_items:
            if isinstance(item, TransparentEllipseItem):
                pos = item.pos()
                painter.translate(pos.x(), pos.y())
                item.paint(painter, None, None)
                painter.translate(-pos.x(), -pos.y())

    def create_discharge_start_area(self, current_time):
        involved_channels = []
        for row in self.main_window.grid_widget.cells:
            for cell in row:
                if cell.is_high_luminance:
                    involved_channels.append(cell)

        print(f"Involved channels: {len(involved_channels)}")

        points = np.array([(cell.row, cell.col) for cell in involved_channels])
        new_centroid = np.average(
            points,
            axis=0,
            # weights=[cell.get_luminance() for cell in involved_channels],
        )
        highest_cell = max(involved_channels, key=lambda cell: cell.row)
        lowest_cell = min(involved_channels, key=lambda cell: cell.row)
        height = (highest_cell.row - lowest_cell.row + 1) * highest_cell.rect().height()

        leftmost_cell = min(involved_channels, key=lambda cell: cell.col)
        rightmost_cell = max(involved_channels, key=lambda cell: cell.col)
        width = (
            rightmost_cell.col - leftmost_cell.col + 1
        ) * rightmost_cell.rect().width()

        centroid_x = new_centroid[1] * rightmost_cell.rect().width()
        centroid_y = new_centroid[0] * highest_cell.rect().height()

        self.discharge_start_areas.append(
            DischargeStartArea(
                current_time,
                centroid_x,
                centroid_y,
                width,
                height,
                involved_channels,
            )
        )
        self.save_discharge_start_areas_to_hdf5()

    def confirm(self, accepted):
        print("confirm")
        if accepted:
            print("accepted")
            self.create_discharge_start_area(
                self.main_window.progress_bar.value() / self.main_window.sampling_rate
            )
            self.update_discharges()

        for cell in self.main_window.grid_widget.cells:
            for cell in cell:
                cell.is_high_luminance = False

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
