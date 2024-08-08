from PyQt5.QtCore import QPoint, QPointF, QTimer, Qt
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem, QLabel

HOVER = QColor("#00ff00")
SELECTED = QColor("#008000")
PLOTTED = QColor("#ef233c")


class ColorCell(QGraphicsRectItem):
    def __init__(self, row, col, color, parent=None):
        super().__init__(parent)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setBrush(QBrush(color))
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(Qt.NoPen))
        self.clicked_state = False
        self.plotted_state = False
        self.plotted_shape = None
        self.hover_color = HOVER
        self.selected_color = SELECTED
        self.plotted_color = PLOTTED
        self.selected_width = 2
        self.plotted_width = 4
        self.row = row
        self.col = col
        self.is_recording_video = False
        self.selected_tooltip = QLabel()
        self.selected_tooltip.setWindowFlags(Qt.ToolTip)
        self.selected_tooltip.hide()
        self.hover_tooltip = QLabel()
        self.hover_tooltip.setWindowFlags(Qt.ToolTip)
        self.hover_tooltip.hide()
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.setInterval(250)
        self.tooltip_timer.timeout.connect(self.show_hover_tooltip)
        self.text = ""
        self.lasso_selected = False
        self.highlighted = False
        self.prev_color = None

    def get_current_color(self):
        return self.brush().color()

    def setText(self, text):
        self.text = text
        self.update()

    def setColor(self, color, strength=1.0, opacity=1.0):
        strength = max(0, min(strength, 1))

        hsv_color = color.toHsv()

        hsv_color.setHsv(
            hsv_color.hue(), int(hsv_color.saturation() * strength), hsv_color.value()
        )

        rgb_color = QColor.fromHsv(
            hsv_color.hue(), hsv_color.saturation(), hsv_color.value()
        )

        rgb_color.setAlphaF(opacity)

        self.setBrush(QBrush(rgb_color))

    def hoverEnterEvent(self, event):
        if not self.is_recording_video:
            if not self.clicked_state:
                self.tooltip_timer.start()

    def hoverLeaveEvent(self, event):
        if not self.is_recording_video:
            if not self.clicked_state:
                self.tooltip_timer.stop()
                self.hover_tooltip.hide()

    def show_hover_tooltip(self):
        if not self.clicked_state and self.isUnderMouse():
            self.hover_tooltip.setText(f"({self.row + 1}, {self.col + 1})")
            tooltip_pos = QCursor.pos()
            tooltip_pos += QPoint(20, -20)
            self.hover_tooltip.move(tooltip_pos)
            self.hover_tooltip.show()

    def show_selected_tooltip(self):
        self.selected_tooltip.setText(f"({self.row + 1}, {self.col + 1})")
        tooltip_pos = QCursor.pos()
        tooltip_pos += QPoint(20, -20)
        self.selected_tooltip.move(tooltip_pos)
        self.selected_tooltip.show()

    # ["", "󰔷", "x", ""]
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.text:
            painter.save()
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(Qt.black)
            rect = self.boundingRect()
            text_rect = painter.boundingRect(rect, Qt.AlignCenter, self.text)
            painter.drawText(text_rect, Qt.AlignCenter, self.text)
            painter.restore()

        if not self.is_recording_video:
            if self.clicked_state:
                painter.setPen(QPen(self.selected_color, self.selected_width))
                painter.drawRect(
                    self.rect().adjusted(
                        self.selected_width // 2,
                        self.selected_width // 2,
                        -self.selected_width // 2,
                        -self.selected_width // 2,
                    )
                )
            elif self.plotted_shape == "":
                painter.setPen(QPen(self.plotted_color, self.selected_width))
                painter.drawEllipse(
                    self.rect().adjusted(
                        self.plotted_width // 2,
                        self.plotted_width // 2,
                        -self.plotted_width // 2,
                        -self.plotted_width // 2,
                    )
                )
            elif self.plotted_shape == "󰔷":
                painter.setPen(QPen(self.plotted_color, self.selected_width))
                triangle_points = [
                    QPointF(
                        self.rect().center().x(),
                        self.rect().top() + self.plotted_width // 2,
                    ),
                    QPointF(
                        self.rect().left() + self.plotted_width // 2,
                        self.rect().bottom() - self.plotted_width // 2,
                    ),
                    QPointF(
                        self.rect().right() - self.plotted_width // 2,
                        self.rect().bottom() - self.plotted_width // 2,
                    ),
                ]
                painter.drawPolygon(QPolygonF(triangle_points))
            elif self.plotted_shape == "x":
                painter.setPen(QPen(self.plotted_color, self.selected_width))
                painter.drawLine(
                    self.rect().topLeft()
                    + QPointF(self.plotted_width // 2, self.plotted_width // 2),
                    self.rect().bottomRight()
                    - QPointF(self.plotted_width // 2, self.plotted_width // 2),
                )
                painter.drawLine(
                    self.rect().topRight()
                    - QPointF(self.plotted_width // 2, -self.plotted_width // 2),
                    self.rect().bottomLeft()
                    + QPointF(self.plotted_width // 2, -self.plotted_width // 2),
                )
            elif self.plotted_shape == "":
                painter.setPen(QPen(self.plotted_color, self.selected_width))
                painter.drawRect(
                    self.rect().adjusted(
                        self.plotted_width // 2,
                        self.plotted_width // 2,
                        -self.plotted_width // 2,
                        -self.plotted_width // 2,
                    )
                )
