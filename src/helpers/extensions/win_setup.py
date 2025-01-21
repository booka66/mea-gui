from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os

# HDF5 paths for CI environment
hdf5_dir = os.path.join(os.environ.get("GITHUB_WORKSPACE", ""), "HDF5-1.14.4-win64")
hdf5_include_dir = os.path.join(hdf5_dir, "include")
hdf5_lib_dir = os.path.join(hdf5_dir, "lib")

# Add HDF5 bin directory to PATH (for dynamic libraries)
os.environ["PATH"] = os.path.join(hdf5_dir, "bin") + os.pathsep + os.environ["PATH"]

# Choose between static and dynamic libraries
use_dynamic = True  # Set to False for static libraries
if use_dynamic:
    compile_args = ["/std:c++17", f"/I{hdf5_include_dir}", "/DH5_BUILT_AS_DYNAMIC_LIB"]
    libraries = ["hdf5_cpp", "hdf5"]
else:
    compile_args = ["/std:c++17", f"/I{hdf5_include_dir}"]
    libraries = ["libhdf5_cpp", "libhdf5"]

link_args = [f"/LIBPATH:{hdf5_lib_dir}"]

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        ["sz_se_detect_win.cpp"],
        include_dirs=[
            pybind11.get_include(),
            hdf5_include_dir,
        ],
        library_dirs=[hdf5_lib_dir],
        libraries=libraries,
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    ),
    Pybind11Extension(
        "signal_analyzer",
        ["signal_analyzer.cpp"],
        include_dirs=[pybind11.get_include()],
        extra_compile_args=["/std=c++17"],
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
