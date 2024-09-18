from pathlib import Path
from PyQt5.QtGui import QBrush, QImage, QIntValidator, QPainter, QPixmap
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from PyQt5.QtCore import QRect, QSize, Qt
import os

from helpers.Constants import BACKGROUND


class SaveChannelPlotsDialog(QDialog):
    def __init__(self, parent=None, plot_index=None):
        super().__init__(parent)
        self.parent = parent
        self.plot_index = plot_index
        self.setWindowTitle("Save Channel Plots")
        self.setMinimumWidth(300)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Channel selection
        self.channel_checkboxes = []
        if (
            self.plot_index is not None
            and self.parent.plotted_channels[self.plot_index] is not None
        ):
            row, col = (
                self.parent.plotted_channels[self.plot_index].row,
                self.parent.plotted_channels[self.plot_index].col,
            )
            checkbox = QCheckBox(f"Channel ({row + 1}, {col + 1})")
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)
        else:
            for i in range(4):
                if self.parent.plotted_channels[i] is not None:
                    row, col = (
                        self.parent.plotted_channels[i].row,
                        self.parent.plotted_channels[i].col,
                    )
                    checkbox = QCheckBox(f"Channel ({row + 1}, {col + 1})")
                    checkbox.setChecked(True)
                    layout.addWidget(checkbox)
                    self.channel_checkboxes.append(checkbox)

            # Select All checkbox
            self.select_all_checkbox = QCheckBox("Select All")
            self.select_all_checkbox.setChecked(True)
            self.select_all_checkbox.stateChanged.connect(self.toggle_all_channels)
            layout.addWidget(self.select_all_checkbox)

        # Update the file format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("File Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "SVG"])
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Hide lines?
        hide_lines_layout = QHBoxLayout()
        hide_lines_layout.addWidget(QLabel("Hide Playheads:"))
        self.hide_lines_checkbox = QCheckBox()
        self.hide_lines_checkbox.setChecked(True)
        hide_lines_layout.addWidget(self.hide_lines_checkbox)
        layout.addLayout(hide_lines_layout)

        # Scale (when you hover it should say "Scale of the image")
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))
        self.scale_input = QLineEdit("4")
        self.scale_input.setValidator(QIntValidator())
        self.scale_input.setToolTip(
            "Scale of the image (e.g. 4 for 4x scale)\n10 is probably all you'll ever need"
        )
        scale_layout.addWidget(self.scale_input)
        layout.addLayout(scale_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_plots)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def toggle_all_channels(self, state):
        for checkbox in self.channel_checkboxes:
            checkbox.setChecked(state == Qt.Checked)

    def save_plots(self):
        selected_plots = [
            self.parent.graph_widget.plot_widgets[i]
            for i, checkbox in enumerate(self.channel_checkboxes)
            if checkbox.isChecked()
        ]

        if not selected_plots:
            QMessageBox.warning(
                self, "No Selection", "Please select at least one channel to save."
            )
            return

        file_format = self.format_combo.currentText().lower()
        file_filter = f"{file_format.upper()} Files (*.{file_format})"
        default_filename = f"channel_plots.{file_format}"
        scale_factor = int(self.scale_input.text())
        hide_lines = self.hide_lines_checkbox.isChecked()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Channel Plots",
            os.path.join(os.path.expanduser("~"), "Downloads", default_filename),
            file_filter,
        )

        if file_path:
            save_plots_to_image(
                self.parent,
                selected_plots,
                file_path,
                file_format,
                scale_factor,
                hide_lines,
            )
            QMessageBox.information(
                self, "Save Completed", f"Channel plots saved to {file_path}"
            )
            self.accept()


