import os
import sys
from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11

# HDF5 paths
h5py_path = r"D:\Users\booka66\AppData\Local\Programs\Python\Python311\Lib\site-packages\h5py"
hdf5_dir = h5py_path  # The .dll files are in the main h5py directory
hdf5_include_dir = os.path.join(h5py_path, 'include')

# Verify directories exist
if not os.path.exists(hdf5_dir):
    raise RuntimeError(f"HDF5 library directory not found: {hdf5_dir}")
if not os.path.exists(hdf5_include_dir):
    print(f"Warning: HDF5 include directory not found: {hdf5_include_dir}")
    print("Using main h5py directory for includes.")
    hdf5_include_dir = hdf5_dir

# Common compile and link arguments
compile_args = ["/std:c++17", "/DWIN32", "/D_WINDOWS", "/DH5_BUILT_AS_DYNAMIC_LIB", "/D_CRT_SECURE_NO_WARNINGS"]
link_args = []

# Libraries
libraries = ["hdf5", "hdf5_hl"]  # Use the base HDF5 library names

# Add include and lib directories to compile and link args
compile_args.append(f"/I{hdf5_include_dir}")
link_args.append(f"/LIBPATH:{hdf5_dir}")

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        ["sz_se_detect_win.cpp"],
        include_dirs=[pybind11.get_include(), hdf5_include_dir],
        library_dirs=[hdf5_dir],
        libraries=libraries,
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    ),
]

setup(
    name="sz_se_detect",
    version="0.0.1",
    author="Jake Cahoon",
    author_email="jacobbcahoon@gmail.com",
    description="A module for seizure and status epilepticus detection",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.6",
)
