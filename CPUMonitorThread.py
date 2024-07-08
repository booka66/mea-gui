import psutil
from pyqtgraph.Qt.QtCore import QThread, pyqtSignal


class CPUMonitorThread(QThread):
    cpu_usage_updated = pyqtSignal(float)

    def run(self):
        while not self.isInterruptionRequested():
            cpu_usage = psutil.cpu_percent()
            self.cpu_usage_updated.emit(cpu_usage)
            self.msleep(500)
