from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import platform
import os
import sys
import subprocess


class UpdateThread(QThread):
    update_completed = pyqtSignal(bool)

    def __init__(self, release):
        super().__init__()
        self.release = release

    def run(self):
        try:
            # Create a separate Python process to handle the update
            current_dir = Path.cwd()
            updater_script = (
                current_dir / "src" / "helpers" / "update" / "NewUpdater.py"
            )

            if platform.system() == "Windows":
                # Use pythonw.exe on Windows to avoid console window
                python_exe = os.path.join(sys.prefix, "pythonw.exe")
                subprocess.Popen(
                    [python_exe, str(updater_script)],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # Use regular python on other platforms
                subprocess.Popen([sys.executable, str(updater_script)])

            self.update_completed.emit(True)
        except Exception as e:
            print(f"Failed to start update process: {e}")
            self.update_completed.emit(False)
