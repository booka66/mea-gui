#include <H5Cpp.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdlib> // for getenv
#include <iostream>
#include <mutex>
#include <numeric>
#include <pwd.h> // for getpwuid
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <thread>
#include <vector>

namespace py = pybind11;

struct ChannelData {
  std::vector<double> signal;
  std::vector<int> name;
};

struct ElectrodeInfo {
  int Row;
  int Col;
};

struct DetectionResult {
  std::vector<std::vector<double>> SzTimes;
  std::vector<std::vector<double>> DischargeTimes;
  std::vector<std::vector<double>> SETimes;
};

struct ChannelDetectionResult {
  int Row;
  int Col;
  std::vector<double> signal;
  DetectionResult result;
};

struct Peak {
  int index;
  double value;
};

std::vector<int> findpeaks(const std::vector<double> &data,
                           double min_peak_height) {
  std::vector<int> peaks;
  for (int i = 1; i < static_cast<int>(data.size()) - 1; ++i) {
    if (data[i] > data[i - 1] && data[i] > data[i + 1] &&
        data[i] >= min_peak_height) {
      peaks.push_back(i);
    }
  }
  return peaks;
}

std::vector<double> movvar(const std::vector<double> &V, int window_size) {
  std::vector<double> result(V.size() - window_size + 1);
  double sum = 0, sum_sq = 0;
  for (int i = 0; i < window_size; ++i) {
    sum += V[i];
    sum_sq += V[i] * V[i];
  }
  for (size_t i = 0; i <= V.size() - window_size; ++i) {
    if (i > 0) {
      sum = sum - V[i - 1] + V[i + window_size - 1];
      sum_sq = sum_sq - V[i - 1] * V[i - 1] +
               V[i + window_size - 1] * V[i + window_size - 1];
    }
    double mean = sum / window_size;
    double variance = std::max(0.0, (sum_sq / window_size) - (mean * mean));
    result[i] = variance;
  }
  return result;
}

