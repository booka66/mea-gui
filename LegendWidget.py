from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QBrush, QLinearGradient, QPainter
from PyQt5.QtWidgets import QWidget

from Constants import ACTIVE, BACKGROUND, SE, SEIZURE


class LegendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient1 = QLinearGradient(0, 0, 0, self.height() // 2)
        gradient1.setColorAt(0.0, Qt.white)
        gradient1.setColorAt(1.0, SEIZURE)

        gradient2 = QLinearGradient(0, 0, 0, self.height() // 2)
        gradient2.setColorAt(0.0, Qt.white)
        gradient2.setColorAt(1.0, SE)

        seizure_bar = QRect(10, 40, 20, self.height() // 2)
        se_bar = QRect(50, 40, 20, self.height() // 2)

        painter.setBrush(QBrush(gradient1))
        painter.setPen(Qt.NoPen)
        painter.drawRect(seizure_bar)

        painter.setBrush(QBrush(gradient2))
        painter.drawRect(se_bar)

        painter.setPen(Qt.white)
        painter.save()
        painter.translate(seizure_bar.right() + 15, seizure_bar.center().y())
        painter.rotate(-90)
        painter.drawText(0, 0, "Seizure")
        painter.restore()

        painter.save()
        painter.translate(se_bar.right() + 15, se_bar.center().y())
        painter.rotate(-90)
        painter.drawText(0, 0, "Status Epilepticus")
        painter.restore()

        labels = ["Minimum", "Maximum"]
        painter.setPen(Qt.white)
        painter.drawText(seizure_bar.left(), seizure_bar.top() - 5, labels[0])
        painter.drawText(seizure_bar.left(), seizure_bar.bottom() + 15, labels[1])

        # Show active channel and inactive channel colors
        painter.setPen(Qt.white)
        painter.drawText(0, seizure_bar.bottom() + 65, "Active")
        painter.drawText(55, se_bar.bottom() + 65, "Inactive")

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(ACTIVE))
        painter.drawRect(10, seizure_bar.bottom() + 30, 20, 20)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(BACKGROUND))
        painter.drawRect(50, se_bar.bottom() + 30, 20, 20)
