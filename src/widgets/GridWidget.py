import typing
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt5.QtGui import QBrush, QColor, QPainterPath, QPen, QPixmap, QTransform
from PyQt5.QtWidgets import (
    QAction,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
    QGraphicsEllipseItem,
)
import random
from widgets.ColorCell import ColorCell
from helpers.Constants import BACKGROUND, ACTIVE


class Spark(QGraphicsEllipseItem):
    def __init__(self, x, y):
        super().__init__(0, 0, 3, 3)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(255, 165, 0)))  # Orange color for sparks
        self.setPen(QPen(Qt.NoPen))
        self.velocity = QPointF(
            random.uniform(-2, 2), random.uniform(-8, -4)
        )  # More upward velocity
        self.gravity = 0.8  # Gravity effect
        self.life = random.randint(5, 15)  # Increased life for longer trails

    def update_position(self):
        self.moveBy(self.velocity.x(), self.velocity.y())
        self.velocity.setY(self.velocity.y() + self.gravity)  # Apply gravity
        self.life -= 1
        if self.life <= 0:
            self.scene().removeItem(self)
            return False
        return True


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

        self.is_lasso_mode = False
        self.lasso_path = None
        self.lasso_item = None
        self.lasso_points = []
        self.highlighted_cells = set()
        self.lasso_history = []

        self.sparks = []
        self.spark_timer = QTimer(self)
        self.spark_timer.timeout.connect(self.update_sparks)
        self.spark_timer.start(16)  # 60 FPS

        self.setFocusPolicy(Qt.StrongFocus)

    def createGrid(self):
        self.cells = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(self.cols):
                cell = ColorCell(i, j, BACKGROUND)
                cell.mousePressEvent = self.cell_mouse_press_event
                self.scene.addItem(cell)
                self.cells[i][j] = cell

        self.resizeGrid()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        save_video_action = QAction("Save as video", self)
        save_image_action = QAction("Save as image", self)
        toggle_lasso_action = QAction("Toggle lasso mode", self)
        toggle_lasso_action.setCheckable(True)
        toggle_lasso_action.setChecked(self.is_lasso_mode)

        context_menu.addAction(save_video_action)
        context_menu.addAction(save_image_action)
        context_menu.addAction(toggle_lasso_action)

        save_video_action.triggered.connect(self.save_as_video_requested.emit)
        save_image_action.triggered.connect(self.save_as_image_requested.emit)
        toggle_lasso_action.triggered.connect(self.toggle_lasso_mode)

        context_menu.exec_(self.mapToGlobal(event.pos()))

    def toggle_lasso_mode(self):
        self.is_lasso_mode = not self.is_lasso_mode
        if not self.is_lasso_mode:
            self.clear_lasso()

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]) -> None:
        if event.key() == Qt.Key_Z:
            self.undo_lasso_selection()
        elif event.key() == Qt.Key_C:
            self.clear_lasso_selection()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.is_lasso_mode and event.button() == Qt.LeftButton:
            self.start_lasso(event.pos())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_lasso_mode and event.buttons() & Qt.LeftButton:
            self.continue_lasso(event.pos())
            if random.random() < 0.1:
                self.create_sparks(event.pos())
        else:
            super().mouseMoveEvent(event)

    def undo_lasso_selection(self):
        if self.lasso_history:
            # Restore the previous state
            previous_state = self.lasso_history.pop()
            for cell in previous_state:
                print(f"({cell.row}, {cell.col})")
                cell.lasso_selected = False
                cell.setColor(ACTIVE)
            self.update()
            print("Undid last lasso selection")
        else:
            print("No lasso selection to undo")

    def clear_lasso_selection(self):
        # Clear all lasso selections
        for row in self.cells:
            for cell in row:
                if cell.lasso_selected:
                    cell.lasso_selected = False
                    cell.setColor(ACTIVE)
        self.lasso_history.clear()
        self.update()
        print("Cleared all lasso selections")

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

    def continue_lasso(self, pos):
        scene_pos = self.mapToScene(pos)
        self.lasso_points.append(scene_pos)

        # Clear the existing path
        self.lasso_path = QPainterPath()
        self.lasso_path.moveTo(self.lasso_points[0])

        # Draw lines to all points, including the current one
        for point in self.lasso_points[1:]:
            self.lasso_path.lineTo(point)

        # Connect back to the start
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
                    cell.setColor(ACTIVE)

    def end_lasso(self):
        if len(self.lasso_points) > 2:
            self.select_cells_in_lasso()
        self.clear_lasso()
        # Clear highlights after selection
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
        # Store the current state before making a new selection
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
        # Clear any remaining highlights
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
        if self.image_path:
            self.setBackgroundImage(self.image_path)

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
