import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt5.QtGui import QBrush, QColor, QPainterPath, QPen, QPixmap, QTransform
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QGraphicsPathItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QMenu,
    QGraphicsEllipseItem,
    QPushButton,
    QVBoxLayout,
)
import random
from widgets.ColorCell import ColorCell
from helpers.Constants import BACKGROUND, ACTIVE
import pyqtgraph as pg
import numpy as np


class Spark(QGraphicsEllipseItem):
    def __init__(self, x, y):
        super().__init__(0, 0, 3, 3)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(255, 165, 0)))
        self.setPen(QPen(Qt.NoPen))
        self.velocity = QPointF(random.uniform(-2, 2), random.uniform(-8, -4))
        self.gravity = 0.8
        self.life = random.randint(5, 15)

    def update_position(self):
        self.moveBy(self.velocity.x(), self.velocity.y())
        self.velocity.setY(self.velocity.y() + self.gravity)
        self.life -= 1
        if self.life <= 0:
            self.scene().removeItem(self)
            return False
        return True


class PurpleDot(QGraphicsEllipseItem):
    def __init__(self, x, y, size=40, color=QColor(128, 0, 128, 128)):
        super().__init__(0, 0, size, size)
        self.setPos(x - size / 2, y - size / 2)
        self.color = color
        self.setBrush(QBrush(self.color))
        self.setPen(QPen(Qt.NoPen))

    def change_color(self, new_color):
        self.color = new_color
        self.setBrush(QBrush(self.color))


class SimpleColorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose a Color")
        self.layout = QVBoxLayout(self)

        self.predefined_colors = [
            QColor(255, 0, 0, 128),
            QColor(0, 255, 0, 128),
            QColor(0, 0, 255, 128),
            QColor(255, 255, 0, 128),
            QColor(255, 0, 255, 128),
            QColor(0, 255, 255, 128),
        ]

        for color in self.predefined_colors:
            button = QPushButton()
            button.setStyleSheet(f"background-color: {color.name()}; min-height: 30px;")
            button.clicked.connect(lambda _, c=color: self.color_chosen(c))
            self.layout.addWidget(button)

        self.selected_color = None

    def color_chosen(self, color):
        self.selected_color = color
        self.accept()


