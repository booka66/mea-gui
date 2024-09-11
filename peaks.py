import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import find_peaks


# Generate sample EEG-like data
def generate_sample_eeg(t, freq_components):
    eeg = np.zeros_like(t)
    for freq, amp in freq_components:
        eeg += amp * np.sin(2 * np.pi * freq * t)
    return eeg + np.random.normal(0, 0.5, t.shape)  # Add some noise


# Set up the time array and generate sample data
t = np.linspace(0, 10, 1000)
freq_components = [(10, 1), (20, 0.5), (30, 0.3)]  # (frequency, amplitude) pairs
eeg_data = generate_sample_eeg(t, freq_components)

# Perform CWT
widths = np.arange(1, 31)
cwt = signal.cwt(eeg_data, signal.ricker, widths)

# Sum CWT coefficients to get a measure of "peakiness"
peakiness = np.sum(np.abs(cwt), axis=0)

# Find peaks in the peakiness measure
peaks, _ = find_peaks(peakiness, height=np.std(peakiness), distance=20)

# Plot the results
plt.figure(figsize=(12, 12))

plt.subplot(411)
plt.plot(t, eeg_data)
plt.plot(t[peaks], eeg_data[peaks], "rx", markersize=10, label="Detected Peaks")
plt.title("Original EEG-like Signal with Detected Peaks")
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.legend()

plt.subplot(412)
plt.imshow(
    cwt,
    extent=[t[0], t[-1], 1, 31],
    cmap="PRGn",
    aspect="auto",
    vmax=abs(cwt).max(),
    vmin=-abs(cwt).max(),
)
plt.title("CWT of EEG Signal")
plt.xlabel("Time")
plt.ylabel("Scale")

plt.subplot(413)
plt.plot(t, peakiness)
plt.plot(t[peaks], peakiness[peaks], "rx", markersize=10)
plt.title("Peakiness Measure with Detected Peaks")
plt.xlabel("Time")
plt.ylabel("Peakiness")

# Add a subplot to show a zoomed-in view of the original signal with peaks
plt.subplot(414)
zoom_start, zoom_end = (
    2,
    4,
)  # Adjust these values to zoom into a specific part of the signal
mask = (t >= zoom_start) & (t <= zoom_end)
plt.plot(t[mask], eeg_data[mask])
peaks_in_zoom = peaks[(t[peaks] >= zoom_start) & (t[peaks] <= zoom_end)]
plt.plot(
    t[peaks_in_zoom],
    eeg_data[peaks_in_zoom],
    "rx",
    markersize=10,
    label="Detected Peaks",
)
plt.title("Zoomed View of EEG Signal with Detected Peaks")
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.legend()

plt.tight_layout()
plt.show()

# Print peak locations
print("Peaks found at times:", t[peaks])
