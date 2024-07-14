from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys
import h5py
import numpy as np


def print_debug(message):
    print(f"DEBUG: {message}")


# Get HDF5 info from h5py
hdf5_version = h5py.version.hdf5_version
print_debug(f"HDF5 version: {hdf5_version}")

# Try to find HDF5 installation directory
hdf5_dir = None
for path in os.environ.get("PATH", "").split(os.pathsep):
    if os.path.exists(os.path.join(path, "h5cc")) or os.path.exists(
        os.path.join(path, "h5cc.exe")
    ):
        hdf5_dir = os.path.dirname(path)
        break

if not hdf5_dir:
    # If we can't find it in PATH, let's try a common location
    possible_dirs = [
        r"C:\Program Files\HDF_Group\HDF5",
        r"C:\Program Files (x86)\HDF_Group\HDF5",
    ]
    for dir in possible_dirs:
        if os.path.exists(dir):
            hdf5_dir = dir
            break

if not hdf5_dir:
    raise RuntimeError("Could not find HDF5 installation directory")

print_debug(f"HDF5 dir: {hdf5_dir}")

if sys.platform == "win32":
    hdf5_include_dir = os.path.join(hdf5_dir, "include")
    hdf5_lib_dir = os.path.join(hdf5_dir, "lib")
else:
    raise NotImplementedError("This script is currently set up for Windows only.")

print_debug(f"HDF5 include dir: {hdf5_include_dir}")
print_debug(f"HDF5 lib dir: {hdf5_lib_dir}")

# Compile and link arguments
compile_args = ["/std:c++17", "/EHsc", "/bigobj", f"/I{hdf5_include_dir}"]
link_args = [f"/LIBPATH:{hdf5_lib_dir}"]

# Libraries to link against
libraries = ["hdf5_cpp", "hdf5"]

print_debug(f"Compile args: {compile_args}")
print_debug(f"Link args: {link_args}")
print_debug(f"Libraries: {libraries}")

cpp_file = "sz_se_detect_win.cpp"

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        [cpp_file],
        include_dirs=[
            pybind11.get_include(),
            hdf5_include_dir,
            np.get_include(),  # Include NumPy headers
        ],
        library_dirs=[hdf5_lib_dir],
        libraries=libraries,
        extra_compile_args=compile_args,
        extra_link_args=link_args,
        define_macros=[("H5_BUILT_AS_DYNAMIC_LIB", None)],
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
    install_requires=["h5py", "numpy"],
)
