import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QProgressBar,
    QLabel,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)
from PyQt5.QtCore import QThread, pyqtSignal
import qdarktheme
from NewUpdater import AppUpdater


class UpdateWorker(QThread):
    progress = pyqtSignal(str, int)  # Message, percentage
    finished = pyqtSignal(bool)  # Success status

    def __init__(self, release, install_dir):
        super().__init__()
        self.release = release
        self.install_dir = install_dir
        self.updater = AppUpdater(install_dir=install_dir)

    def run(self):
        try:
            self.progress.emit("Downloading update...", 0)
            update_file = self.updater.download_update(self.release)

            if not update_file:
                self.progress.emit("Download failed.", 100)
                self.finished.emit(False)
                return

            self.progress.emit("Installing update...", 50)
            success = self.updater.install_update(update_file)

            if success:
                self.progress.emit("Installation complete!", 100)
                self.finished.emit(True)
            else:
                self.progress.emit("Installation failed.", 100)
                self.finished.emit(False)

        except Exception as e:
            self.progress.emit(f"Error: {str(e)}", 100)
            self.finished.emit(False)


class UpdaterWindow(QMainWindow):
    def __init__(self, release=None, install_dir=None):
        super().__init__()
        self.release = release
        self.install_dir = install_dir or Path("/Applications/")
        self.init_ui()
        self.start_update()

    def init_ui(self):
        self.setWindowTitle("MEA GUI Updater")
        self.setFixedSize(400, 150)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add status label
        self.status_label = QLabel("Preparing update...")
        layout.addWidget(self.status_label)

        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # Center the window
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

    def start_update(self):
        self.worker = UpdateWorker(self.release, self.install_dir)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.handle_completion)
        self.worker.start()

    def update_progress(self, message, percentage):
        self.status_label.setText(message)
        self.progress_bar.setValue(percentage)

    def handle_completion(self, success):
        if success:
            QMessageBox.information(
                self,
                "Update Complete",
                "The update has been installed successfully. The application will now restart.",
            )
            # Launch the main application
            app_path = self.install_dir / "MEA GUI.app"
            if app_path.exists():
                os.system(f"open '{app_path}'")
        else:
            QMessageBox.critical(
                self,
                "Update Failed",
                "The update process failed. Please try again later.",
            )
        self.close()


def main():
    # Check if we received a release JSON as an argument
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()

    # In a real scenario, you would pass the release info as arguments
    updater = AppUpdater(install_dir=Path("/Applications/"))
    update_available, release = updater.check_for_update()

    if update_available and release:
        window = UpdaterWindow(release=release)
        window.show()
        return app.exec()
    else:
        print("No update available")
        return 0


if __name__ == "__main__":
    sys.exit(main())
