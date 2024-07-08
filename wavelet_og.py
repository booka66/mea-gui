import numpy as np
import math
import matplotlib.pyplot as plt
import h5py
import pywt

# variables
file_path = "/Volumes/T7/Neocortical Seizures/6-24-2024-slice2c.brw"
chIdx = 145
# open the BRW file
file = h5py.File(file_path, "r")
# collect experiment information
samplingRate = file.attrs["SamplingRate"]
nChannels = len(file["Well_A1/StoredChIdxs"])
coefsTotalLength = len(file["Well_A1/WaveletBasedEncodedRaw"])
compressionLevel = file["Well_A1/WaveletBasedEncodedRaw"].attrs["CompressionLevel"]
framesChunkLength = file["Well_A1/WaveletBasedEncodedRaw"].attrs["DataChunkLength"]
coefsChunkLength = math.ceil(framesChunkLength / pow(2, compressionLevel)) * 2
# reconstruct all data for a given channel index
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
# close the file
file.close()
# visualize the reconstructed raw signal
x = np.arange(0, len(data), 1) / samplingRate
y = np.fromiter(data, float)


plt.figure()
plt.plot(x, y, color="blue")
plt.title("Reconstructed Raw Signal")
plt.xlabel("(sec)")
plt.ylabel("(ADC Count)")
plt.show()
