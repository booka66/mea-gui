from PyQt5.QtWidgets import (
    QLabel,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPen
from PyQt5.QtCore import Qt, QRectF, pyqtSignal


class EEGScrubber(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
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
            background = QLinearGradient(0, 0, self.width(), 0)
            background.setColorAt(0, QColor(60, 60, 60))
            background.setColorAt(1, QColor(40, 40, 40))
            painter.fillRect(self.rect(), background)

            progress_width = int(self.valueToPixel(self._value))
            progress_gradient = QLinearGradient(0, 0, progress_width, 0)
            progress_gradient.setColorAt(0, QColor(0, 120, 255))
            progress_gradient.setColorAt(1, QColor(0, 180, 255))
            painter.fillRect(
                QRectF(0, 0, progress_width, self.height()), progress_gradient
            )

            marker_pen = QPen(QColor(255, 100, 0))
            marker_pen.setWidth(2)
            painter.setPen(marker_pen)
            for marker in self.markers:
                x = int(self.valueToPixel(marker * self.sampling_rate))
                painter.drawLine(x, 0, x, self.height())

            handle_width = 1
            handle_x = progress_width - handle_width // 2
            handle_color = QColor(255, 255, 255)
            painter.setPen(QPen(handle_color, handle_width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(handle_x, 0, handle_x, self.height())

            circle_radius = 3
            painter.setBrush(handle_color)
            painter.drawEllipse(
                QRectF(
                    handle_x - circle_radius, 0, circle_radius * 2, circle_radius * 2
                )
            )

            painter.setPen(QColor(100, 100, 100))
            num_ticks = 30
            for i in range(num_ticks + 1):
                x = int(i * self.width() / num_ticks)
                painter.drawLine(x, self.height() - 5, x, self.height())

            if self.hover_position is not None and not self.mouse_pressed:
                painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
                painter.drawLine(
                    self.hover_position, 0, self.hover_position, self.height()
                )

        finally:
            painter.end()

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
        if self.mouse_pressed:
            self.setValue(self.pixelToValue(event.x()))
        else:
            self.hover_position = event.x()
            self.update()
            self.showTooltip(event.pos())

    def leaveEvent(self, event):
        self.hover_position = None
        self.mouse_pressed = False
        self.update()
        QToolTip.hideText()

    def showTooltip(self, pos):
        value = self.pixelToValue(pos.x())
        time_in_seconds = value / self.sampling_rate
        tooltip_text = EEGScrubberWidget.formatTime(time_in_seconds)
        QToolTip.showText(self.mapToGlobal(pos), tooltip_text, self)


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
