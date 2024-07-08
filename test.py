import os
import sys
import requests
import subprocess
from packaging import version

GITHUB_REPO = "jhnorby/Jake-Squared"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version():
    return "1.0.0-alpha"  # Replace with your version tracking method


def check_for_update():
    current_version = get_current_version()
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        latest_version = response.json()["tag_name"]
        return version.parse(latest_version) > version.parse(current_version)
    return False


def download_update():
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        assets = response.json()["assets"]
        for asset in assets:
            if sys.platform == "darwin" and asset["name"].endswith(".app.zip"):
                download_url = asset["browser_download_url"]
            elif sys.platform == "win32" and asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]

    if download_url:
        r = requests.get(download_url)
        with open("update", "wb") as f:
            f.write(r.content)
        return True
    return False


def apply_update():
    if sys.platform == "darwin":
        subprocess.run(["unzip", "update"])
        os.remove("update")
        os.rename("YourApp.app", "YourApp_old.app")
        os.rename("update.app", "YourApp.app")
        os.remove("YourApp_old.app")
    elif sys.platform == "win32":
        os.rename("YourApp.exe", "YourApp_old.exe")
        os.rename("update", "YourApp.exe")
        os.remove("YourApp_old.exe")


def main():
    if check_for_update():
        print("Update available. Downloading...")
        if download_update():
            print("Update downloaded. Applying...")
            apply_update()
            print("Update applied. Restarting...")
            os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        print("No update available.")


if __name__ == "__main__":
    main()
