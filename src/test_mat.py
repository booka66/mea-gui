import scipy.io
import numpy as np


def print_mat_contents(d, indent=0):
    for key, value in d.items():
        print(" " * indent + str(key) + ": ", end="")
        if isinstance(value, np.ndarray):
            print("Array of shape", value.shape)
            if value.size < 10:  # Print small arrays
                print(value)
        elif isinstance(value, dict):
            print("Dictionary:")
            print_mat_contents(value, indent + 4)
        else:
            print(value)


def main():
    file_path = "/Users/booka66/Downloads/discharges_1490.51_1512.54/all_discharges.mat"  # Replace with your .mat file path
    mat_contents = scipy.io.loadmat(file_path)
    print_mat_contents(mat_contents)


if __name__ == "__main__":
    main()
