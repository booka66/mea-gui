import numpy as np
import pyqtgraph as pg
import pyaudio
from PyQt5 import QtCore, QtGui, QtWidgets

FS = 44100
CHUNKSZ = 1024 * 2


class MicrophoneRecorder:
    def __init__(self, signal):
        self.signal = signal
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=FS,
            input=True,
            frames_per_buffer=CHUNKSZ,
        )

    def read(self):
        data = self.stream.read(CHUNKSZ, exception_on_overflow=False)
        y = np.frombuffer(data, "int16")
        self.signal.emit(y)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class SpectrogramWidget(pg.PlotWidget):
    read_collected = QtCore.pyqtSignal(np.ndarray)

    def __init__(self):
        super(SpectrogramWidget, self).__init__()
        self.img = pg.ImageItem()
        self.addItem(self.img)
        self.img_array = np.zeros((1000, int(CHUNKSZ / 2 + 1)))

        # bipolar colormap
        pos = np.array([0.0, 1.0, 0.5, 0.25, 0.75])
        color = np.array(
            [
                [0, 255, 255, 255],
                [255, 255, 0, 255],
                [0, 0, 0, 255],
                (0, 0, 255, 255),
                (255, 0, 0, 255),
            ],
            dtype=np.ubyte,
        )
        cmap = pg.ColorMap(pos, color)
        cmap = pg.colormap.get("inferno")
        lut = cmap.getLookupTable(0.0, 1.0, 256)

        # set colormap
        self.img.setLookupTable(cmap.getLookupTable())
        self.img.setLevels([-50, 40])

        self.setLabel("left", "Frequency", units="Hz")

        # prepare window for later use
        self.win = np.hanning(CHUNKSZ)
        self.show()

    def update(self, chunk):
        spec = np.fft.rfft(chunk * self.win) / CHUNKSZ
        psd = abs(spec)
        psd = 20 * np.log10(psd)
        self.img_array = np.roll(self.img_array, -1, 0)
        self.img_array[-1:] = psd
        self.img.setImage(self.img_array, autoLevels=False)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = SpectrogramWidget()
    w.read_collected.connect(w.update)
    mic = MicrophoneRecorder(w.read_collected)
    interval = FS / CHUNKSZ
    t = QtCore.QTimer()
    t.timeout.connect(mic.read)
    t.start(int(1000 / interval))
    app.exec_()
    mic.close()
