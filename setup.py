from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os

# HDF5 paths for Homebrew installation
hdf5_dir = "/opt/homebrew/Cellar/hdf5/1.14.3_1"
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
