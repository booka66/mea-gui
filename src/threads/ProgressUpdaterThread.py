from time import perf_counter
from PyQt5.QtCore import QThread, pyqtSignal
import os


class ProgressUpdaterThread(QThread):
    progress_updated = pyqtSignal(str, int)

    def __init__(self, temp_data_path):
        super().__init__()
        self.temp_data_path = temp_data_path
        self.start_time = perf_counter()

    def run(self):
        num_files = 0
        while not self.isInterruptionRequested():
            if not os.path.exists(self.temp_data_path):
                temp_files = []
            else:
                temp_files = [f for f in os.listdir(self.temp_data_path)]
            num_files = len(temp_files)
            elapsed_time = perf_counter() - self.start_time
            hours = int(elapsed_time // 3600)
            elapsed_time -= hours * 3600
            minutes = int(elapsed_time // 60)
            elapsed_time -= minutes * 60
            seconds = elapsed_time
            self.progress_updated.emit(
                f"Elapsed time: {hours}h {minutes}m {seconds:.2f}s",
                num_files,
            )
            self.msleep(100)  # Update progress every second

        # Emit final progress update
        self.progress_updated.emit("Analysis completed.", num_files)