DetectionResult SzSEDetectLEGIT(std::vector<double> V, double sampRate,
                                const std::vector<double> &t,
                                bool do_analysis) {
  DetectionResult result;

  if (!do_analysis || V.empty() || t.empty() || V.size() != t.size()) {
    return result;
  }

  // Timing Variables
  double ScanSize = 2.0;
  double Vthresh = 6.0;
  double varThresh = 6.0;
  double LookAheadTime = 10.0;
  double SELimTime = 25.0;
  int SEDurLim = ceil(5 * 60 * sampRate);
  double RefInc = 1.2;

  // Determine Reference section
  double Refsize = 2.0;
  int step_size = static_cast<int>(floor(sampRate));
  double TotRefCheck = floor(t.back() / 4);

  int window_size = static_cast<int>(ceil(sampRate * 60 * Refsize));
  int VtoCheck = static_cast<int>(floor(sampRate * 60 * TotRefCheck));

  std::vector<int> range;
  for (int i = ceil(sampRate * 15); i <= (VtoCheck - window_size + 1);
       i += step_size) {
    range.push_back(i);
  }

  bool refSeek = true;
  double coef = 0.5;

  std::vector<int> refRange;
  std::vector<double> VRef;

  while (refSeek) {
    double mean_abs_V = std::accumulate(V.begin(), V.end(), 0.0,
                                        [](double sum, double val) {
                                          return sum + std::abs(val);
                                        }) /
                        V.size();
    double std_abs_V = std::sqrt(
        std::inner_product(V.begin(), V.end(), V.begin(), 0.0, std::plus<>(),
                           [mean_abs_V](double a, double b) {
                             return std::pow(std::abs(a) - mean_abs_V, 2);
                           }) /
        V.size());
    double refpeakThresh = mean_abs_V + coef * std_abs_V;

    for (int i : range) {
      int end_index =
          std::min(i + window_size - 1, static_cast<int>(V.size()) - 1);
      if (end_index <= i)
        break;

      std::vector<double> window_data(V.begin() + i, V.begin() + end_index + 1);
      auto peaks = findpeaks(window_data, refpeakThresh);

      if (peaks.empty()) {
        refRange.clear();
        for (int k = i; k <= end_index; ++k)
          refRange.push_back(k);
        refSeek = false;
        break;
      }
    }
    coef *= RefInc;
    RefInc = std::pow(RefInc, 2);
  }

  std::vector<double> tRef = {t[refRange.front()], t[refRange.back()]};
  for (int idx : refRange)
    VRef.push_back(V[idx]);

  double ref_mean = std::accumulate(VRef.begin(), VRef.end(), 0.0,
                                    [](double sum, double val) {
                                      return sum + std::abs(val);
                                    }) /
                    VRef.size();
  double ref_std =
      std::sqrt(std::inner_product(VRef.begin(), VRef.end(), VRef.begin(), 0.0,
                                   std::plus<>(),
                                   [ref_mean](double a, double b) {
                                     return std::pow(std::abs(a) - ref_mean, 2);
                                   }) /
                VRef.size());
  double Vuplim = ref_mean + Vthresh * ref_std;

  std::vector<int> outlier_indices;
  for (int i = 0; i < V.size(); ++i) {
    if (std::abs(V[i]) > Vuplim)
      outlier_indices.push_back(i);
  }

  window_size = ScanSize * ceil(sampRate);
  auto moving_var = movvar(V, window_size);

  std::vector<double> tVar(t.begin() + window_size / 2,
                           t.end() - window_size / 2);

  auto tRef_start = std::lower_bound(tVar.begin(), tVar.end(), tRef[0]);
  auto tRef_end = std::lower_bound(tVar.begin(), tVar.end(), tRef[1]);
  std::vector<double> refVar(moving_var.begin() + (tRef_start - tVar.begin()),
                             moving_var.begin() + (tRef_end - tVar.begin()));

  double varLim =
      std::accumulate(refVar.begin(), refVar.end(), 0.0) / refVar.size() +
      varThresh *
          std::sqrt(std::inner_product(refVar.begin(), refVar.end(),
                                       refVar.begin(), 0.0, std::plus<>(),
                                       [&](double a, double b) {
                                         return std::pow(a - refVar[0], 2);
                                       }) /
                    refVar.size());

  std::vector<bool> PassPts(t.size(), false);
  std::vector<int> chkpts;
  std::copy_if(outlier_indices.begin(), outlier_indices.end(),
               std::back_inserter(chkpts),
               [&](int i) { return i > ((sampRate * ScanSize) / 2); });

  int adjust = std::max(
      0, static_cast<int>(std::lower_bound(t.begin(), t.end(), tVar[0]) -
                          t.begin() - 1));
  std::vector<double> moving_varMod(t.size(), 0);
  std::copy(moving_var.begin(), moving_var.end(),
            moving_varMod.begin() + adjust);

  for (int pt : chkpts) {
    if (pt < moving_varMod.size() && moving_varMod[pt] > varLim)
      PassPts[pt] = true;
  }

  int checkLim = ceil(ScanSize * sampRate);
  std::vector<bool> discharge_list(PassPts.size(), false);

  std::vector<int> trueIndices;
  for (size_t i = 0; i < PassPts.size(); ++i) {
    if (PassPts[i])
      trueIndices.push_back(i);
  }

  if (trueIndices.empty())
    return result;

  for (size_t i = 0; i < trueIndices.size() - 1; ++i) {
    if (trueIndices[i + 1] - trueIndices[i] <= checkLim) {
      size_t start = trueIndices[i];
      size_t end = std::min(static_cast<size_t>(trueIndices[i + 1] + 1),
                            discharge_list.size());
      std::fill(discharge_list.begin() + start, discharge_list.begin() + end,
                true);
    }
  }

  int LenLim = sampRate * 10;
  std::vector<bool> tenSecSz(discharge_list.size(), false);

  int start = -1;
  for (size_t i = 0; i < discharge_list.size(); ++i) {
    if (discharge_list[i] && start == -1)
      start = i;
    else if (!discharge_list[i] && start != -1) {
      if (static_cast<int>(i - start) >= LenLim) {
        std::fill(tenSecSz.begin() + start, tenSecSz.begin() + i, true);
      }
      start = -1;
    }
  }

  std::vector<int> SzEndIdxs;
  for (size_t i = 1; i < tenSecSz.size(); ++i) {
    if (tenSecSz[i - 1] && !tenSecSz[i])
      SzEndIdxs.push_back(i - 1);
  }

  int EventLim = ceil(LookAheadTime * sampRate);
  std::vector<bool> AfterDischarges(discharge_list.size(), false);

  for (int idx : SzEndIdxs) {
    size_t current_idx = idx;
    while (current_idx < discharge_list.size()) {
      size_t end_idx =
          std::min(current_idx + EventLim - 1, discharge_list.size() - 1);
      auto it = std::find(discharge_list.begin() + current_idx,
                          discharge_list.begin() + end_idx + 1, true);
      if (it != discharge_list.begin() + end_idx + 1) {
        size_t nextTrue = it - discharge_list.begin();
        std::fill(AfterDischarges.begin() + current_idx - 1,
                  AfterDischarges.begin() + nextTrue + 1, true);
        current_idx = nextTrue + 1;
      } else {
        break;
      }
    }
  }

  int SELim = sampRate * SELimTime;
  std::vector<bool> SECand(discharge_list.size(), false);

  for (size_t i = 0; i < trueIndices.size() - 1; ++i) {
    if (trueIndices[i + 1] - trueIndices[i] <= SELim) {
      size_t start = trueIndices[i];
      size_t end =
          std::min(static_cast<size_t>(trueIndices[i + 1] + 1), SECand.size());
      std::fill(SECand.begin() + start, SECand.begin() + end, true);
    }
  }

  std::vector<bool> SEList(discharge_list.size(), false);

  start = -1;
  for (size_t i = 0; i < SECand.size(); ++i) {
    if (SECand[i] && start == -1)
      start = i;
    else if (!SECand[i] && start != -1) {
      if (static_cast<int>(i - start) >= SEDurLim) {
        std::fill(SEList.begin() + start, SEList.begin() + i, true);
      }
      start = -1;
    }
  }

  for (size_t i = 0; i < tenSecSz.size(); ++i) {
    tenSecSz[i] = tenSecSz[i] || AfterDischarges[i];
  }

  for (size_t i = 0; i < tenSecSz.size(); ++i) {
    if (tenSecSz[i] && SEList[i])
      tenSecSz[i] = false;
  }

  for (size_t i = 0; i < discharge_list.size(); ++i) {
    if (discharge_list[i] && (tenSecSz[i] || SEList[i]))
      discharge_list[i] = false;
  }

  auto find_events = [&](const std::vector<bool> &events) {
    std::vector<std::vector<double>> times;
    int start = -1;
    for (size_t i = 0; i < events.size(); ++i) {
      if (events[i] && start == -1)
        start = i;
      else if (!events[i] && start != -1) {
        double event_power = std::accumulate(moving_varMod.begin() + start,
                                             moving_varMod.begin() + i, 0.0) /
                             (i - start);
        times.push_back({t[start], t[i - 1], event_power});
        start = -1;
      }
    }
    if (start != -1 && start < t.size()) {
      double event_power = std::accumulate(moving_varMod.begin() + start,
                                           moving_varMod.end(), 0.0) /
                           (t.size() - start);
      times.push_back({t[start], t.back(), event_power});
    }
    return times;
  };

  result.SzTimes = find_events(tenSecSz);
  result.DischargeTimes = find_events(discharge_list);
  result.SETimes = find_events(SEList);

  auto calculate_power = [&](std::vector<std::vector<double>> &times) {
    for (auto &event : times) {
      // Adjust the time values for power calculation
      auto start_it = std::lower_bound(t.rbegin(), t.rend(), event[0]);
      auto end_it = std::lower_bound(t.rbegin(), t.rend(), event[1]);
      if (start_it == t.rend() || end_it == t.rend())
        continue;
      size_t start_idx = t.rend() - start_it - 1;
      size_t end_idx = t.rend() - end_it - 1;
      if (start_idx >= moving_varMod.size() ||
          end_idx >= moving_varMod.size() || end_idx > start_idx)
        continue;
      event[2] = std::accumulate(moving_varMod.begin() + end_idx,
                                 moving_varMod.begin() + start_idx + 1, 0.0) /
                 (start_idx - end_idx + 1);
    }
  };

  calculate_power(result.SzTimes);
  calculate_power(result.DischargeTimes);
  calculate_power(result.SETimes);

  return result;
}

