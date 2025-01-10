# TODO: I'm pretty sure this code is useless at this point. I'm keeping it here for reference. This is where I was trying to reconstruct the raw signal from the wavelet coefficients to fix an issue with BW5.
import numpy as np
import math
import h5py
import pywt
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg
from datetime import datetime, timedelta
import sys
from time import perf_counter


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(timedelta(seconds=value))[:-3] for value in values]


class MainWindow(QMainWindow):
    def __init__(self, x, y):
        super().__init__()
        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        time_axis = TimeAxisItem(orientation="bottom")
        self.graphWidget.setAxisItems({"bottom": time_axis})

        view_box = self.graphWidget.getPlotItem().getViewBox()

        curve = self.graphWidget.plot(pen=pg.mkPen("w", width=3))
        print(f"Ayyo I'm about to plot {len(x)} points")
        curve.setData(x, y)
        curve.setDownsampling(auto=True, method="peak", ds=100)
        curve.setClipToView(True)
        self.graphWidget.setTitle("Reconstructed Raw Signal")
        self.graphWidget.setLabel("left", "ADC Count")
        self.graphWidget.setLabel("bottom", "Time (hh:mm:ss.ms)")


def get_channel_index(row, col):
    if not (1 <= row <= 64 and 1 <= col <= 64):
        raise ValueError("Row and column must be between 1 and 64")

    return ((row - 1) * 64 + col) - 1


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
    chIdx = get_channel_index(45, 42)
    print(f"Channel index: {chIdx}")

    with h5py.File(file_path, "r") as file:
        samplingRate = file.attrs["SamplingRate"]
        nChannels = len(file["Well_A1/StoredChIdxs"])
        compressionLevel = file["Well_A1/WaveletBasedEncodedRaw"].attrs[
            "CompressionLevel"
        ]
        framesChunkLength = file["Well_A1/WaveletBasedEncodedRaw"].attrs[
            "DataChunkLength"
        ]
        coefsChunkLength = math.ceil(framesChunkLength / pow(2, compressionLevel)) * 2

        toc = file["TOC"][:]
        wavelet_toc = file["Well_A1/WaveletBasedEncodedRawTOC"][:]

        data = []
        # for i in range(605, 607):
        start = perf_counter()
        for i in range(len(toc) - 1):
            frame_start, frame_end = toc[i][:2]
            coefs_start = wavelet_toc[i]
            coefs_end = wavelet_toc[i + 1] if i + 1 < len(wavelet_toc) else None

            chunk_coefs = file["Well_A1/WaveletBasedEncodedRaw"][coefs_start:coefs_end]
            chunk_data = reconstruct_chunk(
                chunk_coefs, compressionLevel, chIdx, nChannels, coefsChunkLength
            )
            data.extend(chunk_data)
        end = perf_counter()
        print(f"Time taken: {end - start}")

    x = np.arange(0, len(data), 1) / samplingRate
    y = np.array(data, dtype=float)

    app = QApplication(sys.argv)
    main_window = MainWindow(x, y)
    main_window.show()
    sys.exit(app.exec_())


def reconstruct_chunk(
    chunk_coefs, compressionLevel, chIdx, nChannels, coefsChunkLength
):
    chunk_data = []
    coefsPosition = chIdx * coefsChunkLength
    while coefsPosition < len(chunk_coefs):
        coefs = chunk_coefs[coefsPosition : coefsPosition + coefsChunkLength]
        length = int(len(coefs) / 2)
        approx, details = coefs[:length], coefs[length:]
        offset = -5
        approx = np.roll(approx, offset)
        details = np.roll(details, offset)
        wavelet = "sym7"
        mode = "periodization"
        frames = pywt.idwt(approx, details, wavelet, mode)
        for i in range(1, compressionLevel):
            frames = pywt.idwt(frames, None, wavelet, mode)
        chunk_data.extend(frames[2:-2])
        coefsPosition += coefsChunkLength * nChannels
    return chunk_data


if __name__ == "__main__":
    main()
