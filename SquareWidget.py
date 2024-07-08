from PyQt5.QtWidgets import QWidget
from pyqtgraph.Qt.QtCore import QSize


class SquareWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.maintain_square_aspect_ratio()

    def maintain_square_aspect_ratio(self):
        current_size = self.size()
        min_dimension = min(current_size.width(), current_size.height())
        square_size = QSize(min_dimension, min_dimension)
        self.resize(square_size)
