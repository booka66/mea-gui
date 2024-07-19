from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient, QPen, QPolygon
from PyQt5.QtCore import QPoint, Qt, QRectF, pyqtSignal


class EEGScrubber(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)  # Increased height to accommodate tooltip
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._value = 0
        self._minimum = 0
        self._maximum = 100
        self.seizure_regions = []
        self.se_regions = []
        self.markers = []
        self.sampling_rate = 1
        self.hover_position = None
        self.setMouseTracking(True)
        self.mouse_pressed = False

    def setSamplingRate(self, rate):
        self.sampling_rate = rate

    def setRange(self, minimum, maximum):
        self._minimum = minimum
        self._maximum = maximum
        self.update()

    def minimum(self):
        return self._minimum

    def maximum(self):
        return self._maximum

    def value(self):
        return self._value

    def setValue(self, value):
        if self._minimum <= value <= self._maximum:
            self._value = value
            self.update()
            self.valueChanged.emit(value)

    def setMarkers(self, markers):
        self.markers = markers
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            # Draw background
            background_color = QColor(60, 60, 60)
            painter.fillRect(
                QRectF(0, 20, self.width(), self.height() - 20), background_color
            )

            # Draw progress
            progress_width = int(self.valueToPixel(self._value))
            progress_gradient = QLinearGradient(0, 20, progress_width, 20)
            progress_gradient.setColorAt(0, QColor(0, 120, 255))
            progress_gradient.setColorAt(1, QColor(0, 180, 255))
            painter.fillRect(
                QRectF(0, 20, progress_width, self.height() - 20), progress_gradient
            )

            # Draw markers
            marker_pen = QPen(QColor(255, 100, 0))
            marker_pen.setWidth(2)
            painter.setPen(marker_pen)
            for marker in self.markers:
                x = int(self.valueToPixel(marker * self.sampling_rate))
                painter.drawLine(x, 20, x, self.height())

            # Draw handle
            handle_width = 1
            handle_x = progress_width - handle_width // 2
            handle_color = QColor(255, 255, 255)
            painter.setPen(QPen(handle_color, handle_width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(handle_x, 20, handle_x, self.height())

            # Draw handle circle
            circle_radius = 3
            painter.setBrush(handle_color)
            painter.drawEllipse(
                QRectF(
                    handle_x - circle_radius, 20, circle_radius * 2, circle_radius * 2
                )
            )

            # Draw ticks
            painter.setPen(QColor(100, 100, 100))
            num_ticks = 30
            for i in range(num_ticks + 1):
                x = int(i * self.width() / num_ticks)
                painter.drawLine(x, self.height() - 5, x, self.height())

            # Draw hover line
            if self.hover_position is not None and not self.mouse_pressed:
                painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
                painter.drawLine(
                    self.hover_position, 20, self.hover_position, self.height()
                )

            # Draw custom tooltip
            if self.hover_position is not None:
                self.drawCustomTooltip(painter, self.hover_position)

        finally:
            painter.end()

    def drawCustomTooltip(self, painter, x_position):
        value = self.pixelToValue(x_position)
        time_in_seconds = value / self.sampling_rate
        tooltip_text = EEGScrubberWidget.formatTime(time_in_seconds)

        # Set up tooltip appearance
        tooltip_width = 100
        tooltip_height = 20
        triangle_height = 5
        tooltip_x = max(
            0, min(x_position - tooltip_width // 2, self.width() - tooltip_width)
        )

        # Calculate new y-position for the tooltip
        tooltip_y = -5

        # Draw tooltip rectangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 50, 50, 200))
        painter.drawRect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)

        # Draw tooltip triangle
        triangle = QPolygon(
            [
                QPoint(x_position, tooltip_y + tooltip_height + triangle_height),
                QPoint(x_position - 5, tooltip_y + tooltip_height),
                QPoint(x_position + 5, tooltip_y + tooltip_height),
            ]
        )
        painter.drawPolygon(triangle)

        # Draw tooltip text
        painter.setPen(Qt.white)
        painter.drawText(
            QRectF(tooltip_x, tooltip_y, tooltip_width, tooltip_height),
            Qt.AlignCenter,
            tooltip_text,
        )

    def valueToPixel(self, value):
        return (value - self._minimum) / (self._maximum - self._minimum) * self.width()

    def pixelToValue(self, pixel):
        return int(
            self._minimum + (pixel / self.width()) * (self._maximum - self._minimum)
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.setValue(self.pixelToValue(event.x()))
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = False
            self.hover_position = event.x()
            self.update()

    def mouseMoveEvent(self, event):
        self.hover_position = event.x()
        if self.mouse_pressed:
            self.setValue(self.pixelToValue(event.x()))
        self.update()

    def leaveEvent(self, event):
        self.hover_position = None
        self.mouse_pressed = False
        self.update()


class EEGScrubberWidget(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.scrubber = EEGScrubber()
        self.main_layout.addWidget(self.scrubber)

        self.control_layout = QHBoxLayout()

        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self.control_layout.addWidget(self.time_label)

        self.main_layout.addLayout(self.control_layout)

        self.scrubber.valueChanged.connect(self.updateTimeDisplay)
        self.scrubber.valueChanged.connect(self.valueChanged.emit)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def setRange(self, minimum, maximum):
        self.scrubber.setRange(minimum, maximum)
        self.updateTimeDisplay()

    def setValue(self, value):
        self.scrubber.setValue(value)
        self.updateTimeDisplay()

    def value(self):
        return self.scrubber.value()

    def minimum(self):
        return self.scrubber.minimum()

    def maximum(self):
        return self.scrubber.maximum()

    def setMarkers(self, markers):
        self.scrubber.setMarkers(markers)

    def setSamplingRate(self, rate):
        self.scrubber.setSamplingRate(rate)
        self.updateTimeDisplay()

    def updateTimeDisplay(self):
        current_time = self.value() / self.scrubber.sampling_rate
        total_time = self.maximum() / self.scrubber.sampling_rate
        self.time_label.setText(
            f"{self.formatTime(current_time)} / {self.formatTime(total_time)}"
        )

    @staticmethod
    def formatTime(seconds):
        total_milliseconds = int(seconds * 1000)
        milliseconds = total_milliseconds % 1000
        total_seconds = total_milliseconds // 1000
        hours, remaining_seconds = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remaining_seconds, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
