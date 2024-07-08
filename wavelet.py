import h5py
import math
from matplotlib import pyplot as plt
import numpy as np
import pywt
from tqdm import tqdm
from multiprocessing import Pool, freeze_support

# variables
filePath = "/Users/booka66/Jake-Squared/Sz_SE_Detection/5_13_24_slice1B_BW5_00.brw"
downsample_factor = 190  # Adjust this value to control the downsampling factor

# open the BRW file
file = h5py.File(filePath, "r")

# collect experiment information
samplingRate = file.attrs["SamplingRate"]
nChannels = len(file["Well_A1/StoredChIdxs"])
coefsTotalLength = len(file["Well_A1/WaveletBasedEncodedRaw"])
compressionLevel = file["Well_A1/WaveletBasedEncodedRaw"].attrs["CompressionLevel"]
framesChunkLength = file["Well_A1/WaveletBasedEncodedRaw"].attrs["DataChunkLength"]
coefsChunkLength = math.ceil(framesChunkLength / pow(2, compressionLevel)) * 2


def reconstruct_signal(chIdx):
    # reconstruct data for the current channel
    data = []
    coefsPosition = chIdx * coefsChunkLength
    while coefsPosition < coefsTotalLength:
        coefs = file["Well_A1/WaveletBasedEncodedRaw"][
            coefsPosition : coefsPosition + coefsChunkLength
        ]
        length = int(len(coefs) / 2)
        frames = pywt.idwt(coefs[:length], coefs[length:], "sym7", "periodization")
        length *= 2
        for i in range(1, compressionLevel):
            frames = pywt.idwt(frames[:length], None, "sym7", "periodization")
            length *= 2
        data.extend(frames)
        coefsPosition += coefsChunkLength * nChannels

    # downsample the reconstructed data
    downsampled_data = data[::downsample_factor]
    downsampled_data = downsampled_data[:-100]

    # create a new figure for the current channel
    fig, ax = plt.subplots(figsize=(8, 6))

    # plot the downsampled reconstructed raw signal
    x = np.arange(0, len(downsampled_data), 1) / (samplingRate / downsample_factor)
    y = np.fromiter(downsampled_data, float)
    # change the stroke width to be smaller
    ax.plot(x, y, color="blue", linewidth=0.5)
    ax.set_title(f"Channel {chIdx}")
    ax.set_xlabel("(sec)")
    ax.set_ylabel("(ADC Count)")

    # save the figure
    plt.savefig(f"channel_{chIdx}.png")
    plt.close(fig)


if __name__ == "__main__":
    freeze_support()

    # get the number of channels to plot from user input
    num_channels_to_plot = int(input("Enter the number of channels to plot: "))

    # create a pool of worker processes
    pool = Pool()

    # iterate over the selected channels in parallel
    for _ in tqdm(
        pool.imap_unordered(reconstruct_signal, range(num_channels_to_plot)),
        total=num_channels_to_plot,
        desc="Reconstructing signals",
    ):
        pass

    # close the pool of worker processes
    pool.close()
    pool.join()

    # close the file
    file.close()
