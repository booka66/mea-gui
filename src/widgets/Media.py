from PyQt5.QtGui import QImage, QIntValidator, QPainter
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from PyQt5.QtCore import QRect, QSize, Qt
import os


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


def save_grid_as_png(self):
    if self.file_path:
        default_filename = os.path.splitext(self.file_path)[0] + "_grid.png"
    else:
        default_filename = "grid.png"

    file_path, _ = QFileDialog.getSaveFileName(
        self,
        "Save Grid as PNG",
        os.path.join(os.path.expanduser("~"), "Downloads", default_filename),
        "PNG Files (*.png)",
    )

    if file_path:
        pixmap = self.grid_widget.grab()
        pixmap.save(file_path, "PNG")
