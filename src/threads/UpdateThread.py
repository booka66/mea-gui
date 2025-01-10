from PyQt5.QtCore import QThread, pyqtSignal
from helpers.update.Updater import download_and_install_update


class UpdateThread(QThread):
    update_completed = pyqtSignal(bool)

    def __init__(self, latest_release):
        super().__init__()
        self.latest_release = latest_release

    def run(self):
        success = download_and_install_update(self.latest_release)
        self.update_completed.emit(success)
