import os
from time import perf_counter


import h5py
import numpy as np
from scipy.io import loadmat
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from alert import alert
from ProgressUpdaterThread import ProgressUpdaterThread


class ChannelProcessThread(QThread):
    finished = pyqtSignal(int, int, dict)

    def __init__(
        self,
        file_path,
        channel_index,
        num_channels,
        adc_counts_to_mv,
        mv_offset,
        sampling_rate,
        row,
        col,
        eng,
    ):
        super().__init__()
        self.file_path = file_path
        self.channel_index = channel_index
        self.num_channels = num_channels
        self.adc_counts_to_mv = adc_counts_to_mv
        self.mv_offset = mv_offset
        self.sampling_rate = sampling_rate
        self.row = row
        self.col = col
        self.eng = eng

    def run(self):
        with h5py.File(self.file_path, "r") as f:
            raw_data = f["/3BData/Raw"][self.channel_index :: self.num_channels]
        channel_data = raw_data.astype(np.float32)
        channel_data = (
            channel_data * self.adc_counts_to_mv + self.mv_offset
        ) / 1_000_000
        channel_data -= np.mean(channel_data)

        channel_data = channel_data.reshape(-1, 1)

        sampling_rate = float(self.sampling_rate)

        discharge_times, sz_times, discharge_trains_times, se_times = (
            self.eng.SzDetectCat(channel_data, sampling_rate, True, nargout=4)
        )
        result = {
            "signal": channel_data,
            "SzTimes": np.array(sz_times) if sz_times else np.array([]),
            "SETimes": np.array(se_times) if se_times else np.array([]),
            "DischargeTimes": np.array(discharge_times)
            if discharge_times
            else np.array([]),
            "DischargeTrainsTimes": np.array(discharge_trains_times)
            if discharge_trains_times
            else np.array([]),
        }
        print(f"Progress: {self.channel_index + 1}/{self.num_channels}")
        self.finished.emit(self.row, self.col, result)


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

    def get_cat_envelop(self, file_path, temp_data_path):
        with h5py.File(file_path, "r") as f:
            rec_electrode_list = f["/3BRecInfo/3BMeaStreams/Raw/Chs"]
            rows = rec_electrode_list["Row"][()]
            cols = rec_electrode_list["Col"][()]
            num_channels = int(len(rows))
            num_rec_frames = int(f["/3BRecInfo/3BRecVars/NRecFrames"][()])
            sampling_rate = int(f["/3BRecInfo/3BRecVars/SamplingRate"][()])
            signal_inversion = float(f["/3BRecInfo/3BRecVars/SignalInversion"][()][0])
            max_u_volt = float(f["/3BRecInfo/3BRecVars/MaxVolt"][()])
            min_u_volt = float(f["/3BRecInfo/3BRecVars/MinVolt"][()])
            bit_depth = int(f["/3BRecInfo/3BRecVars/BitDepth"][()][0])

        q_level = 2 ^ bit_depth
        from_q_level_to_u_volt = (max_u_volt - min_u_volt) / float(q_level)
        adc_counts_to_mv = signal_inversion * from_q_level_to_u_volt
        mv_offset = signal_inversion * min_u_volt

        os.makedirs(temp_data_path, exist_ok=True)

        threads = []

        for k in range(num_channels):
            thread = ChannelProcessThread(
                file_path,
                k,
                num_channels,
                adc_counts_to_mv,
                mv_offset,
                sampling_rate,
                int(rows[k]) - 1,
                int(cols[k]) - 1,
                self.eng,
            )
            thread.finished.connect(self.on_channel_processed)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.wait()

        return num_channels, sampling_rate, num_rec_frames

    def on_channel_processed(self, row, col, channel_data):
        self.data[row, col] = channel_data

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

            if not self.use_low_ram:
                print("Using MATLAB function")

                # Create temporary directory if it doesn't exist
                os.makedirs(self.temp_data_path, exist_ok=True)
                # Call MATLAB function
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

                        signal = np.array(data["signal"]).squeeze()
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
                        DischargeTrainsTimes = (
                            np.array(data["DischargeTrainsTimes"])
                            if "DischargeTrainsTimes" in data
                            else np.array([])
                        )

                        row, col = name
                        self.data[row - 1, col - 1] = {
                            "signal": signal,
                            "SzTimes": SzTimes,
                            "SETimes": SETimes,
                            "DischargeTimes": DischargeTimes,
                            "DischargeTrainsTimes": DischargeTrainsTimes,
                        }

            else:
                print("Using Python function")
                total_channels, self.sampling_rate, num_rec_frames = (
                    self.get_cat_envelop(self.file_path, self.temp_data_path)
                )

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