def save_mea_with_plots(self):
    options = QFileDialog.Options()
    file_filter = "PNG Files (*.png);;SVG Files (*.svg)"
    default_filename = "mea_with_plots"
    file_path, selected_filter = QFileDialog.getSaveFileName(
        self,
        "Save MEA with Channel Plots",
        os.path.join(os.path.expanduser("~"), "Downloads", default_filename),
        file_filter,
        options=options,
    )

    if file_path:
        # Create a dialog to select the channels to save
        channel_dialog = QDialog(self)
        channel_dialog.setWindowTitle("Select Channels")
        channel_layout = QVBoxLayout()

        channel_checkboxes = []
        for i in range(4):
            if self.plotted_channels[i] is not None:
                row, col = (
                    self.plotted_channels[i].row,
                    self.plotted_channels[i].col,
                )
                checkbox = QCheckBox(f"Channel ({row + 1}, {col + 1})")
                checkbox.setChecked(True)
                channel_layout.addWidget(checkbox)
                channel_checkboxes.append(checkbox)

        select_all_checkbox = QCheckBox("Select All")
        select_all_checkbox.setChecked(True)
        select_all_checkbox.stateChanged.connect(
            lambda state: select_all_channels(state, channel_checkboxes)
        )
        channel_layout.addWidget(select_all_checkbox)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(channel_dialog.accept)
        button_layout.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(channel_dialog.reject)
        button_layout.addWidget(cancel_button)

        channel_layout.addLayout(button_layout)
        channel_dialog.setLayout(channel_layout)

        if channel_dialog.exec() == QDialog.Accepted:
            selected_plots = []
            for i, checkbox in enumerate(channel_checkboxes):
                if checkbox.isChecked():
                    selected_plots.append(self.graph_widget.plot_widgets[i])

            if selected_plots:
                save_mea_with_selected_plots(
                    self, selected_plots, file_path, selected_filter
                )


