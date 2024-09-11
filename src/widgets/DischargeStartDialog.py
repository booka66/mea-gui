from PyQt5.QtWidgets import QDialog, QLabel, QSpinBox, QVBoxLayout


class DischargeStartDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setWindowTitle("Discharge Start Viewer")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout()
        self.setLayout(layout)

        num_bins_label = QLabel("Number of Bins:")
        layout.addWidget(num_bins_label)

        self.num_bins = QSpinBox()
        self.num_bins.setMinimum(1)
        self.num_bins.setMaximum(1000)
        self.num_bins.setValue(10)
        layout.addWidget(self.num_bins)
        self.num_bins.valueChanged.connect(self.update_values)
