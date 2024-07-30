import os
import sys
import requests
from packaging import version
import urllib.request

from helpers.Constants import VERSION

GITHUB_REPO = "booka66/mea-gui"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def check_for_update():
    try:
        file_name = (
            "mea_gui_update_parrish_lab_DELETE_ME.pkg"
            if sys.platform == "darwin"
            else "mea_gui_update_parrish_lab_DELETE_ME.exe"
        )
        if os.path.exists(os.path.expanduser(f"~/Downloads/{file_name}")):
            os.remove(os.path.expanduser(f"~/Downloads/{file_name}"))
        response = requests.get(GITHUB_API_URL)
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release["tag_name"]
            found_new_tag = version.parse(latest_version) > version.parse(VERSION)
            if found_new_tag:
                # Check to see if the update has the required assets for the current platform
                assets = latest_release["assets"]
                for asset in assets:
                    if sys.platform == "darwin" and asset["name"].endswith(".pkg"):
                        return True, latest_release
                    elif sys.platform == "win32" and asset["name"].endswith(".exe"):
                        return True, latest_release
            # return version.parse(latest_version) > version.parse(
            #     VERSION
            # ), latest_release
        return False, None
    except Exception as e:
        print(f"Failed to check for updates: {e}")
        return False, None


def download_and_install_update(release):
    assets = release["assets"]
    download_url = None
    for asset in assets:
        if sys.platform == "darwin" and asset["name"].endswith(".pkg"):
            download_url = asset["browser_download_url"]
            break
        elif sys.platform == "win32" and asset["name"].endswith(".exe"):
            download_url = asset["browser_download_url"]
            break

    if download_url:
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

        try:
            if sys.platform == "win32":
                os.startfile(file_path)
                return True
            elif sys.platform == "darwin":
                os.system(f"open {file_path}")
                return True
            print(f"Launched {file_path}")
        except Exception as e:
            print(f"Error launching file: {e}")
    else:
        print("No suitable update found for your platform.")
        return False


def main():
    update_available, latest_release = check_for_update()
    if update_available:
        print("Update available. Downloading and installing...")
        if download_and_install_update(latest_release):
            print("Update process completed.")
        else:
            print("Update process failed.")
    else:
        print("No update available.")


if __name__ == "__main__":
    main()