def save_mea_with_selected_plots(self, selected_plots, file_path, file_format):
    mea_width = self.grid_widget.width()
    mea_height = self.grid_widget.height()

    # Determine the width of the plots
    plot_width = max(p.width() for p in selected_plots)

    image_width = mea_width + plot_width
    image_height = mea_height

    # Create a QImage to draw on
    image = QImage(image_width, image_height, QImage.Format_ARGB32)
    image.fill(Qt.white)

    painter = QPainter(image)

    # Draw MEA grid
    grid_pixmap = self.grid_widget.grab()
    painter.drawPixmap(0, 0, grid_pixmap)

    # Draw plots vertically stacked without spacing
    for i, plot_widget in enumerate(selected_plots[:4]):  # Limit to 4 plots
        x = mea_width
        y = i * (mea_height // 4)  # Divide total height by 4 for each plot
        plot_height = mea_height // 4  # Height of each plot

        # Grab the plot and scale it to fit exactly
        plot_pixmap = plot_widget.grab()
        scaled_pixmap = plot_pixmap.scaled(
            plot_width, plot_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )

        painter.drawPixmap(x, y, scaled_pixmap)

    painter.end()

    if file_format == "SVG Files (*.svg)":
        # Save as SVG
        svg_generator = QSvgGenerator()
        svg_generator.setFileName(file_path)
        svg_generator.setSize(QSize(image_width, image_height))
        svg_generator.setViewBox(QRect(0, 0, image_width, image_height))

        svg_painter = QPainter(svg_generator)
        svg_painter.drawImage(QRect(0, 0, image_width, image_height), image)
        svg_painter.end()
    else:
        # Save as PNG
        image.save(file_path, "PNG")

    QMessageBox.information(
        self, "Save Completed", f"MEA with plots saved to {file_path}"
    )


def select_all_channels(state, channel_checkboxes):
    for checkbox in channel_checkboxes:
        checkbox.setChecked(state == Qt.Checked)


def save_plots_to_image(
    self,
    selected_plots,
    file_path,
    file_format,
    scale_factor=4,
    hide_red_lines=True,
):
    reshow_minimap = False
    if self.toggleMiniMapAction.isChecked():
        self.toggleMiniMapAction.setChecked(False)
        self.toggle_mini_map(self.toggleMiniMapAction.isChecked())
        reshow_minimap = True
    if hide_red_lines:
        self.graph_widget.hide_red_lines()

    total_height = sum(plot.height() for plot in selected_plots)
    max_width = max(plot.width() for plot in selected_plots)

    if file_format.lower() == "svg":
        svg_generator = QSvgGenerator()
        svg_generator.setFileName(file_path)
        svg_generator.setSize(QSize(max_width, total_height))
        svg_generator.setViewBox(QRect(0, 0, max_width, total_height))
        svg_generator.setTitle("Combined Plots")
        svg_generator.setDescription("Generated by Your Application")

        painter = QPainter(svg_generator)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        y_offset = 0
        for plot_widget in selected_plots:
            plot_pixmap = plot_widget.grab()
            painter.drawPixmap(0, y_offset, plot_pixmap)
            y_offset += plot_widget.height()

        painter.end()
    else:
        image = QImage(
            max_width * scale_factor,
            total_height * scale_factor,
            QImage.Format_ARGB32,
        )
        image.fill(Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        y_offset = 0
        for plot_widget in selected_plots:
            plot_pixmap = plot_widget.grab()

            scaled_pixmap = plot_pixmap.scaled(
                max_width * scale_factor,
                plot_widget.height() * scale_factor,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )

            painter.drawPixmap(
                0,
                y_offset * scale_factor,
                max_width * scale_factor,
                plot_widget.height() * scale_factor,
                scaled_pixmap,
            )
            y_offset += plot_widget.height()

        painter.end()

        image.save(file_path, "PNG", quality=100)

    if reshow_minimap:
        self.toggleMiniMapAction.setChecked(True)
        self.toggle_mini_map(self.toggleMiniMapAction.isChecked())
    if hide_red_lines:
        self.graph_widget.show_red_lines()


def open_save_grid_dialog(self):
    dialog = QDialog(self)
    dialog.setWindowTitle("Save Grid")
    dialog.setMinimumWidth(500)
    layout = QVBoxLayout(dialog)

    # File selection
    file_layout = QHBoxLayout()
    file_path_input = QLineEdit()
    file_path_input.setReadOnly(True)
    file_layout.addWidget(file_path_input)
    browse_button = QPushButton("Browse")
    browse_button.clicked.connect(lambda: select_file(file_path_input))
    file_layout.addWidget(browse_button)
    layout.addLayout(file_layout)

    # Set default path to Downloads folder
    base_name = os.path.basename(self.file_path)
    base_name = os.path.splitext(base_name)[0]
    default_path = str(Path.home() / "Downloads" / f"{base_name}_grid.png")
    file_path_input.setText(default_path)

    # Transparent background checkbox
    transparent_checkbox = QCheckBox("Transparent Background")
    transparent_checkbox.setChecked(True)
    layout.addWidget(transparent_checkbox)

    # Propagation checkboxes
    propagation_layout = QVBoxLayout()
    propagation_layout.addWidget(QLabel("Propagation:"))

    paths_checkbox = QCheckBox("Start/End Paths")
    paths_checkbox.setChecked(False)
    paths_checkbox.setEnabled(len(self.cluster_tracker.seizures) > 0)
    propagation_layout.addWidget(paths_checkbox)

    beginning_points_checkbox = QCheckBox("Beginning Points")
    beginning_points_checkbox.setChecked(False)
    beginning_points_checkbox.setEnabled(len(self.cluster_tracker.seizures) > 0)
    propagation_layout.addWidget(beginning_points_checkbox)

    heat_map_checkbox = QCheckBox("Heat Map")
    heat_map_checkbox.setChecked(False)
    heat_map_checkbox.setEnabled(len(self.cluster_tracker.seizures) > 0)
    propagation_layout.addWidget(heat_map_checkbox)

    seizure_beginnings_checkbox = QCheckBox("Seizure Beginnings")
    seizure_beginnings_checkbox.setChecked(False)
    seizure_beginnings_checkbox.setEnabled(
        hasattr(self.grid_widget, "seizure_beginnings")
    )
    propagation_layout.addWidget(seizure_beginnings_checkbox)

    discharge_start_areas_checkbox = QCheckBox("Discharge Start Areas")
    discharge_start_areas_checkbox.setChecked(False)
    discharge_start_areas_checkbox.setEnabled(
        len(self.discharge_start_dialog.discharge_start_areas) > 0
    )
    propagation_layout.addWidget(discharge_start_areas_checkbox)

    save_all_individually_checkbox = QCheckBox("Save All Individually")
    save_all_individually_checkbox.setChecked(False)
    save_all_individually_checkbox.setEnabled(len(self.cluster_tracker.seizures) > 0)
    propagation_layout.addWidget(save_all_individually_checkbox)

    save_all_individually_checkbox.stateChanged.connect(
        lambda state: paths_checkbox.setEnabled(state == Qt.Unchecked)
        or beginning_points_checkbox.setEnabled(state == Qt.Unchecked)
        or heat_map_checkbox.setEnabled(state == Qt.Unchecked)
        or seizure_beginnings_checkbox.setEnabled(state == Qt.Unchecked)
        or discharge_start_areas_checkbox.setEnabled(state == Qt.Unchecked)
    )
    layout.addLayout(propagation_layout)

    # Buttons
    button_layout = QHBoxLayout()
    save_button = QPushButton("Save")
    save_button.clicked.connect(
        lambda: save_grid(
            self,
            dialog,
            file_path_input.text(),
            transparent_checkbox,
            paths_checkbox,
            beginning_points_checkbox,
            heat_map_checkbox,
            seizure_beginnings_checkbox,
            discharge_start_areas_checkbox,
            save_all_individually_checkbox,
        )
    )
    cancel_button = QPushButton("Cancel")
    cancel_button.clicked.connect(dialog.reject)
    button_layout.addWidget(save_button)
    button_layout.addWidget(cancel_button)
    layout.addLayout(button_layout)

    dialog.setLayout(layout)
    dialog.exec()


def select_file(file_path_input):
    initial_path = Path(file_path_input.text())
    file_path, _ = QFileDialog.getSaveFileName(
        None, "Save Grid", str(initial_path), "PNG Files (*.png);;SVG Files (*.svg)"
    )
    if file_path:
        file_path_input.setText(file_path)


def save_grid(
    self,
    dialog,
    file_path,
    transparent_checkbox,
    paths_checkbox,
    beginning_points_checkbox,
    heat_map_checkbox,
    seizure_beginnings_checkbox,
    discharge_start_areas_checkbox,
    save_all_individually_checkbox,
):
    params = [
        transparent_checkbox.isChecked(),
        paths_checkbox.isChecked() and paths_checkbox.isEnabled(),
        beginning_points_checkbox.isChecked() and beginning_points_checkbox.isEnabled(),
        heat_map_checkbox.isChecked() and heat_map_checkbox.isEnabled(),
        seizure_beginnings_checkbox.isChecked()
        and seizure_beginnings_checkbox.isEnabled(),
        discharge_start_areas_checkbox.isChecked()
        and discharge_start_areas_checkbox.isEnabled(),
    ]

    post_fix = "" if not params[0] else "_transparent"
    # Add post_fix right before the file extension
    if file_path.endswith(".png"):
        file_path = file_path.replace(".png", f"{post_fix}.png")
    elif file_path.endswith(".svg"):
        file_path = file_path.replace(".svg", f"{post_fix}.svg")

    if save_all_individually_checkbox.isChecked():
        params = [transparent_checkbox.isChecked(), False, False, False, False, False]
        save_grid_image(self, file_path, params)
        for i in range(4):
            # Set the parameters for each iteration
            params = [
                transparent_checkbox.isChecked(),
                False,
                False,
                False,
                False,
                False,
            ]
            params[i + 1] = True
            if file_path.endswith(".png"):
                export_file_path = file_path.replace(
                    ".png",
                    f"_{['paths', 'beginning_points', 'heat_map', 'seizure_beginnings', 'discharge_start_areas'][i]}.png",
                )
            elif file_path.endswith(".svg"):
                export_file_path = file_path.replace(
                    ".svg",
                    f"_{['paths', 'beginning_points', 'heat_map', 'seizure_beginnings', 'discharge_start_areas'][i]}.svg",
                )
            save_grid_image(self, export_file_path, params)
    else:
        save_grid_image(self, file_path, params)

    dialog.accept()


def save_grid_image(self, file_path, params):
    if not file_path or file_path == "" or not file_path.endswith((".png", ".svg")):
        return

    # Check if the file path exists:
    if os.path.exists(file_path):
        overwrite = QMessageBox.question(
            self,
            "Overwrite File?",
            f"The file {file_path} already exists. Do you want to overwrite it?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if overwrite == QMessageBox.No:
            return

    if file_path.endswith(".png"):
        pixmap = QPixmap(self.grid_widget.size())
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
    else:
        svg_generator = QSvgGenerator()
        svg_generator.setFileName(file_path)
        svg_generator.setSize(self.grid_widget.size())
        svg_generator.setViewBox(self.grid_widget.rect())
        svg_generator.setTitle("Grid with Seizure Visualization")
        svg_generator.setDescription("Generated from MEA Grid View")

        painter = QPainter(svg_generator)
        painter.setRenderHint(QPainter.Antialiasing)

    transparent = params[0]
    for row in self.grid_widget.cells:
        for cell in row:
            if cell.color == BACKGROUND and transparent:
                continue
            # Calculate the cell's position
            cell_rect = cell.sceneBoundingRect()
            cell_pos = self.grid_widget.mapFromScene(cell_rect.topLeft())
            # Draw the cell with a slight overlap
            painter.setBrush(QBrush(cell.get_current_color()))
            painter.setPen(Qt.NoPen)
            painter.drawRect(
                int(cell_pos.x()) - 1,
                int(cell_pos.y()) - 1,
                int(cell_rect.width()) + 2,
                int(cell_rect.height()) + 2,
            )

    # Draw seizures using cluster_tracker's draw_seizures function
    if not hasattr(self, "cluster_tracker") and any(params):
        painter.end()
        QMessageBox.warning(
            self,
            "No Seizures Tracked",
            "No seizures have been tracked. Please track seizures before saving.",
        )
        return

    _, paths, beginning_points, heat_map, seizure_beginnings, discharge_start_areas = (
        params
    )
    cell_width = self.grid_widget.cells[0][0].rect().width()
    cell_height = self.grid_widget.cells[0][0].rect().height()
    temp_scene = QGraphicsScene()

    if heat_map:
        print("Drawing heat map")
        rows, cols = 64, 64
        self.cluster_tracker.draw_heatmap(
            temp_scene, cell_width, cell_height, rows, cols, painter, False
        )

    if paths:
        print("Drawing paths")
        self.cluster_tracker.draw_seizures(
            temp_scene, cell_width, cell_height, painter, False
        )
    if beginning_points:
        print("Drawing beginning points")
        self.cluster_tracker.draw_beginning_points(
            temp_scene, cell_width, cell_height, painter, False
        )

    if seizure_beginnings:
        if hasattr(self.grid_widget, "seizure_beginnings"):
            self.grid_widget.draw_purple_dots_on_image(painter)

    if discharge_start_areas:
        print("Drawing discharge start areas")
        self.discharge_start_dialog.draw_discharge_starts_on_image(painter)

    if file_path.endswith(".png"):
        pixmap.save(file_path, "PNG")
    painter.end()
