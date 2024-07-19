import colorsys

import cv2
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector
from PIL import Image
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from helpers.Constants import MARKER, SIZE


class ScatterPlot(QWidget):
    enterPressed = pyqtSignal()

    def __init__(self, parent=None, image_path=None, active_channels=None):
        super().__init__()
        self.image_path = image_path
        self.image = None
        self.parent = parent
        self.selected_points = []
        self.undo_stack = []
        self.redo_stack = []
        self.active_channels = active_channels
        self.groups = []
        self.group_colors = []
        self.color_index = 0
        self.predefined_colors = [
            (211, 31, 17),
            (98, 200, 211),
            (244, 122, 0),
            (0, 113, 145),
            (106, 153, 78),
        ]
        self.initUI()
        self.setFocusPolicy(Qt.StrongFocus)

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        fig = Figure(figsize=(5, 5), dpi=100)
        fig.set_tight_layout(True)
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)

        self.ax = fig.add_subplot(111)
        self.ax.set_aspect("equal")

        self.x = [point[1] for point in self.active_channels]
        self.y = [64 - point[0] for point in self.active_channels]

        if self.image_path is not None:
            self.image = cv2.imread(self.image_path)
            if self.image is not None:
                height, width, _ = self.image.shape

                # Resize the image to match the size of the points
                image = Image.open(self.image_path)
                image = image.resize((64, 64), Image.LANCZOS)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                self.image = np.array(image)

                self.ax.imshow(self.image, extent=[0, 64, 64, 0])
                self.ax.set_xlim(0, 64)
                self.ax.set_ylim(0, 64)  # Invert the y-axis
            else:
                print(f"Failed to load image: {self.image_path}")
        else:
            self.ax.set_aspect("equal")
            self.ax.set_xlim(0, 64)
            self.ax.set_ylim(0, 64)

        self.ax.scatter(self.x, self.y, c="k", s=SIZE, alpha=0.3, marker=MARKER)

        self.lasso = LassoSelector(
            self.ax,
            self.lasso_callback,
            button=[1, 3],
            useblit=True,
        )

        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.canvas.draw()

    def lasso_callback(self, verts):
        path = Path(verts)
        new_selected_points = [
            (x, y) for x, y in zip(self.x, self.y) if path.contains_point((x, y))
        ]

        self.undo_stack.append(self.selected_points.copy())
        self.redo_stack.clear()
        self.selected_points.extend(new_selected_points)

        self.update_selected_points_plot()

        verts = np.append(verts, [verts[0]], axis=0)
        if hasattr(self, "lasso_line"):
            self.lasso_line.remove()
        self.lasso_line = self.ax.plot(
            verts[:, 0], verts[:, 1], "b-", linewidth=1, alpha=0.8
        )[0]

        self.canvas.draw()

    def update_selected_points_plot(self):
        if hasattr(self, "selected_points_plot"):
            self.selected_points_plot.remove()
        self.selected_points_plot = self.ax.scatter(
            [point[0] for point in self.selected_points],
            [point[1] for point in self.selected_points],
            c="red",
            s=SIZE,
            alpha=0.8,
            marker=MARKER,
        )

    def save_group(self):
        if self.selected_points:
            new_color = self.get_next_color()
            self.groups.append(self.selected_points.copy())
            self.group_colors.append(new_color)
            self.update_groups_plot()
            self.clear_selection()

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

    def update_groups_plot(self):
        for group, color in zip(self.groups, self.group_colors):
            self.ax.scatter(
                [point[0] for point in group],
                [point[1] for point in group],
                c=color,
                s=SIZE,
                alpha=0.8,
                marker=MARKER,
            )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.enterPressed.emit()
        elif event.key() == Qt.Key_C:
            self.clear_selection()
        elif event.key() == Qt.Key_Z:
            if event.modifiers() & Qt.ShiftModifier:
                self.redo_selection()
            else:
                self.undo_selection()

    def clear_selection(self):
        if self.lasso.active:
            self.lasso_line.set_visible(False)
            self.canvas.draw()
        self.undo_stack.append(self.selected_points.copy())
        self.redo_stack.clear()
        self.selected_points.clear()
        self.update_selected_points_plot()
        self.canvas.draw()

    def undo_selection(self):
        if self.undo_stack:
            if self.lasso.active:
                self.lasso_line.set_visible(False)
                self.canvas.draw()

            self.redo_stack.append(self.selected_points.copy())
            self.selected_points = self.undo_stack.pop()
            self.update_selected_points_plot()
            self.canvas.draw()

    def redo_selection(self):
        if self.redo_stack:
            if self.lasso.active:
                self.lasso_line.set_visible(False)
                self.canvas.draw()

            self.undo_stack.append(self.selected_points.copy())
            self.selected_points = self.redo_stack.pop()
            self.update_selected_points_plot()
            self.canvas.draw()

    def onrelease(self, event):
        if self.lasso.active:
            self.lasso_line.set_visible(False)
            self.canvas.draw()

    def showHotkeysHelp(self):
        hotkeys = [
            "There is no shift+click to do multiple selections. Just keep drawing and use the hotkeys to clear, undo, or redo.",
            "c: Clear",
            "z: Undo",
            "shift+z: Redo",
        ]
        QMessageBox.information(self, "Plot Hotkeys", "\n".join(hotkeys))
