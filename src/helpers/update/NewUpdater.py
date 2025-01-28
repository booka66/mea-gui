import os
import stat
import sys
import platform
import requests
import subprocess
import shutil
from pathlib import Path
from packaging import version

VERSION = "v0.0.0"
GITHUB_REPO = "booka66/mea-gui"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class AppUpdater:
    def __init__(self, install_dir=None):
        self.is_frozen = getattr(sys, "frozen", False)
        # Use provided install_dir, or default to appropriate location
        if install_dir:
            self.app_path = Path(install_dir)
        else:
            self.app_path = (
                Path(sys._MEIPASS)
                if self.is_frozen
                else Path(os.path.dirname(os.path.abspath(__file__)))
            )

        self.system = platform.system()
        self.machine = platform.machine()
        self.temp_dir = Path(os.path.expanduser("~")) / ".app_updates"

    def _remove_readonly(self, func, path, _):
        """Clear the readonly bit and reattempt the removal"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def _clean_directory(self, path):
        """Safely remove a directory and its contents if it exists."""
        try:
            path = Path(path)
            if path.exists():
                # First try to fix permissions
                for root, dirs, files in os.walk(str(path)):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), stat.S_IRWXU)
                        except:
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), stat.S_IRWXU)
                        except:
                            pass

                # Then remove the directory
                shutil.rmtree(path, onerror=self._remove_readonly)

            # Create new directory with proper permissions
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, stat.S_IRWXU)  # 700 permissions

        except Exception as e:
            print(f"Failed to clean directory {path}: {e}")
            raise

    def check_for_update(self):
        try:
            response = requests.get(GITHUB_API_URL)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"].lstrip("v")
                current_version = VERSION.lstrip("v")

                # Consider no local installation as needing an update
                if not self._is_app_installed():
                    return True, latest_release

                return version.parse(latest_version) > version.parse(
                    current_version
                ), latest_release
            return False, None
        except Exception as e:
            print(f"Update check failed: {e}")
            return False, None

    def _is_app_installed(self):
        """Check if the application is installed in the target directory"""
        if self.system == "Darwin":
            return (self.app_path / "MEA GUI.app").exists()
        else:
            return (self.app_path / "MEA_GUI.exe").exists()

    def _get_download_url(self, assets):
        if self.system == "Darwin":
            arch_suffix = "arm64" if self.machine == "arm64" else "x86_64"
            asset_name = f"MEA_GUI_MacOS_{arch_suffix}.pkg"
        else:
            asset_name = "MEA_GUI_Windows.exe"

        for asset in assets:
            if asset["name"] == asset_name:
                return asset["browser_download_url"]
        return None

    def download_update(self, release):
        try:
            # Clean temp directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, onerror=self._remove_readonly)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.temp_dir, stat.S_IRWXU)

            download_url = self._get_download_url(release["assets"])
            if not download_url:
                raise Exception("No suitable update found for your platform")

            ext = ".pkg" if self.system == "Darwin" else ".exe"
            update_file = self.temp_dir / f"update{ext}"

            print(f"Downloading from {download_url}...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            block_size = 8192
            downloaded = 0

            with open(update_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(100 * downloaded / total_size)
                        print(f"Download progress: {percent}%", end="\r")

            print("\nDownload complete!")
            # Ensure the downloaded file has proper permissions
            os.chmod(update_file, stat.S_IRWXU)

            return update_file

        except Exception as e:
            print(f"Download failed: {e}")
            return None

    def _update_macos(self, pkg_file):
        try:
            app_location = self.app_path
            extract_dir = self.temp_dir / "pkg_contents"
            payload_dir = self.temp_dir / "payload_contents"

            # Ensure directories are clean and have proper permissions
            for directory in [extract_dir, payload_dir]:
                if directory.exists():
                    shutil.rmtree(directory, onerror=self._remove_readonly)
                directory.mkdir(parents=True, exist_ok=True)
                os.chmod(directory, stat.S_IRWXU)

            print("Extracting package contents...")

            # Use xar to extract the package (more reliable than pkgutil on macOS)
            result = subprocess.run(
                ["xar", "-xf", str(pkg_file), "-C", str(extract_dir)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Fallback to pkgutil if xar fails
                result = subprocess.run(
                    ["pkgutil", "--expand", str(pkg_file), str(extract_dir)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise Exception(f"Failed to extract package: {result.stderr}")

            # Find the Payload file
            payload = None
            for file in extract_dir.rglob("Payload"):
                payload = file
                break

            if not payload:
                raise Exception("Payload not found in package")

            print("Extracting payload...")
            result = subprocess.run(
                ["tar", "-xf", str(payload), "-C", str(payload_dir)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(f"Failed to extract payload: {result.stderr}")

            # Look for the .app bundle
            app_bundle = None
            for path in payload_dir.rglob("*.app"):
                app_bundle = path
                break

            if not app_bundle:
                raise Exception("Application bundle not found in extracted contents")

            print(f"Installing application to: {app_location}")

            # If the app exists, try to remove it
            target_app = app_location / app_bundle.name
            if target_app.exists():
                print("Removing existing application...")
                try:
                    shutil.rmtree(target_app, onerror=self._remove_readonly)
                except PermissionError:
                    raise Exception(
                        "Cannot update while application is running. Please close the application and try again."
                    )

            print("Installing new version...")
            shutil.copytree(app_bundle, target_app, symlinks=True)

            # Ensure proper permissions on the new installation
            for root, dirs, files in os.walk(str(target_app)):
                for d in dirs:
                    os.chmod(os.path.join(root, d), stat.S_IRWXU)
                for f in files:
                    os.chmod(os.path.join(root, f), stat.S_IRWXU)

            return True

        except Exception as e:
            print(f"MacOS update failed: {e}")
            return False
        finally:
            # Cleanup
            try:
                for directory in [extract_dir, payload_dir]:
                    if directory.exists():
                        shutil.rmtree(directory, onerror=self._remove_readonly)
            except Exception as e:
                print(f"Cleanup failed: {e}")

    def _update_windows(self, exe_file):
        try:
            app_location = self.app_path
            extract_dir = self.temp_dir / "installer_contents"

            # Clean and recreate extraction directory
            self._clean_directory(extract_dir)

            # Use 7zip to extract the installer
            result = subprocess.run(
                ["7z", "x", str(exe_file), f"-o{extract_dir}", "-y"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise Exception(f"Failed to extract installer: {result.stderr}")

            # Copy the updated contents
            app_dir = extract_dir / "app"
            if not app_dir.exists():
                raise Exception("Application directory not found in extracted contents")

            print(f"Installing application to: {app_location}")

            # Create the app location directory if it doesn't exist
            app_location.mkdir(parents=True, exist_ok=True)

            # Copy contents
            for item in app_dir.iterdir():
                dest = app_location / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                else:
                    if dest.exists():
                        shutil.rmtree(dest, onerror=self._remove_readonly)
                    shutil.copytree(item, dest, symlinks=True)

            return True

        except Exception as e:
            print(f"Windows update failed: {e}")
            return False
        finally:
            try:
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, onerror=self._remove_readonly)
            except Exception as e:
                print(f"Cleanup failed: {e}")

    def install_update(self, update_file):
        try:
            if self.system == "Darwin":
                success = self._update_macos(update_file)
            else:
                success = self._update_windows(update_file)

            if success:
                # Clean up temp directory
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir, onerror=self._remove_readonly)

            return success

        except Exception as e:
            print(f"Installation failed: {e}")
            return False


def main():
    # When run directly, install/update in the current directory
    current_dir = Path.cwd()
    updater = AppUpdater(install_dir=current_dir)

    print("Checking for updates...")
    update_available, release = updater.check_for_update()

    if update_available:
        if updater._is_app_installed():
            print("Update available. Downloading...")
        else:
            print("Application not found. Downloading...")

        update_file = updater.download_update(release)

        if update_file:
            print("Installing...")
            if updater.install_update(update_file):
                print("Installation successful!")
                sys.exit(0)
            else:
                print("Installation failed.")
                sys.exit(1)
        else:
            print("Download failed.")
            sys.exit(1)
    else:
        print("No update available.")
        sys.exit(0)


if __name__ == "__main__":
    main()
