from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys
import platform

# Determine the current architecture
current_arch = platform.machine()


# HDF5 path configuration
def get_hdf5_paths():
    if sys.platform == "darwin":
        # Try Homebrew paths for both Intel and Apple Silicon
        homebrew_paths = [
            "/usr/local/Cellar/hdf5",  # Intel Homebrew
            "/opt/homebrew/Cellar/hdf5",  # Apple Silicon Homebrew
        ]

        for path in homebrew_paths:
            if os.path.exists(path):
                versions = sorted(os.listdir(path), reverse=True)
                if versions:
                    hdf5_dir = os.path.join(path, versions[0])
                    return {
                        "include_dir": os.path.join(hdf5_dir, "include"),
                        "lib_dir": os.path.join(hdf5_dir, "lib"),
                    }

    # Fallback for Windows or if Homebrew paths not found
    return {
        "include_dir": os.environ.get("HDF5_INCLUDE_DIR", ""),
        "lib_dir": os.environ.get("HDF5_LIB_DIR", ""),
    }


# Get HDF5 paths
hdf5_paths = get_hdf5_paths()

# Compilation flags
extra_compile_flags = ["-std=c++17", "-O3"]
extra_link_flags = []

# Architecture-specific flags
if sys.platform == "darwin":
    # Check if running under Rosetta 2 (x86_64 on arm64)
    is_rosetta = platform.machine() == "x86_64" and platform.processor() == "i386"

    if current_arch == "x86_64" or is_rosetta:
        extra_compile_flags.extend(["-arch", "x86_64"])
        extra_link_flags.extend(["-arch", "x86_64"])
    elif current_arch == "arm64":
        extra_compile_flags.extend(["-arch", "arm64"])
        extra_link_flags.extend(["-arch", "arm64"])
    else:
        # For universal binaries or other scenarios
        extra_compile_flags.extend(["-arch", "arm64", "-arch", "x86_64"])
        extra_link_flags.extend(["-arch", "arm64", "-arch", "x86_64"])

# Extension modules
ext_modules = [
    Pybind11Extension(
        "sz_se_detect",
        ["sz_se_detect.cpp"],
        include_dirs=[
            pybind11.get_include(),
            hdf5_paths["include_dir"],
        ],
        library_dirs=[hdf5_paths["lib_dir"]],
        libraries=["hdf5_cpp", "hdf5"],
        extra_compile_args=extra_compile_flags + [f"-I{hdf5_paths['include_dir']}"],
        extra_link_args=extra_link_flags + [f"-L{hdf5_paths['lib_dir']}"],
    ),
    Pybind11Extension(
        "signal_analyzer",
        ["signal_analyzer.cpp"],
        include_dirs=[pybind11.get_include()],
        extra_compile_args=extra_compile_flags,
        extra_link_args=extra_link_flags,
    ),
]

setup(
    name="neuro_signal_processing",
    version="0.0.3",
    author="Jake Cahoon",
    author_email="jacobbcahoon@gmail.com",
    description="A module for seizure and status epilepticus detection, and signal analysis",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.10",
)
