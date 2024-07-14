from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys


def print_debug(message):
    print(f"DEBUG: {message}")


# HDF5 paths
if sys.platform == "win32":
    hdf5_dir = r"D:\Users\booka66\Desktop\HDF5-1.14.4-win64"
    hdf5_include_dir = os.path.join(hdf5_dir, "include")
    hdf5_lib_dir = os.path.join(hdf5_dir, "lib")
    vs_dir = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.40.33807"
    win_kit_dir = r"C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0"
else:
    raise NotImplementedError("This script is currently set up for Windows only.")

print_debug(f"HDF5 include dir: {hdf5_include_dir}")
print_debug(f"HDF5 lib dir: {hdf5_lib_dir}")

# List all files in the HDF5 lib directory
print_debug("Files in HDF5 lib directory:")
for file in os.listdir(hdf5_lib_dir):
    print_debug(f"  {file}")

# Explicitly specify the libraries
libraries = ["libhdf5_cpp", "libhdf5", "libszip", "libzlib"]

# Compile and link arguments
compile_args = ["/std:c++17", "/EHsc", "/bigobj", f"/I{hdf5_include_dir}"]
link_args = [
    f"/LIBPATH:{hdf5_lib_dir}",
    "/NODEFAULTLIB:libcmt.lib",
    f"/LIBPATH:{os.path.join(vs_dir, 'lib', 'x64')}",
    f"/LIBPATH:{os.path.join(win_kit_dir, 'ucrt', 'x64')}",
    f"/LIBPATH:{os.path.join(win_kit_dir, 'um', 'x64')}",
]

print_debug(f"Compile args: {compile_args}")
print_debug(f"Link args: {link_args}")
print_debug(f"Libraries: {libraries}")

cpp_file = "sz_se_detect_win.cpp"

ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        [cpp_file],
        include_dirs=[pybind11.get_include(), hdf5_include_dir],
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
)
