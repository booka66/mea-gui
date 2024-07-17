#include <algorithm>
#include <cmath>
#include <numeric>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>

namespace py = pybind11;

class SignalAnalyzer {
public:
  SignalAnalyzer(py::array_t<double> time_vector, double n_std_dev = 4,
                 int distance = 70, double slope_threshold = 2,
                 double sampling_rate = 100)
      : time_vector(time_vector), n_std_dev(n_std_dev), distance(distance),
        slope_threshold(slope_threshold), sampling_rate(sampling_rate),
        baseline_window(static_cast<int>(sampling_rate * 0.2)),
        snr_threshold(35) {}

  static double find_baseline(const std::vector<double> &signal) {
    std::vector<double> sorted_signal = signal;
    std::nth_element(sorted_signal.begin(),
                     sorted_signal.begin() + sorted_signal.size() / 2,
                     sorted_signal.end());
    return sorted_signal[sorted_signal.size() / 2];
  }

  // Getters and setters for class attributes
  double get_n_std_dev() const { return n_std_dev; }
  void set_n_std_dev(double n_std_dev) { this->n_std_dev = n_std_dev; }

  int get_distance() const { return distance; }
  void set_distance(int distance) { this->distance = distance; }

  double get_slope_threshold() const { return slope_threshold; }
  void set_slope_threshold(double slope_threshold) {
    this->slope_threshold = slope_threshold;
  }

  double get_sampling_rate() const { return sampling_rate; }
  void set_sampling_rate(double sampling_rate) {
    this->sampling_rate = sampling_rate;
  }

  int get_baseline_window() const { return baseline_window; }
  void set_baseline_window(int baseline_window) {
    this->baseline_window = baseline_window;
  }

  double get_snr_threshold() const { return snr_threshold; }
  void set_snr_threshold(double snr_threshold) {
    this->snr_threshold = snr_threshold;
  }

  std::tuple<py::array_t<double>, py::array_t<double>, py::array_t<double>,
             py::array_t<double>>
  analyze_signal(py::array_t<double> volt_signal, double start, double stop) {
    py::buffer_info time_buf = time_vector.request();
    py::buffer_info volt_buf = volt_signal.request();

    if (time_buf.ndim != 1 || volt_buf.ndim != 1)
      throw std::runtime_error("Number of dimensions must be one");

    if (time_buf.size != volt_buf.size)
      throw std::runtime_error("Input shapes must match");

    auto time_ptr = static_cast<double *>(time_buf.ptr);
    auto volt_ptr = static_cast<double *>(volt_buf.ptr);
    size_t n = time_buf.size;

    // Find region indices
    size_t region_start_index =
        std::lower_bound(time_ptr, time_ptr + n, start) - time_ptr;
    size_t region_stop_index =
        std::lower_bound(time_ptr, time_ptr + n, stop) - time_ptr;

    // Extract region data
    std::vector<double> region_x(time_ptr + region_start_index,
                                 time_ptr + region_stop_index);
    std::vector<double> region_y(volt_ptr + region_start_index,
                                 volt_ptr + region_stop_index);

    // Calculate signal energy and background noise level
    double signal_energy = std::inner_product(region_y.begin(), region_y.end(),
                                              region_y.begin(), 0.0);
    double background_noise = find_baseline(region_y);

    // Calculate SNR
    double snr =
        signal_energy / (std::pow(background_noise, 2) * region_y.size());
    if (snr < snr_threshold) {
      return std::make_tuple(py::array_t<double>(), py::array_t<double>(),
                             py::array_t<double>(), py::array_t<double>());
    }

    // Calculate mean and standard deviation
    double mu = std::accumulate(region_y.begin(), region_y.end(), 0.0) /
                region_y.size();
    double sq_sum = std::inner_product(region_y.begin(), region_y.end(),
                                       region_y.begin(), 0.0);
    double sigma = std::sqrt(sq_sum / region_y.size() - mu * mu);

    // Find peaks and valleys
    double peak_threshold = mu + n_std_dev * sigma;
    double valley_threshold = mu - n_std_dev * sigma;
    std::vector<size_t> peak_indices =
        find_peaks(region_y, peak_threshold, distance);
    std::vector<size_t> valley_indices =
        find_peaks(negate(region_y), -valley_threshold, distance);

    // Combine and sort indices
    std::vector<size_t> all_indices;
    all_indices.reserve(peak_indices.size() + valley_indices.size());
    all_indices.insert(all_indices.end(), peak_indices.begin(),
                       peak_indices.end());
    all_indices.insert(all_indices.end(), valley_indices.begin(),
                       valley_indices.end());
    std::sort(all_indices.begin(), all_indices.end());

    if (all_indices.empty()) {
      return std::make_tuple(py::array_t<double>(), py::array_t<double>(),
                             py::array_t<double>(), py::array_t<double>());
    }

    // Process peaks and find discharge starts
    std::vector<double> peak_x, peak_y, discharge_start_x, discharge_start_y;
    for (size_t peak_index : all_indices) {
      peak_x.push_back(region_x[peak_index]);
      peak_y.push_back(region_y[peak_index]);

      size_t baseline_start =
          (peak_index > static_cast<size_t>(baseline_window))
              ? peak_index - baseline_window
              : 0;
      double baseline = find_baseline(std::vector<double>(
          region_y.begin() + baseline_start, region_y.begin() + peak_index));

      // Find the steepest point closest to the peak
      size_t steepest_point_index =
          find_steepest_point(region_y, baseline_start, peak_index);

      if (steepest_point_index != peak_index) {
        discharge_start_x.push_back(region_x[steepest_point_index]);
        discharge_start_y.push_back(region_y[steepest_point_index]);
      }
    }

    // Filter discharges
    if (!discharge_start_x.empty()) {
      std::vector<size_t> discharge_indices(discharge_start_x.size());
      for (size_t i = 0; i < discharge_start_x.size(); ++i) {
        discharge_indices[i] =
            std::lower_bound(region_x.begin(), region_x.end(),
                             discharge_start_x[i]) -
            region_x.begin();
      }

      std::vector<bool> mask(discharge_indices.size());
      mask[0] = true;
      for (size_t i = 1; i < discharge_indices.size(); ++i) {
        mask[i] = (discharge_indices[i] - discharge_indices[i - 1] >=
                   static_cast<size_t>(distance));
      }

      std::vector<double> filtered_discharge_start_x,
          filtered_discharge_start_y;
      for (size_t i = 0; i < mask.size(); ++i) {
        if (mask[i]) {
          filtered_discharge_start_x.push_back(discharge_start_x[i]);
          filtered_discharge_start_y.push_back(discharge_start_y[i]);
        }
      }

      return std::make_tuple(
          py::array_t<double>(peak_x.size(), peak_x.data()),
          py::array_t<double>(peak_y.size(), peak_y.data()),
          py::array_t<double>(filtered_discharge_start_x.size(),
                              filtered_discharge_start_x.data()),
          py::array_t<double>(filtered_discharge_start_y.size(),
                              filtered_discharge_start_y.data()));
    } else {
      return std::make_tuple(py::array_t<double>(peak_x.size(), peak_x.data()),
                             py::array_t<double>(peak_y.size(), peak_y.data()),
                             py::array_t<double>(), py::array_t<double>());
    }
  }

private:
  py::array_t<double> time_vector;
  double n_std_dev;
  int distance;
  double slope_threshold;
  double sampling_rate;
  int baseline_window;
  double snr_threshold;

