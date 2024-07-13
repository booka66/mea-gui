import os
import sys
import requests
from packaging import version

from Constants import VERSION

GITHUB_REPO = "booka66/mea-gui"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def check_for_update():
    try:
        response = requests.get(GITHUB_API_URL)
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release["tag_name"]
            return version.parse(latest_version) > version.parse(
                VERSION
            ), latest_release
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
        if sys.platform == "darwin":
            print("Downloading and installing update...")
            # Download to downloads folder
            download_folder = os.path.expanduser("~/Downloads")
            os.system(f"curl -sL {download_url} -o {download_folder}/update.pkg")
            os.system(f"open {download_folder}/update.pkg")
            print("Update installed successfully.")
            return True
        elif sys.platform == "win32":
            download_folder = os.path.expanduser("~\\Downloads")
            os.system(f"curl -sL {download_url} -o {download_folder}\\update.exe")
            os.system(f"start {download_folder}\\update.exe")
            print("Update installed successfully.")
            return True
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
