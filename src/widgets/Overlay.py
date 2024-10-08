from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QPainter, QPainterPath
from PyQt5.QtWidgets import QGraphicsItem


class Overlay(QGraphicsItem):
    def __init__(self, cells, color, opacity=0.5):
        super().__init__()
        self.cells = cells
        self.color = color
        self.color.setAlphaF(opacity)
        self.updateBoundingRect()
        self.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def updateBoundingRect(self):
        if not self.cells:
            self.bounding_rect = QRectF()
            return
        rects = [cell.sceneBoundingRect() for cell in self.cells]
        top = min(rect.top() for rect in rects)
        left = min(rect.left() for rect in rects)
        bottom = max(rect.bottom() for rect in rects)
        right = max(rect.right() for rect in rects)
        self.bounding_rect = QRectF(left, top, right - left, bottom - top)

    def boundingRect(self):
        return self.bounding_rect

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        for cell in self.cells:
            cell.overlay_color = self.color
            cell_rect = cell.sceneBoundingRect()
            path.addRect(cell_rect)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def shape(self):
        return QPainterPath()