class GridWidget(QGraphicsView):
    cell_clicked = pyqtSignal(int, int)
    save_as_video_requested = pyqtSignal()
    save_as_image_requested = pyqtSignal()

    def __init__(self, rows, cols, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.rows = rows
        self.cols = cols
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.cells = []
        self.is_recording_video = False
        self.selected_channel = None
        self.image_path = None
        self.createGrid()

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.setFixedSize(300, 200)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)

        self.plot_item.enableAutoRange(axis="y")

        self.curve1 = self.plot_item.plot(pen="b")
        self.curve2 = self.plot_item.plot(pen="r")

        self.plot_proxy = QGraphicsProxyWidget()
        self.plot_proxy.setWidget(self.plot_widget)

        self.plot_proxy.setZValue(1000)

        self.plot_data1 = np.zeros(100)
        self.plot_data2 = np.zeros(100)
        self.plot_x = np.arange(100)

        self.is_lasso_mode = False
        self.lasso_path = None
        self.lasso_item = None
        self.lasso_points = []
        self.highlighted_cells = set()
        self.lasso_history = []

        self.sparks = []
        self.spark_timer = QTimer(self)
        self.spark_timer.timeout.connect(self.update_sparks)
        self.spark_timer.start(16)

        self.is_seizure_beginning_mode = False
        self.seizure_beginnings = []

        self.setFocusPolicy(Qt.StrongFocus)

        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.message_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.message_label.hide()

        self.message_timer = QTimer(self)
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.hide_message)

    def show_temporary_message(self, message, duration=3000):
        self.message_label.setText(message)
        self.message_label.adjustSize()
        self.update_message_position()
        self.message_label.show()
        self.message_timer.start(duration)

    def hide_message(self):
        self.message_label.hide()

    def update_message_position(self):
        margin = 10
        self.message_label.move(
            self.width() - self.message_label.width() - margin, margin
        )

    def createGrid(self):
        self.cells = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(self.cols):
                cell = ColorCell(i, j, BACKGROUND)
                cell.mousePressEvent = self.cell_mouse_press_event
                self.scene.addItem(cell)
                self.cells[i][j] = cell

        self.resizeGrid()

    def show_color_dialog(self, dot):
        dialog = SimpleColorDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_color:
            dot.change_color(dialog.selected_color)

    def contextMenuEvent(self, event):
        item = self.scene.itemAt(self.mapToScene(event.pos()), QTransform())
        if isinstance(item, PurpleDot):
            self.show_color_dialog(item)
        else:
            context_menu = QMenu(self)
            save_video_action = QAction("Save as Video", self)
            save_image_action = QAction("Save as Image", self)
            toggle_lasso_action = QAction("Create Propagation Groups", self)
            seizure_beginning_action = QAction("Place Seizure Beginning", self)
            clear_discharge_start_areas = QAction("Clear Discharge Start Areas", self)

            context_menu.addAction(save_video_action)
            context_menu.addAction(save_image_action)
            context_menu.addAction(toggle_lasso_action)
            context_menu.addAction(seizure_beginning_action)
            context_menu.addAction(clear_discharge_start_areas)

            save_video_action.triggered.connect(self.save_as_video_requested.emit)
            save_image_action.triggered.connect(self.save_as_image_requested.emit)
            toggle_lasso_action.triggered.connect(self.start_lasso_mode)
            seizure_beginning_action.triggered.connect(self.start_purple_dot_mode)
            clear_discharge_start_areas.triggered.connect(
                self.main_window.discharge_start_dialog.clear_discharge_start_areas_from_hdf5
            )

            context_menu.exec_(self.mapToGlobal(event.pos()))

    def update_cursor(self):
        if not self.is_lasso_mode:
            for row, col in self.main_window.active_channels:
                self.cells[row - 1][col - 1].setCursor(Qt.PointingHandCursor)

    def start_lasso_mode(self):
        self.is_lasso_mode = True
        self.clear_lasso_selection()

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]) -> None:
        if event.key() == Qt.Key_E:
            self.start_purple_dot_mode()
        elif event.key() == Qt.Key_Return:
            if self.is_seizure_beginning_mode:
                self.end_purple_dot_mode()
            elif self.is_lasso_mode:
                self.is_lasso_mode = False
                self.clear_lasso()
                self.update_cursor()
                self.show_temporary_message("Propagation groups created.")
        elif event.key() == Qt.Key_Z:
            self.undo_lasso_selection()
        elif event.key() == Qt.Key_C:
            self.clear_lasso_selection()
        elif event.key() == Qt.Key_Escape:
            if self.is_lasso_mode:
                self.is_lasso_mode = False
                self.clear_lasso()
                self.clear_lasso_selection()
                self.update_cursor()
                self.show_temporary_message("Lasso selection cancelled.")
            elif self.is_seizure_beginning_mode:
                self.cancel_purple_dot_mode()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.is_seizure_beginning_mode and event.button() == Qt.LeftButton:
            self.place_purple_dot(event.pos())
        elif not self.is_seizure_beginning_mode and event.button() == Qt.LeftButton:
            item = self.scene.itemAt(self.mapToScene(event.pos()), QTransform())
            if isinstance(item, PurpleDot):
                self.remove_purple_dot(item)
            elif self.is_lasso_mode:
                self.start_lasso(event.pos())
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_lasso_mode and event.buttons() & Qt.LeftButton:
            self.continue_lasso(event.pos())

        else:
            super().mouseMoveEvent(event)

    def start_purple_dot_mode(self):
        self.is_seizure_beginning_mode = True
        self.show_temporary_message(
            "Seizure beginning placement mode activated.\nPress 'Enter' to confirm or 'Esc' to cancel."
        )

    def end_purple_dot_mode(self):
        self.is_seizure_beginning_mode = False
        self.show_temporary_message("Seizure beginning placement mode ended.")

    def cancel_purple_dot_mode(self):
        for dot in self.seizure_beginnings:
            self.scene.removeItem(dot)
        self.seizure_beginnings.clear()
        self.end_purple_dot_mode()
        self.show_temporary_message("Seizure beginning placement cancelled.")

    def place_purple_dot(self, pos):
        scene_pos = self.mapToScene(pos)
        dot = PurpleDot(scene_pos.x(), scene_pos.y())
        self.seizure_beginnings.append(dot)
        self.draw_purple_dots(self.scene)

    def reset_scene(self, scene):
        if scene is None:
            return

        valid_items = []

        for item in self.seizure_beginnings:
            try:
                if item.scene() == scene:
                    scene.removeItem(item)
                else:
                    valid_items.append(item)
            except RuntimeError:
                pass

        self.seizure_beginnings = valid_items

    def draw_purple_dots(self, scene, painter=None, reset_scene=False):
        if reset_scene:
            self.reset_scene(scene)

        for dot in self.seizure_beginnings:
            if dot not in scene.items():
                scene.addItem(dot)

    def draw_purple_dots_on_image(self, painter):
        for dot in self.seizure_beginnings:
            dot_pos = dot.scenePos()
            painter.setBrush(dot.color)
            painter.drawEllipse(
                dot_pos, dot.rect().width() / 2, dot.rect().height() / 2
            )

    def remove_purple_dot(self, dot):
        self.scene.removeItem(dot)
        self.seizure_beginnings.remove(dot)
        self.show_temporary_message("Seizure beginning removed.")

    def undo_lasso_selection(self):
        if self.lasso_history:
            previous_state = self.lasso_history.pop()
            for cell in previous_state:
                print(f"({cell.row}, {cell.col})")
                cell.lasso_selected = False
                cell.setColor(ACTIVE)
            self.update()
            self.show_temporary_message("Undid last lasso selection")
        else:
            self.show_temporary_message("No lasso selection to undo")

    def clear_lasso_selection(self):
        for row in self.cells:
            for cell in row:
                if cell.lasso_selected:
                    cell.lasso_selected = False
                    cell.setColor(ACTIVE)
        self.lasso_history.clear()
        self.update()
        self.show_temporary_message("Cleared all lasso selections")

    def create_sparks(self, pos):
        scene_pos = self.mapToScene(pos)
        for _ in range(1):
            spark = Spark(scene_pos.x(), scene_pos.y())
            self.scene.addItem(spark)
            self.sparks.append(spark)

    def update_sparks(self):
        self.sparks = [spark for spark in self.sparks if spark.update_position()]

    def mouseReleaseEvent(self, event):
        if self.is_lasso_mode and event.button() == Qt.LeftButton:
            self.end_lasso()
        else:
            super().mouseReleaseEvent(event)

    def start_lasso(self, pos):
        self.lasso_points = [self.mapToScene(pos)]
        self.lasso_path = QPainterPath()
        self.lasso_path.moveTo(self.lasso_points[0])
        self.lasso_item = QGraphicsPathItem(self.lasso_path)
        self.lasso_item.setPen(QPen(QColor(255, 0, 0), 2))
        self.scene.addItem(self.lasso_item)

        for row in self.cells:
            for cell in row:
                if not cell.lasso_selected:
                    cell.prev_color = cell.get_current_color()

    def continue_lasso(self, pos):
        scene_pos = self.mapToScene(pos)
        self.lasso_points.append(scene_pos)

        self.lasso_path = QPainterPath()
        self.lasso_path.moveTo(self.lasso_points[0])

        for point in self.lasso_points[1:]:
            self.lasso_path.lineTo(point)

        self.lasso_path.lineTo(self.lasso_points[0])

        self.lasso_item.setPath(self.lasso_path)
        self.update_highlighted_cells()

    def update_highlighted_cells(self):
        for cell in self.highlighted_cells:
            cell.lasso_highlighted = False
        self.highlighted_cells.clear()

        for row, col in self.main_window.active_channels:
            cell = self.cells[row - 1][col - 1]
            if (
                self.lasso_path.contains(cell.sceneBoundingRect().center())
                and not cell.lasso_selected
            ):
                cell.lasso_highlighted = True
                self.highlighted_cells.add(cell)
                cell.setColor(QColor(0, 255, 0))
            else:
                if not cell.lasso_selected:
                    cell.lasso_highlighted = False
                    cell.setColor(cell.prev_color)

    def end_lasso(self):
        if len(self.lasso_points) > 2:
            self.select_cells_in_lasso()
        self.clear_lasso()

        for cell in self.highlighted_cells:
            cell.lasso_highlighted = False
        self.highlighted_cells.clear()

    def get_lasso_selected_cells(self):
        selected_cells = []
        for row in self.cells:
            for cell in row:
                if cell.lasso_selected:
                    selected_cells.append(cell)
        return selected_cells

    def select_cells_in_lasso(self):
        current_state = set(cell for cell in self.highlighted_cells)
        self.lasso_history.append(current_state)

        for cell in self.highlighted_cells:
            cell.lasso_selected = True
            cell.setColor(QColor(255, 0, 0))

        print("Selected cells:")
        for cell in self.highlighted_cells:
            print(f"({cell.row}, {cell.col})")

    def clear_lasso(self):
        if self.lasso_item:
            self.scene.removeItem(self.lasso_item)
            self.lasso_item = None
        self.lasso_path = None
        self.lasso_points = []

        for cell in self.highlighted_cells:
            cell.highlighted = False
        self.highlighted_cells.clear()

    def resizeGrid(self):
        rect = self.viewport().rect()

        cell_width = rect.width() / self.cols
        cell_height = rect.height() / self.rows

        cell_size = min(cell_width, cell_height)

        total_width = self.cols * cell_size
        total_height = self.rows * cell_size

        center_x = rect.width() / 2
        center_y = rect.height() / 2

        top_left_x = center_x - total_width / 2
        top_left_y = center_y - total_height / 2

        self.setSceneRect(top_left_x, top_left_y, total_width, total_height)

        for i in range(self.rows):
            for j in range(self.cols):
                self.cells[i][j].setRect(0, 0, cell_size, cell_size)
                self.cells[i][j].setPos(
                    top_left_x + j * cell_size, top_left_y + i * cell_size
                )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resizeGrid()
        self.update_message_position()
        if self.image_path:
            self.setBackgroundImage(self.image_path)
        self.update_plot_position()

    def update_plot_position(self):
        self.plot_proxy.setPos(10, 10)

    def update_plot(self, value):
        self.plot_data1[:-1] = self.plot_data1[1:]
        self.plot_data2[:-1] = self.plot_data2[1:]

        self.plot_data1[-1] = self.main_window.metric_50
        self.plot_data2[-1] = self.main_window.metric_cluster

        self.curve1.setData(self.plot_x, self.plot_data1)
        self.curve2.setData(self.plot_x, self.plot_data2)

    def setBackgroundImage(self, image_path):
        self.image_path = image_path
        pixmap = QPixmap(image_path)

        scale_x = self.sceneRect().width() / pixmap.width()
        scale_y = self.sceneRect().height() / pixmap.height()

        transform = QTransform().scale(scale_x, scale_y)

        brush = QBrush(pixmap)
        brush.setTransform(transform)

        self.setBackgroundBrush(brush)

    def set_is_recording_video(self, value):
        self.is_recording_video = value
        for row in self.cells:
            for cell in row:
                cell.is_recording_video = value

    def hide_all_selected_tooltips(self):
        for row in self.cells:
            for cell in row:
                cell.selected_tooltip.hide()

    def cell_mouse_press_event(self, event):
        if not self.is_recording_video and not self.is_lasso_mode:
            if event.button() == Qt.LeftButton:
                cell = self.scene.itemAt(event.scenePos(), QTransform())
                if isinstance(cell, ColorCell):
                    cell.clicked_state = not cell.clicked_state
                    self.cell_clicked.emit(cell.row, cell.col)
                    cell.update()
                    if cell.clicked_state:
                        self.hide_all_selected_tooltips()
                        cell.show_selected_tooltip()
                    else:
                        cell.selected_tooltip.hide()
                        cell.hover_tooltip.hide()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        for row in self.cells:
            for cell in row:
                cell.update()
