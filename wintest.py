import os
import sys
import urllib.request
import subprocess


def download_and_run_file():
    download_url = (
        "https://github.com/booka66/mea-gui/releases/download/v1.0.11/MEA_GUI_MacOS.pkg"
    )
    file_name = (
        "mea_gui_update_parrish_lab_DELETE_ME.pkg"
        if sys.platform == "darwin"
        else "mea_gui_update_parrish_lab_DELETE_ME.exe"
    )
    download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    file_path = os.path.join(download_folder, file_name)

    # Ensure the download folder exists
    os.makedirs(download_folder, exist_ok=True)

    print(f"Downloading {download_url} to {file_path}")

    # Download the file
    try:
        urllib.request.urlretrieve(download_url, file_path)
    except Exception as e:
        print(f"Error downloading file: {e}")
        return

    print("Download completed.")

    # Run the file
    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", file_path], check=True)
        else:
            subprocess.run(["xdg-open", file_path], check=True)
        print(f"Launched {file_path}")
    except Exception as e:
        print(f"Error launching file: {e}")


if __name__ == "__main__":
    download_and_run_file()
