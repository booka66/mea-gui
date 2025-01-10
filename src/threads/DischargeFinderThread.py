from PyQt5.QtCore import QThread, pyqtSignal


class DischargeFinderThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, data, active_channels, signal_analyzer, start, stop):
        super().__init__()
        self.data = data
        self.active_channels = active_channels
        self.signal_analyzer = signal_analyzer
        self.start_range = start
        self.stop_range = stop

    def run(self):
        discharges = {}
        for row, col in self.active_channels:
            volt_signal = self.data[row - 1, col - 1]["signal"]
            peak_x, peak_y, discharge_start_x, discharge_start_y = (
                self.signal_analyzer.analyze_signal(
                    volt_signal, self.start_range, self.stop_range
                )
            )
            discharges[(row - 1, col - 1)] = (
                discharge_start_x,
                discharge_start_y,
            )
        self.finished.emit(discharges)
