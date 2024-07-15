import sz_se_detect
import numpy as np

# Assuming processAllChannels is a function in your module
results = sz_se_detect.processAllChannels(
    "D:\\Users\\booka66\\Downloads\\5_13_24_slice1B_resample_100.brw", True
)

for result in results:
    signal = np.array(result.signal, dtype=np.float16).squeeze()
    name = (result.Row, result.Col)
    SzTimes = np.array(result.result.SzTimes)
    SETimes = np.array(result.result.SETimes)
    DischargeTimes = np.array(result.result.DischargeTimes)
    print(signal, name, SzTimes, SETimes, DischargeTimes)