std::pair<std::vector<int>, std::vector<int>>
getChs(const std::string &FilePath) {
  std::cout << "getChs: Reading channel information from " << FilePath
            << std::endl;
  try {
    H5::H5File file(FilePath, H5F_ACC_RDONLY);
    H5::DataSet dataset = file.openDataSet("/3BRecInfo/3BMeaStreams/Raw/Chs");
    H5::DataSpace dataspace = dataset.getSpace();
    hsize_t dims[2];
    int ndims = dataspace.getSimpleExtentDims(dims, NULL);

    H5::CompType mtype(sizeof(int) * 2);
    mtype.insertMember("Row", 0, H5::PredType::NATIVE_INT);
    mtype.insertMember("Col", sizeof(int), H5::PredType::NATIVE_INT);

    std::vector<std::pair<int, int>> data(dims[0]);
    dataset.read(data.data(), mtype);

    std::vector<int> rows(dims[0]);
    std::vector<int> cols(dims[0]);

    for (size_t i = 0; i < dims[0]; ++i) {
      rows[i] = data[i].first;
      cols[i] = data[i].second;
    }

    std::cout << "getChs: Successfully read " << dims[0] << " channels"
              << std::endl;
    return std::make_pair(std::move(rows), std::move(cols));
  } catch (H5::Exception &error) {
    std::cerr << "getChs: H5 Exception: ";
    error.printErrorStack();
    throw std::runtime_error("Error reading HDF5 file");
  } catch (std::exception &e) {
    std::cerr << "getChs: Standard exception: " << e.what() << std::endl;
    throw;
  } catch (...) {
    std::cerr << "getChs: Unknown exception occurred" << std::endl;
    throw;
  }
}

