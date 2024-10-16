import os
from time import perf_counter
import sys


import h5py
import numpy as np
from scipy.io import loadmat
from PyQt5.QtCore import QThread, pyqtSignal

from helpers.alert import alert
from threads.ProgressUpdaterThread import ProgressUpdaterThread

cpp_import_failed = False
try:
    from helpers.extensions import sz_se_detect

    print("C++ extension loaded successfully")
except ImportError:
    cpp_import_failed = True
    print("C++ extension failed to load")


class CppAnalysisThread(QThread):
    analysis_completed = pyqtSignal(object)

    def __init__(self, file_path, do_analysis, temp_data_path):
        super().__init__()
        self.file_path = file_path
        self.do_analysis = do_analysis
        self.temp_data_path = temp_data_path

    def run(self):
        if sys.platform == "win32":
            results = sz_se_detect.processAllChannels(self.file_path, self.do_analysis)
        else:
            results = sz_se_detect.processAllChannels(
                self.file_path, self.do_analysis, self.temp_data_path
            )
        self.analysis_completed.emit(results)


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
        self.use_cpp = False

    def process_cpp_results(self, results):
        for result in results:
            signal = np.array(result.signal, dtype=np.float32).squeeze()
            SzTimes = np.array([(t[0], t[1], 1) for t in result.result.SzTimes])
            SETimes = np.array([(t[0], t[1], 1) for t in result.result.SETimes])
            DischargeTimes = np.array(result.result.DischargeTimes)

            self.data[result.Row - 1, result.Col - 1] = {
                "signal": signal,
                "SzTimes": SzTimes,
                "SETimes": SETimes,
                "DischargeTimes": DischargeTimes,
            }

    def stop_engine(self):
        if self.eng is not None:
            try:
                self.eng.quit()
                self.eng = None
            except Exception as e:
                print(f"Error while stopping MATLAB engine: {e}")

    def run(self):
        start = perf_counter()
        self.data = np.empty((64, 64), dtype=object)
        # Create temporary directory if it doesn't exist
        if self.temp_data_path is not None:
            os.makedirs(self.temp_data_path, exist_ok=True)
        try:
            self.progress_updater_thread = ProgressUpdaterThread(self.temp_data_path)
            self.progress_updater_thread.progress_updated.connect(self.progress_updated)
            self.progress_updater_thread.start()
            if self.eng is None or (self.use_cpp and not cpp_import_failed):
                print("Using c++ version")
                cpp_thread = CppAnalysisThread(
                    self.file_path, self.do_analysis, self.temp_data_path
                )
                cpp_thread.analysis_completed.connect(self.process_cpp_results)
                cpp_thread.start()
                cpp_thread.wait()
            else:
                print("Using matlab version")

                if self.use_low_ram:
                    _, self.sampling_rate, num_rec_frames = self.eng.low_ram_cat(
                        self.file_path,
                        self.temp_data_path,
                        self.do_analysis,
                        nargout=3,
                    )
                else:
                    _, self.sampling_rate, num_rec_frames = self.eng.get_cat_envelop(
                        self.file_path,
                        self.temp_data_path,
                        self.do_analysis,
                        nargout=3,
                    )

                # Load data from .mat files
                for file in os.listdir(self.temp_data_path):
                    if file.endswith(".mat"):
                        data = loadmat(os.path.join(self.temp_data_path, file))

                        signal = np.array(data["signal"], dtype=np.float32).squeeze()

                        name = np.array(data["name"]).squeeze()
                        SzTimes = (
                            np.array(data["SzTimes"])
                            if "SzTimes" in data
                            else np.array([])
                        )
                        SETimes = (
                            np.array(data["SETimes"])
                            if "SETimes" in data
                            else np.array([])
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

            with h5py.File(self.file_path, "r") as f:
                num_rec_frames = int(f["/3BRecInfo/3BRecVars/NRecFrames"][()])
                self.sampling_rate = float(f["/3BRecInfo/3BRecVars/SamplingRate"][()])

            self.recording_length = (1 / self.sampling_rate) * (num_rec_frames - 1)
            self.time_vector = [i / self.sampling_rate for i in range(num_rec_frames)]
            rows, cols = self.get_channels()
            self.active_channels = list(zip(rows, cols))
            for cell_data in self.data.flatten():
                if cell_data is None:
                    continue
                signal = cell_data["signal"]
                if signal is not None:
                    # Print stats about the signal
                    min_strength = signal.min()
                    max_strength = signal.max()
                    mean_strength = signal.mean()
                    std_strength = signal.std()
                    print(
                        f"min: {min_strength}, max: {max_strength}, mean: {mean_strength}, std: {std_strength}\n{signal[:20]}"
                    )
                    break
            self.analysis_completed.emit()
            end = perf_counter()
            analysis_time = end - start
            alert(f"Analysis completed in {analysis_time:.2f} seconds.")
        except Exception as e:
            print(f"Error: {e}")
            alert(f"Error during analysis:\n{str(e)}")
        finally:
            if self.progress_updater_thread is not None:
                self.progress_updater_thread.requestInterruption()
                self.progress_updater_thread.wait()
            # Clean up .mat or .txt files in temporary directory if they exist
            if os.path.exists(self.temp_data_path):
                for file in os.listdir(self.temp_data_path):
                    if file.endswith(".mat"):
                        os.remove(os.path.join(self.temp_data_path, file))
                # Clean up temporary directory
                os.rmdir(self.temp_data_path)

    def get_channels(self):
        with h5py.File(self.file_path, "r") as f:
            recElectrodeList = f["/3BRecInfo/3BMeaStreams/Raw/Chs"]
            rows = recElectrodeList["Row"][()]
            cols = recElectrodeList["Col"][()]
        return rows, cols
