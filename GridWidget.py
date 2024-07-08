from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QPixmap, QTransform
from PyQt5.QtWidgets import QAction, QGraphicsScene, QGraphicsView, QMenu
from ColorCell import ColorCell
from Constants import BACKGROUND


class GridWidget(QGraphicsView):
    cell_clicked = pyqtSignal(int, int)
    save_as_video_requested = pyqtSignal()
    save_as_image_requested = pyqtSignal()

    def __init__(self, rows, cols, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.cells = []
        self.is_recording_video = False
        self.selected_channel = None
        self.image_path = None
        self.createGrid()

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

        context_menu.addAction(save_video_action)
        context_menu.addAction(save_image_action)

        save_video_action.triggered.connect(self.save_as_video_requested.emit)
        save_image_action.triggered.connect(self.save_as_image_requested.emit)

        context_menu.exec_(self.mapToGlobal(event.pos()))

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
        if not self.is_recording_video:
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
