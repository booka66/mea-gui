import os
import sys
import ctypes
import platform


def print_dll_search_path():
    print("DLL search path:")
    for path in os.environ.get("PATH", "").split(os.pathsep):
        print(f"  {path}")
    print()


def check_file_exists(filename):
    if os.path.exists(filename):
        print(f"File exists: {filename}")
    else:
        print(f"File does not exist: {filename}")


print_dll_search_path()

module_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(module_dir, "sz_se_detect.cp311-win_amd64.pyd")

check_file_exists(module_path)

print("\nAttempting to load the module:")
try:
    import sz_se_detect

    print("Module imported successfully!")
except ImportError as e:
    print(f"Import failed: {e}")

    # Try to load the DLL directly
    try:
        ctypes.CDLL(module_path)
        print("DLL loaded successfully via ctypes!")
    except Exception as e:
        print(f"DLL load failed: {e}")

    # Check for common dependencies
    common_deps = ["hdf5.dll", "hdf5_cpp.dll", "vcruntime140.dll", "msvcp140.dll"]
    print("\nChecking for common dependencies:")
    for dep in common_deps:
        try:
            ctypes.CDLL(dep)
            print(f"  {dep}: Found")
        except Exception as e:
            print(f"  {dep}: Not found ({e})")

    print("\nAttempting to load HDF5 DLLs explicitly:")
    hdf5_dir = r"D:\Users\booka66\Desktop\HDF5-1.14.4-win64\bin"
    for dll in ["hdf5.dll", "hdf5_cpp.dll"]:
        dll_path = os.path.join(hdf5_dir, dll)
        try:
            ctypes.CDLL(dll_path)
            print(f"  {dll}: Loaded successfully from {dll_path}")
        except Exception as e:
            print(f"  {dll}: Failed to load from {dll_path}")
            print(f"    Error: {e}")

print("\nPython version:", sys.version)
print("Python executable:", sys.executable)
print("System architecture:", platform.architecture()[0])
