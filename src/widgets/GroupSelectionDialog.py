from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from helpers.Constants import MARKER, SIZE
from widgets.ScatterPlot import ScatterPlot


class Group:
    def __init__(self, channels, image, color, number):
        self.channels = channels
        self.image = image
        self.color = color
        self.number = number


class GroupSelectionDialog(QDialog):
    def __init__(self, parent=None, uploadedImage=None, active_channels=None):
        super().__init__(parent)
        self.setWindowTitle("Create Groups")
        self.setWindowState(Qt.WindowMaximized)

        layout = QHBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.scatter_plot = ScatterPlot(self, uploadedImage, active_channels)
        self.scatter_plot.enterPressed.connect(self.save_group)
        splitter.addWidget(self.scatter_plot)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)

        self.group_list = QListWidget()
        right_layout.addWidget(self.group_list)

        button_layout = QHBoxLayout()
        right_layout.addLayout(button_layout)

        self.save_button = QPushButton("Save Group")
        self.save_button.clicked.connect(self.save_group)
        button_layout.addWidget(self.save_button)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(self.confirm_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.groups = []

    def get_selected_points(self):
        selected_points = self.scatter_plot.selected_points
        if self.scatter_plot.image is not None:
            selected_channels = [
                (int(64 - point[1]), int(point[0]))
                for point in selected_points
                if (int(64 - point[1]), int(point[0]))
                in self.scatter_plot.active_channels
            ]
        else:
            selected_channels = [
                (int(64 - point[1]), int(point[0]))
                for point in selected_points
                if (int(64 - point[1]), int(point[0]))
                in self.scatter_plot.active_channels
            ]
        return selected_channels

    def save_group(self):
        selected_channels = self.get_selected_points()
        if not selected_channels:
            return
        num_channels = len(selected_channels)
        group_stats = (
            f"Group: {len(self.group_list) + 1}, Active Channels: {num_channels}"
        )

        self.scatter_plot.save_group()

        self.scatter_plot.canvas.draw()

        group_image = self.capture_group_image()

        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 200))
        self.group_list.addItem(item)
        card_widget = QWidget()
        card_layout = QHBoxLayout()
        card_widget.setLayout(card_layout)
        image_label = QLabel()
        image_label.setPixmap(
            group_image.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        card_layout.addWidget(image_label)
        stats_label = QLabel(group_stats)
        card_layout.addWidget(stats_label)
        self.group_list.setItemWidget(item, card_widget)

        self.groups.append(
            Group(
                selected_channels,
                group_image,
                self.scatter_plot.group_colors[-1],
                len(self.groups) + 1,
            )
        )

    def capture_group_image(self):
        temp_fig = Figure(figsize=(5, 5), dpi=100)
        temp_fig.set_tight_layout(True)
        temp_canvas = FigureCanvas(temp_fig)
        temp_ax = temp_fig.add_subplot(111)
        temp_ax.set_aspect(self.scatter_plot.ax.get_aspect())
        temp_ax.set_xlim(self.scatter_plot.ax.get_xlim())
        temp_ax.set_ylim(self.scatter_plot.ax.get_ylim())
        if self.scatter_plot.image is not None:
            temp_ax.imshow(
                self.scatter_plot.image[::-1],  # Vertically flip the image
                extent=[
                    0,
                    self.scatter_plot.image.shape[1],
                    0,
                    self.scatter_plot.image.shape[0],
                ],
            )
        group = self.scatter_plot.groups[-1]
        color = self.scatter_plot.group_colors[-1]
        temp_ax.scatter(
            [point[0] for point in group],
            [point[1] for point in group],
            c=color,
            s=SIZE,
            alpha=0.8,
            marker=MARKER,
        )
        temp_ax.set_xticks([])
        temp_ax.set_yticks([])
        temp_canvas.draw()
        pixmap = QPixmap(temp_canvas.size())
        temp_canvas.render(pixmap)
        image = QImage(pixmap)
        return QPixmap.fromImage(image)

    def get_groups(self):
        return self.groups
