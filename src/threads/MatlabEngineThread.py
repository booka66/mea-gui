from PyQt5.QtCore import QThread, pyqtSignal
import os

try:
    import matlab.engine
except ImportError:
    pass


class MatlabEngineThread(QThread):
    engine_started = pyqtSignal(
        object
    )  # Using object instead of matlab.engine.MatlabEngine for compatibility
    error_occurred = pyqtSignal(str)

    def __init__(self, cwd, matlab_folder_path):
        super().__init__()
        self.cwd = cwd
        self.matlab_folder_path = matlab_folder_path

    def run(self):
        try:
            eng = matlab.engine.start_matlab()
            folder_to_add = self.matlab_folder_path

            # Ensure the MATLAB folder path exists
            if not os.path.exists(self.matlab_folder_path):
                folder_to_add = self.cwd

            eng.addpath(folder_to_add)

            # Check if required .m files exist
            required_files = [
                "SzDetectCat.m",
                "save_channel_to_mat.m",
                "getChs.m",
                "get_cat_envelop.m",
            ]
            for file in required_files:
                if not os.path.exists(os.path.join(folder_to_add, file)):
                    raise FileNotFoundError(f"Required MATLAB file not found: {file}")

            # Start parallel pool
            eng.eval("parpool('Threads')", nargout=0)

            self.engine_started.emit(eng)
        except Exception as e:
            self.error_occurred.emit(str(e))