  std::vector<size_t> find_peaks(const std::vector<double> &signal,
                                 double height, int distance) {
    std::vector<size_t> peaks;
    for (size_t i = 1; i < signal.size() - 1; ++i) {
      if (signal[i] > height && signal[i] > signal[i - 1] &&
          signal[i] > signal[i + 1]) {
        if (peaks.empty() ||
            i - peaks.back() >= static_cast<size_t>(distance)) {
          peaks.push_back(i);
        }
      }
    }
    return peaks;
  }

  std::vector<double> negate(const std::vector<double> &vec) {
    std::vector<double> result(vec.size());
    std::transform(vec.begin(), vec.end(), result.begin(),
                   std::negate<double>());
    return result;
  }
  size_t find_steepest_point(const std::vector<double> &signal, size_t start,
                             size_t end) {
    double max_slope = 0;
    size_t steepest_point = end;

    for (size_t i = start + 1; i < end; ++i) {
      double slope = std::abs(signal[i] - signal[i - 1]);
      if (slope > max_slope || (slope == max_slope && i > steepest_point)) {
        max_slope = slope;
        steepest_point = i;
      }
    }

    return steepest_point;
  }
};

PYBIND11_MODULE(signal_analyzer, m) {
  py::class_<SignalAnalyzer>(m, "SignalAnalyzer")
      .def(py::init<py::array_t<double>, double, int, double, double>(),
           py::arg("time_vector"), py::arg("n_std_dev") = 3,
           py::arg("distance") = 50, py::arg("slope_threshold") = 2,
           py::arg("sampling_rate") = 100)
      .def("analyze_signal", &SignalAnalyzer::analyze_signal)
      .def_static("find_baseline", &SignalAnalyzer::find_baseline)
      // Expose getters and setters
      .def_property("n_std_dev", &SignalAnalyzer::get_n_std_dev,
                    &SignalAnalyzer::set_n_std_dev)
      .def_property("distance", &SignalAnalyzer::get_distance,
                    &SignalAnalyzer::set_distance)
      .def_property("slope_threshold", &SignalAnalyzer::get_slope_threshold,
                    &SignalAnalyzer::set_slope_threshold)
      .def_property("sampling_rate", &SignalAnalyzer::get_sampling_rate,
                    &SignalAnalyzer::set_sampling_rate)
      .def_property("baseline_window", &SignalAnalyzer::get_baseline_window,
                    &SignalAnalyzer::set_baseline_window)
      .def_property("snr_threshold", &SignalAnalyzer::get_snr_threshold,
                    &SignalAnalyzer::set_snr_threshold);
}
