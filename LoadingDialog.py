import time
from PyQt5.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout
from pyqtgraph.Qt.QtCore import pyqtSignal
from pyqtgraph.Qt.QtWidgets import QPushButton


class LoadingDialog(QDialog):
    analysis_cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analysis in Progress")
        self.resize(800, 75)
        layout = QVBoxLayout()
        self.label = QLabel("Starting analysis...")
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar()
        self.active_channels = self.parent().active_channels
        layout.addWidget(self.progress_bar)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_analysis)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)
        self.start_time = 0

    def update_progress(self, message, value):
        self.label.setText(message)
        self.progress_bar.setValue(value)

    def showEvent(self, event):
        super().showEvent(event)
        self.start_time = time.time()

    def closeEvent(self, event):
        super().closeEvent(event)

    def cancel_analysis(self):
        self.analysis_cancelled.emit()
        self.close()
