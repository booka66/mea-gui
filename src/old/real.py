# NOTE: I'm pretty sure this code is useless at this point. I'm keeping it here for reference. This is where I was trying to reconstruct the raw signal from the wavelet coefficients to fix an issue with BW5.
import numpy as np
import math
import h5py
import pywt
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QKeyEvent
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
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        time_axis = TimeAxisItem(orientation="bottom")
        self.graphWidget.setAxisItems({"bottom": time_axis})

        self.curve = self.graphWidget.plot(pen=pg.mkPen("w", width=3))
        self.curve.setDownsampling(auto=True, method="peak", ds=100)
        self.curve.setClipToView(True)
        self.graphWidget.setTitle("Reconstructed Raw Signal")
        self.graphWidget.setLabel("left", "ADC Count")
        self.graphWidget.setLabel("bottom", "Time (hh:mm:ss.ms)")

        self.file_path = file_path
        self.chIdx = chIdx
        self.data = []
        self.x = []
        self.chunk_index = 0

        self.setup_file()

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_next_chunk)
        self.timer.start(0)  # Process chunks as fast as possible

        self.is_paused = False

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

    def process_next_chunk(self):
        if self.is_paused:
            return

        if self.chunk_index < len(self.toc):
            with h5py.File(self.file_path, "r") as file:
                frame_start, frame_end = self.toc[self.chunk_index][:2]
                coefs_start = self.wavelet_toc[self.chunk_index]
                coefs_end = (
                    self.wavelet_toc[self.chunk_index + 1]
                    if self.chunk_index + 1 < len(self.wavelet_toc)
                    else None
                )

                chunk_coefs = file["Well_A1/WaveletBasedEncodedRaw"][
                    coefs_start:coefs_end
                ]
                self.reconstruct_and_update(chunk_coefs)

            self.chunk_index += 1
        else:
            self.timer.stop()

    def reconstruct_and_update(self, chunk_coefs):
        coefsPosition = self.chIdx * self.coefsChunkLength
        while coefsPosition < len(chunk_coefs):
            coefs = chunk_coefs[coefsPosition : coefsPosition + self.coefsChunkLength]
            length = int(len(coefs) / 2)
            approx, details = coefs[:length], coefs[length:]
            wavelet = "sym7"
            mode = "symmetric"
            frames = pywt.idwt(approx, details, wavelet, mode)
            length *= 2
            for i in range(1, self.compressionLevel):
                frames = pywt.idwt(frames[:length], None, wavelet, mode)
                length *= 2

            self.data.extend(frames)
            new_x = np.arange(len(self.data)) / self.samplingRate
            self.x = new_x

            self.update_plot()

            coefsPosition += self.coefsChunkLength * self.nChannels

    def update_plot(self):
        self.curve.setData(self.x, self.data)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.graphWidget.setTitle("Reconstructed Raw Signal (Paused)")
            else:
                self.graphWidget.setTitle("Reconstructed Raw Signal")


def get_channel_index(row, col):
    if not (1 <= row <= 64 and 1 <= col <= 64):
        raise ValueError("Row and column must be between 1 and 64")
    return (row - 1) * 64 + col


def choose_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select BRW file", filetypes=[("BRW files", "*.brw")]
    )
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit()
    return file_path


def main():
    file_path = "/Users/booka66/Desktop/6-14-24-slice2a_00.brw"
    chIdx = get_channel_index(45, 42) - 1
    print(f"Channel index: {chIdx}")

    app = QApplication(sys.argv)
    main_window = MainWindow(file_path, chIdx)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
