from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11
import os
import sys
import subprocess


def get_hdf5_paths():
    """
    Dynamically find HDF5 installation paths using brew.
    Falls back to environment variables or common paths if brew fails.
    """
    try:
        hdf5_dir = (
            subprocess.check_output(["brew", "--prefix", "hdf5"]).decode().strip()
        )
        return {
            "include_dir": os.path.join(hdf5_dir, "include"),
            "lib_dir": os.path.join(hdf5_dir, "lib"),
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback paths
        fallback_paths = {
            "darwin": {
                "include_dir": [
                    "/opt/homebrew/include/hdf5",
                    "/usr/local/include/hdf5",
                    "/usr/include/hdf5",
                ],
                "lib_dir": ["/opt/homebrew/lib", "/usr/local/lib", "/usr/lib"],
            },
            "linux": {
                "include_dir": [
                    "/usr/include/hdf5/serial",
                    "/usr/local/include/hdf5",
                    "/usr/include/hdf5",
                ],
                "lib_dir": ["/usr/lib/x86_64-linux-gnu", "/usr/local/lib", "/usr/lib"],
            },
        }

    # Detect platform-specific paths
    platform_paths = fallback_paths.get(sys.platform, fallback_paths["linux"])

    # Find first existing include directory
    include_dir = next(
        (path for path in platform_paths["include_dir"] if os.path.exists(path)), None
    )
    lib_dir = next(
        (path for path in platform_paths["lib_dir"] if os.path.exists(path)), None
    )

    if not include_dir or not lib_dir:
        raise RuntimeError("Could not find HDF5 installation paths")

    return {"include_dir": include_dir, "lib_dir": lib_dir}


# Determine compilation flags based on platform
extra_compile_flags = ["-std=c++17", "-O3"]
extra_link_flags = []

# Universal binary for macOS
if sys.platform == "darwin":
    extra_compile_flags.extend(["-arch", "arm64", "-arch", "x86_64"])
    extra_link_flags.extend(["-arch", "arm64", "-arch", "x86_64"])

# Get HDF5 paths
hdf5_paths = get_hdf5_paths()

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
    python_requires=">=3.6",
)
