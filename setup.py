from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys

# HDF5 paths
if sys.platform == "darwin":
    hdf5_dir = "/opt/homebrew/Cellar/hdf5/1.14.3_1"
    hdf5_include_dir = os.path.join(hdf5_dir, "include")
    hdf5_lib_dir = os.path.join(hdf5_dir, "lib")
elif sys.platform == "win32":
    hdf5_include_dir = r"D:\Users\booka66\Desktop\HDF5-1.14.4-win64\include"
    hdf5_lib_dir = r"D:\Users\booka66\Desktop\HDF5-1.14.4-win64\lib"
    # Specify the path to Visual Studio libraries
    vs_dir = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.40.33807"
else:
    hdf5_include_dir = ""
    hdf5_lib_dir = ""

# Common compile and link arguments
compile_args = ["-std=c++17"]
link_args = []

# Platform-specific settings
if sys.platform == "win32":
    compile_args = ["/std:c++17", "/EHsc", "/bigobj"]  # MSVC equivalent of -std=c++17
    libraries = ["libhdf5_cpp", "libhdf5", "libcmt"]
    link_args.append("/NODEFAULTLIB:libcmt.lib")
else:
    libraries = ["hdf5_cpp", "hdf5"]

# Add include and lib directories to compile and link args
compile_args.append(f"-I{hdf5_include_dir}")
link_args.append(f"-L{hdf5_lib_dir}")

cpp_file = "sz_se_detect.cpp" if sys.platform == "darwin" else "sz_se_detect_win.cpp"

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        [cpp_file],
        include_dirs=[
            pybind11.get_include(),
            hdf5_include_dir,
        ],
        library_dirs=[
            hdf5_lib_dir,
            os.path.join(vs_dir, "lib", "x64") if sys.platform == "win32" else None,
        ],
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
)
