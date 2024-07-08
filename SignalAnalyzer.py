import numpy as np
import scipy.signal as signal


class SignalAnalyzer:
    def __init__(
        self,
        time_vector,
        n_std_dev=3,
        distance=50,
        slope_threshold=2,
        sampling_rate=100,
    ):
        self.time_vector = time_vector
        self.n_std_dev = n_std_dev
        self.distance = distance
        self.slope_threshold = slope_threshold
        self.sampling_rate = sampling_rate
        self.baseline_window = int(sampling_rate * 0.1)  # 0.1 second worth of samples
        self.snr_threshold = 4

    @staticmethod
    def find_baseline(signal):
        return np.median(signal)

    def analyze_signal(self, volt_signal, start, stop):
        region_start_index = np.searchsorted(self.time_vector, start)
        region_stop_index = np.searchsorted(self.time_vector, stop)
        region_x = self.time_vector[region_start_index:region_stop_index]
        region_y = volt_signal[region_start_index:region_stop_index]

        # Calculate signal energy and background noise level
        signal_energy = np.sum(np.square(region_y))
        background_noise = np.median(np.abs(region_y))

        # Calculate SNR
        snr = signal_energy / (background_noise**2 * len(region_y))
        if snr < self.snr_threshold:
            return [], [], [], []

        # Find peaks and valleys
        mu, sigma = np.mean(region_y), np.std(region_y)
        peak_threshold = mu + self.n_std_dev * sigma
        valley_threshold = mu - self.n_std_dev * sigma

        peak_indices, _ = signal.find_peaks(
            region_y, height=peak_threshold, distance=self.distance
        )
        valley_indices, _ = signal.find_peaks(
            -region_y, height=-valley_threshold, distance=self.distance
        )
        all_indices = np.sort(np.concatenate((peak_indices, valley_indices)))

        if len(all_indices) == 0:
            return [], [], [], []

        # Pre-allocate arrays
        peak_x = np.zeros(len(all_indices))
        peak_y = np.zeros(len(all_indices))
        discharge_start_x = []
        discharge_start_y = []

        # Process peaks and find discharge starts
        for i, peak_index in enumerate(all_indices):
            peak_x[i] = region_x[peak_index]
            peak_y[i] = region_y[peak_index]

            baseline_start = max(0, peak_index - self.baseline_window)
            baseline = self.find_baseline(region_y[baseline_start:peak_index])

            discharge_start = np.argmax(
                np.abs(region_y[baseline_start:peak_index] - baseline)
                > self.slope_threshold * sigma
            )
            if discharge_start != 0:  # If a discharge start is found
                discharge_start_index = baseline_start + discharge_start
                discharge_start_x.append(region_x[discharge_start_index])
                discharge_start_y.append(region_y[discharge_start_index])

        # Filter discharges
        if discharge_start_x:
            discharge_indices = np.searchsorted(region_x, discharge_start_x)
            mask = np.diff(np.concatenate(([0], discharge_indices))) >= self.distance
            filtered_discharge_start_x = np.array(discharge_start_x)[mask]
            filtered_discharge_start_y = np.array(discharge_start_y)[mask]
        else:
            filtered_discharge_start_x = []
            filtered_discharge_start_y = []

        return peak_x, peak_y, filtered_discharge_start_x, filtered_discharge_start_y
