# TODO: I'm pretty sure this code is useless at this point. I'm keeping it here for reference. This is where I was trying to reconstruct the raw signal from the wavelet coefficients to fix an issue with BW5.
import numpy as np
import math
import h5py
import pywt
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from datetime import timedelta
import sys


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(timedelta(seconds=value))[:-3] for value in values]


class MainWindow(QMainWindow):
    def __init__(self, file_path, chIdx):
        super().__init__()
        self.file_path = file_path
        self.chIdx = chIdx
        self.frame_indices = range(604, 608)  # Default frame range
        self.current_frame_index = 0
        self.sub_frame_index = 0
        self.chunk_data = []
        self.setup_file()
        self.setup_ui()
        self.process_frames()

    def setup_file(self):
        with h5py.File(self.file_path, "r") as file:
            self.samplingRate = file.attrs["SamplingRate"]
            self.nChannels = len(file["Well_A1/StoredChIdxs"])
            self.compressionLevel = file["Well_A1/WaveletBasedEncodedRaw"].attrs[
                "CompressionLevel"
            ]
            self.framesChunkLength = file["Well_A1/WaveletBasedEncodedRaw"].attrs[
                "DataChunkLength"
            ]
            self.coefsChunkLength = (
                math.ceil(self.framesChunkLength / pow(2, self.compressionLevel)) * 2
            )
            self.toc = file["TOC"][:]
            self.wavelet_toc = file["Well_A1/WaveletBasedEncodedRawTOC"][:]

    def setup_ui(self):
        self.graphWidget = pg.PlotWidget()
        time_axis = TimeAxisItem(orientation="bottom")
        self.graphWidget.setAxisItems({"bottom": time_axis})
        view_box = self.graphWidget.getPlotItem().getViewBox()
        self.curve = self.graphWidget.plot(pen=pg.mkPen("w", width=3))
        self.graphWidget.setTitle(
            f"Frames {self.frame_indices[0]}-{self.frame_indices[-1]} - Accumulating Data"
        )
        self.graphWidget.setLabel("left", "ADC Count")
        self.graphWidget.setLabel("bottom", "Time (hh:mm:ss.ms)")

        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.previous_sub_frame()
        elif event.key() == Qt.Key_Right:
            self.next_sub_frame()

    def update_plot(self):
        if self.chunk_data:
            accumulated_data = []
            for i in range(self.current_frame_index):
                accumulated_data.extend(self.chunk_data[i].flatten())

            current_frame_data = self.chunk_data[self.current_frame_index]
            for i in range(self.sub_frame_index + 1):
                accumulated_data.extend(current_frame_data[i])

            x = np.arange(0, len(accumulated_data), 1) / self.samplingRate
            self.curve.setData(x, accumulated_data)

        current_frame = self.frame_indices[self.current_frame_index]
        self.setWindowTitle(f"Frame {current_frame}, Sub-frame {self.sub_frame_index}")

    def process_frames(self):
        try:
            with h5py.File(self.file_path, "r") as file:
                for frame_index in self.frame_indices:
                    frame_start, frame_end = self.toc[frame_index][:2]
                    coefs_start = self.wavelet_toc[frame_index]
                    coefs_end = (
                        self.wavelet_toc[frame_index + 1]
                        if frame_index + 1 < len(self.wavelet_toc)
                        else None
                    )
                    chunk_coefs = file["Well_A1/WaveletBasedEncodedRaw"][
                        coefs_start:coefs_end
                    ]
                    self.chunk_data.append(
                        np.array(self.reconstruct_chunk(chunk_coefs))
                    )
            self.update_plot()
        except Exception as e:
            print(f"Error processing frames: {e}")

    def reconstruct_chunk(self, chunk_coefs):
        try:
            reconstructed_data = []
            for i in range(4):  # Exactly 4 sub-frames
                start = (
                    i * self.coefsChunkLength * self.nChannels
                    + self.chIdx * self.coefsChunkLength
                )
                end = start + self.coefsChunkLength
                coefs = chunk_coefs[start:end]

                length = int(len(coefs) / 2)
                approx, details = coefs[:length], coefs[length:]
                wavelet = "sym7"
                mode = "periodization"
                approx = np.roll(approx, -5)
                details = np.roll(details, -5)
                frames = pywt.idwt(approx, details, wavelet, mode)
                length *= 2
                for j in range(1, self.compressionLevel):
                    frames = pywt.idwt(frames[:length], None, wavelet, mode)
                    length *= 2
                reconstructed_data.append(frames[1:-2])

            print(f"Reconstructed 4 sub-frames for frame")
            return reconstructed_data
        except Exception as e:
            print(f"Error reconstructing chunk: {e}")
            return []

    def previous_sub_frame(self):
        if self.sub_frame_index > 0:
            self.sub_frame_index -= 1
        elif self.current_frame_index > 0:
            self.current_frame_index -= 1
            self.sub_frame_index = 3  # Set to last sub-frame of previous frame
        self.update_plot()

    def next_sub_frame(self):
        if self.sub_frame_index < 3:
            self.sub_frame_index += 1
        elif self.current_frame_index < len(self.frame_indices) - 1:
            self.current_frame_index += 1
            self.sub_frame_index = 0
        self.update_plot()


def get_channel_index(row, col):
    if not (1 <= row <= 64 and 1 <= col <= 64):
        raise ValueError("Row and column must be between 1 and 64")
    return ((row - 1) * 64 + col) - 1


def main():
    file_path = "/Users/booka66/Desktop/6-14-24-slice2a_00.brw"
    chIdx = get_channel_index(45, 42)
    print(f"Channel index: {chIdx}")

    app = QApplication(sys.argv)
    main_window = MainWindow(file_path, chIdx)
    main_window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
