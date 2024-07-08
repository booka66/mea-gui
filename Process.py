import h5py
import numpy as np


def process_channel(args):
    file_path, k, num_channels, adc_counts_to_mv, mv_offset, row, col = args
    with h5py.File(file_path, "r") as f:
        channel_data = f["/3BData/Raw"][k::num_channels]

    channel_data = channel_data.astype(np.float32)
    channel_data = (channel_data * adc_counts_to_mv + mv_offset) / 1_000_000
    channel_data -= np.mean(channel_data)

    return (
        row,
        col,
        {
            "signal": channel_data,
            "SzTimes": np.array([]),
            "SETimes": np.array([]),
            "DischargeTimes": np.array([]),
            "DischargeTrainsTimes": np.array([]),
        },
    )
