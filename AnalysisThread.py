import os
from time import perf_counter


import h5py
import numpy as np
from scipy.io import loadmat
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from alert import alert
from ProgressUpdaterThread import ProgressUpdaterThread


class AnalysisThread(QThread):
    analysis_completed = pyqtSignal()
    progress_updated = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.file_path = None
        self.data = np.empty((64, 64), dtype=object)
        self.min_strength = None
        self.max_strength = None
        self.recording_length = None
        self.sampling_rate = None
        self.time_vector = None
        self.active_channels = []
        self.spike_data = []
        self.raster_downsample_factor = 1
        self.eng = None
        self.raster_plot = None
        self.progress_updater_thread = None
        self.temp_data_path = None
        self.do_analysis = False
        self.use_low_ram = False

    def stop_engine(self):
        if self.eng is not None:
            try:
                self.eng.quit()
                self.eng = None
            except Exception as e:
                print(f"Error while stopping MATLAB engine: {e}")

    def run(self):
        if self.eng is None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("MATLAB engine not started. Please wait a few seconds.")
            msg.setWindowTitle("Error")
            msg.exec_()
        try:
            start = perf_counter()
            self.progress_updater_thread = ProgressUpdaterThread(self.temp_data_path)
            self.progress_updater_thread.progress_updated.connect(self.progress_updated)
            self.progress_updater_thread.start()

            # Create temporary directory if it doesn't exist
            os.makedirs(self.temp_data_path, exist_ok=True)
            if self.use_low_ram:
                total_channels, self.sampling_rate, num_rec_frames = (
                    self.eng.low_ram_cat(
                        self.file_path, self.temp_data_path, self.do_analysis, nargout=3
                    )
                )
            else:
                total_channels, self.sampling_rate, num_rec_frames = (
                    self.eng.get_cat_envelop(
                        self.file_path, self.temp_data_path, self.do_analysis, nargout=3
                    )
                )
            self.data = np.empty((64, 64), dtype=object)

            # Load data from .mat files
            for file in os.listdir(self.temp_data_path):
                if file.endswith(".mat"):
                    data = loadmat(os.path.join(self.temp_data_path, file))

                    signal = np.array(data["signal"], dtype=np.float16).squeeze()

                    name = np.array(data["name"]).squeeze()
                    SzTimes = (
                        np.array(data["SzTimes"]) if "SzTimes" in data else np.array([])
                    )
                    SETimes = (
                        np.array(data["SETimes"]) if "SETimes" in data else np.array([])
                    )
                    DischargeTimes = (
                        np.array(data["DischargeTimes"])
                        if "DischargeTimes" in data
                        else np.array([])
                    )

                    row, col = name
                    self.data[row - 1, col - 1] = {
                        "signal": signal,
                        "SzTimes": SzTimes,
                        "SETimes": SETimes,
                        "DischargeTimes": DischargeTimes,
                    }

            total_channels = int(total_channels)
            self.sampling_rate = float(self.sampling_rate)
            num_rec_frames = int(num_rec_frames)
            self.recording_length = (1 / self.sampling_rate) * (num_rec_frames - 1)
            self.time_vector = [i / self.sampling_rate for i in range(num_rec_frames)]
            rows, cols = self.get_channels()
            self.active_channels = list(zip(rows, cols))
            self.analysis_completed.emit()
            end = perf_counter()
            analysis_time = end - start
            alert(f"Analysis completed in {analysis_time:.2f} seconds.")
        except Exception as e:
            print(f"Error: {e}")
            alert(f"Error during analysis:\n{str(e)}")
        finally:
            # Clean up .mat files
            for file in os.listdir(self.temp_data_path):
                if file.endswith(".mat"):
                    os.remove(os.path.join(self.temp_data_path, file))
            # Clean up temporary directory
            os.rmdir(self.temp_data_path)
            self.progress_updater_thread.requestInterruption()
            self.progress_updater_thread.wait()

    def get_channels(self):
        with h5py.File(self.file_path, "r") as f:
            recElectrodeList = f["/3BRecInfo/3BMeaStreams/Raw/Chs"]
            rows = recElectrodeList["Row"][()]
            cols = recElectrodeList["Col"][()]
        return rows, cols
