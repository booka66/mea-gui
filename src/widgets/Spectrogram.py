import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets
from scipy.signal import spectrogram
from matplotlib import pyplot as plt

FS = 100  # Sampling frequency of the EEG data
CHUNKSZ = 1024  # Chunk size for FFT
OVERLAP = 64  # Overlap between chunks
FREQ_RANGE = (0.5, 50)  # Frequency range of interest for seizure activity


class SpectrogramWidget(pg.PlotWidget):
    def __init__(
        self,
        eeg_data,
        fs=100,
        chunk_size=1024,
        overlap=64,
        fs_range=(0.5, 50),
        linked_widget=None,
    ):
        super(SpectrogramWidget, self).__init__()

        self.img = pg.ImageItem()
        self.addItem(self.img)

        # Calculate spectrogram
        Sxx_db = self.calculate_spectrogram(eeg_data, fs, chunk_size, overlap, fs_range)

        # Set colormap
        cmap = pg.colormap.get("inferno")
        self.img.setLookupTable(cmap.getLookupTable())
        self.img.setLevels([np.min(Sxx_db), np.max(Sxx_db)])

        # Setup the correct scaling for y-axis
        freq = np.arange((chunk_size / 2) + 1) / (float(chunk_size) / fs)
        freq_mask = (freq >= fs_range[0]) & (freq <= fs_range[1])
        freq = freq[freq_mask]
        self.setLabel("left", "Frequency", units="Hz")
        self.setLabel("bottom", "Time", units="s")
        self.setXRange(0, eeg_data.shape[0] / fs)
        self.setYRange(fs_range[0], fs_range[1])

        if linked_widget is not None:
            self.setXLink(linked_widget)
            self.setYLink(linked_widget)

        self.show()
        self.getPlotItem().getViewBox().autoRange()

    def calculate_spectrogram(self, eeg_data, fs, chunk_size, overlap, fs_range):
        print(f"EEG data shape: {eeg_data.shape}")

        # Calculate spectrogram for the entire dataset at once
        f, t, Sxx = spectrogram(
            eeg_data,
            fs=fs,
            window="hann",
            nperseg=chunk_size,
            noverlap=overlap,
            nfft=chunk_size,
            scaling="density",
            mode="psd",
        )

        # Convert power spectral density to dB scale
        Sxx_db = 10 * np.log10(Sxx)

        # Extract the frequency range of interest
        freq_mask = (f >= fs_range[0]) & (f <= fs_range[1])
        Sxx_db = Sxx_db[freq_mask, :]

        # Set the image array
        self.img_array = Sxx_db
        self.img.setImage(
            self.img_array.T, autoLevels=False
        )  # Transpose the spectrogram array for correct orientation
        return Sxx_db