std::vector<ChannelData> get_cat_envelop(const std::string &FileName) {
  try {
    H5::H5File file(FileName, H5F_ACC_RDONLY);

    auto readDataset = [&file](const std::string &path) {
      H5::DataSet dataset = file.openDataSet(path);
      H5::DataSpace dataspace = dataset.getSpace();
      H5T_class_t type_class = dataset.getTypeClass();

      if (type_class == H5T_INTEGER) {
        int data;
        dataset.read(&data, H5::PredType::NATIVE_INT);
        return static_cast<double>(data);
      } else if (type_class == H5T_FLOAT) {
        double data;
        dataset.read(&data, H5::PredType::NATIVE_DOUBLE);
        return data;
      } else {
        throw std::runtime_error("Unsupported data type");
      }
    };

    long long NRecFrames =
        static_cast<long long>(readDataset("/3BRecInfo/3BRecVars/NRecFrames"));
    double sampRate = readDataset("/3BRecInfo/3BRecVars/SamplingRate");
    double signalInversion =
        readDataset("/3BRecInfo/3BRecVars/SignalInversion");
    double maxUVolt = readDataset("/3BRecInfo/3BRecVars/MaxVolt");
    double minUVolt = readDataset("/3BRecInfo/3BRecVars/MinVolt");
    int bitDepth =
        static_cast<int>(readDataset("/3BRecInfo/3BRecVars/BitDepth"));

    uint64_t qLevel =
        static_cast<uint64_t>(1) ^ static_cast<uint64_t>(bitDepth);

    double fromQLevelToUVolt =
        (maxUVolt - minUVolt) / static_cast<double>(qLevel);
    double ADCCountsToMV = signalInversion * fromQLevelToUVolt;
    double MVOffset = signalInversion * minUVolt;

    auto [Rows, Cols] = getChs(FileName);
    int total_channels = Rows.size();

    H5::DataSet full_data = file.openDataSet("/3BData/Raw");
    H5::DataSpace dataspace = full_data.getSpace();
    int rank = dataspace.getSimpleExtentNdims();
    std::vector<hsize_t> dims(rank);
    dataspace.getSimpleExtentDims(dims.data(), NULL);

    if (rank != 1) {
      throw std::runtime_error("Unexpected number of dimensions in raw data");
    }

    if (dims[0] != static_cast<hsize_t>(NRecFrames * total_channels)) {
      std::cerr << "Warning: Data size mismatch. Expected size: "
                << NRecFrames * total_channels << ", Actual size: " << dims[0]
                << std::endl;
    }

    std::vector<ChannelData> channelDataList;
    channelDataList.reserve(total_channels);

    std::vector<int16_t> all_data(dims[0]);
    full_data.read(all_data.data(), H5::PredType::NATIVE_INT16);

    for (int k = 0; k < total_channels; ++k) {
      ChannelData ch_data;
      ch_data.signal.reserve(NRecFrames);

      for (long long i = 0; i < NRecFrames; ++i) {
        double val = static_cast<double>(all_data[i * total_channels + k]);
        val = (val * ADCCountsToMV + MVOffset) / 1000000.0; // Convert to mV
        ch_data.signal.push_back(val);
      }
      double mean =
          std::accumulate(ch_data.signal.begin(), ch_data.signal.end(), 0.0) /
          ch_data.signal.size();

      for (auto &val : ch_data.signal) {
        val -= mean;
      }

      ch_data.name = {Rows[k], Cols[k]};
      channelDataList.push_back(std::move(ch_data));
    }

    return channelDataList;
  } catch (H5::Exception &error) {
    std::cerr << "H5 Exception: ";
    error.printErrorStack();
    throw std::runtime_error("Error reading HDF5 file");
  } catch (std::exception &e) {
    std::cerr << "Standard exception: " << e.what() << std::endl;
    throw;
  } catch (...) {
    std::cerr << "Unknown exception occurred" << std::endl;
    throw;
  }
}

