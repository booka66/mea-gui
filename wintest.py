from dependencies import DependencyScanner
import os

# Set the directory where your sz_se_detect.pyd file is located
module_dir = os.path.dirname(os.path.abspath(__file__))

# Create a DependencyScanner object
scanner = DependencyScanner(module_dir)

# Scan the sz_se_detect.pyd file
dependencies = scanner.scan_file(os.path.join(module_dir, "sz_se_detect.pyd"))

# Print out all dependencies and their status
for dep in dependencies:
    print(f"Dependency: {dep.name}")
    print(f"  Found: {dep.found}")
    if dep.found:
        print(f"  Path: {dep.path}")
    else:
        print(f"  Search paths:")
        for path in dep.search_paths:
            print(f"    {path}")
    print()

# Now try to import the module
try:
    import sz_se_detect

    print("Module imported successfully!")
except ImportError as e:
    print(f"Import failed: {e}")
