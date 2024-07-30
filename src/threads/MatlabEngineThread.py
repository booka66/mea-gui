from PyQt5.QtCore import QThread, pyqtSignal
import os
import importlib

class MatlabEngineThread(QThread):
    engine_started = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, cwd, matlab_folder_path):
        super().__init__()
        self.cwd = cwd
        self.matlab_folder_path = matlab_folder_path
        self.matlab_engine_available = False

    def _check_matlab_engine_availability(self):
        try:
            importlib.import_module('matlab.engine')
            return True
        except ImportError:
            return False

    def run(self):
        self.matlab_engine_available = self._check_matlab_engine_availability()
        print(self.matlab_engine_available)
        
        if not self.matlab_engine_available or self.matlab_engine_available is None:
            self.error_occurred.emit("MATLAB engine is not available. Please ensure MATLAB and matlab.engine are properly installed.")
            return

        try:
            import matlab.engine
            eng = matlab.engine.start_matlab()
            folder_to_add = self.matlab_folder_path if os.path.exists(self.matlab_folder_path) else self.cwd
            eng.addpath(folder_to_add)

            required_files = [
                "SzDetectCat.m",
                "save_channel_to_mat.m",
                "getChs.m",
                "get_cat_envelop.m",
            ]
            for file in required_files:
                if not os.path.exists(os.path.join(folder_to_add, file)):
                    raise FileNotFoundError(f"Required MATLAB file not found: {file}")

            eng.eval("parpool('Threads')", nargout=0)
            self.engine_started.emit(eng)
        except Exception as e:
            self.error_occurred.emit(str(e))