std::string expandTilde(const std::string &path) {
  if (path.empty() || path[0] != '~') {
    return path;
  }

  const char *home = getenv("HOME");
  if (home == nullptr) {
    home = getpwuid(getuid())->pw_dir;
  }

  return std::string(home) + path.substr(1);
}

std::vector<ChannelDetectionResult>
processAllChannels(const std::string &filename, bool do_analysis) {
  std::cout << "processAllChannels: Starting processing for file: " << filename
            << std::endl;
  std::string expandedFilename = expandTilde(filename);
  std::cout << "processAllChannels: Expanded filename: " << expandedFilename
            << std::endl;

  std::cout << "processAllChannels: Getting channel data..." << std::endl;
  std::vector<ChannelData> channelDataList = get_cat_envelop(expandedFilename);
  std::cout << "processAllChannels: Retrieved data for "
            << channelDataList.size() << " channels" << std::endl;

  std::cout << "processAllChannels: Getting sampling rate..." << std::endl;
  H5::H5File file(expandedFilename, H5F_ACC_RDONLY);
  H5::DataSet sampRateDataset =
      file.openDataSet("/3BRecInfo/3BRecVars/SamplingRate");
  double sampRate;
  sampRateDataset.read(&sampRate, H5::PredType::NATIVE_DOUBLE);
  std::cout << "processAllChannels: Sampling rate: " << sampRate << std::endl;

  std::vector<ChannelDetectionResult> allResults(channelDataList.size());
  std::mutex resultsMutex;
  std::atomic<size_t> processedCount(0);

  auto processChannel = [&](size_t start, size_t end) {
    for (size_t i = start; i < end; ++i) {
      const auto &channelData = channelDataList[i];
      ChannelDetectionResult channelResult;
      channelResult.Row = channelData.name[0];
      channelResult.Col = channelData.name[1];
      channelResult.signal = channelData.signal;

      std::vector<double> t(channelData.signal.size());
      for (size_t j = 0; j < t.size(); ++j) {
        t[j] = static_cast<double>(j) / sampRate;
      }

      channelResult.result =
          SzSEDetectLEGIT(channelData.signal, sampRate, t, do_analysis);

      {
        std::lock_guard<std::mutex> lock(resultsMutex);
        allResults[i] = std::move(channelResult);
      }

      size_t currentProcessed = ++processedCount;
      if (currentProcessed % 10 == 0 ||
          currentProcessed == channelDataList.size()) {
        std::cout << "processAllChannels: Processed " << currentProcessed
                  << " of " << channelDataList.size() << " channels"
                  << std::endl;
      }
    }
  };

  unsigned int numThreads = std::thread::hardware_concurrency();
  std::vector<std::thread> threads;
  size_t chunkSize = channelDataList.size() / numThreads;
  size_t remainder = channelDataList.size() % numThreads;

  size_t start = 0;
  for (unsigned int i = 0; i < numThreads; ++i) {
    size_t end = start + chunkSize + (i < remainder ? 1 : 0);
    threads.emplace_back(processChannel, start, end);
    start = end;
  }

  for (auto &thread : threads) {
    thread.join();
  }

  std::cout << "processAllChannels: Finished processing all channels"
            << std::endl;
  return allResults;
}

PYBIND11_MODULE(sz_se_detect, m) {
  py::class_<DetectionResult>(m, "DetectionResult")
      .def_readwrite("SzTimes", &DetectionResult::SzTimes)
      .def_readwrite("DischargeTimes", &DetectionResult::DischargeTimes)
      .def_readwrite("SETimes", &DetectionResult::SETimes);

  py::class_<ChannelDetectionResult>(m, "ChannelDetectionResult")
      .def_readwrite("Row", &ChannelDetectionResult::Row)
      .def_readwrite("Col", &ChannelDetectionResult::Col)
      .def_readwrite("signal", &ChannelDetectionResult::signal)
      .def_readwrite("result", &ChannelDetectionResult::result);

  m.def("processAllChannels", &processAllChannels,
        "Process all channels in the given file", py::arg("filename"),
        py::arg("do_analysis") = true);
}
