from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys

# HDF5 paths for Homebrew installation
hdf5_dir = "/opt/homebrew/Cellar/hdf5/1.14.4.3" if sys.platform == "darwin" else ""
hdf5_include_dir = os.path.join(hdf5_dir, "include")
hdf5_lib_dir = os.path.join(hdf5_dir, "lib")

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        ["sz_se_detect.cpp"],
        include_dirs=[
            pybind11.get_include(),
            hdf5_include_dir,
        ],
        library_dirs=[hdf5_lib_dir],
        libraries=["hdf5_cpp", "hdf5"],
        extra_compile_args=["-std=c++17", f"-I{hdf5_include_dir}"],
        extra_link_args=[f"-L{hdf5_lib_dir}"],
    ),
    Pybind11Extension(
        "signal_analyzer",
        ["signal_analyzer.cpp"],
        include_dirs=[pybind11.get_include()],
        extra_compile_args=["-std=c++17", "-O3"],
    ),
]

setup(
    name="neuro_signal_processing",
    version="0.0.2",
    author="Jake Cahoon",
    author_email="jacobbcahoon@gmail.com",
    description="A module for seizure and status epilepticus detection, and signal analysis",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.6",
)
