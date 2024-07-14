import os
import h5py
import site

for path in site.getsitepackages():
    hdf5_dir = os.path.join(path, "h5py", ".libs")
    if os.path.exists(hdf5_dir):
        print(f"HDF5 directory: {hdf5_dir}")
        break
else:
    print("HDF5 directory not found")
