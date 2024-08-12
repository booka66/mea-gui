from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
from PyQt5.QtCore import Qt


class SettingsWidgetManager:
    def __init__(self, parent_menu: QMenu):
        self.parent_menu = parent_menu
        self.submenus = {}

    def add_widget(self, action_text: str, widget: QWidget, separator: bool = True):
        submenu = QMenu(action_text, self.parent_menu)
        widget_action = QWidgetAction(submenu)
        widget_action.setDefaultWidget(widget)
        submenu.addAction(widget_action)

        self.parent_menu.addMenu(submenu)
        if separator:
            self.parent_menu.addSeparator()

        self.submenus[action_text] = submenu


class PeakSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setLayout(QVBoxLayout())

        # Peak threshold (n_std_dev) slider
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Peak Threshold (std dev):")
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(1, 20)  # Range 1 to 10
        self.threshold_slider.setValue(int(parent.n_std_dev))
        self.threshold_value = QLineEdit(str(parent.n_std_dev))
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value)
        self.layout().addLayout(threshold_layout)

        # Distance slider
        distance_layout = QHBoxLayout()
        distance_label = QLabel("Min Distance Between Peaks:")
        self.distance_slider = QSlider(Qt.Horizontal)
        self.distance_slider.setRange(1, 100)  # Range 1 to 100
        self.distance_slider.setValue(parent.distance)
        self.distance_value = QLineEdit(str(parent.distance))
        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(self.distance_slider)
        distance_layout.addWidget(self.distance_value)
        self.layout().addLayout(distance_layout)

        # SNR threshold slider
        snr_layout = QHBoxLayout()
        snr_label = QLabel("SNR Threshold:")
        self.snr_slider = QSlider(Qt.Horizontal)
        self.snr_slider.setRange(1, 100)  # Range 1 to 10
        self.snr_slider.setValue(parent.snr_threshold)
        self.snr_value = QLineEdit(str(parent.snr_threshold))
        snr_layout.addWidget(snr_label)
        snr_layout.addWidget(self.snr_slider)
        snr_layout.addWidget(self.snr_value)
        self.layout().addLayout(snr_layout)

        # Connect sliders to update functions
        self.threshold_slider.valueChanged.connect(self.update_threshold_from_slider)
        self.distance_slider.valueChanged.connect(self.update_distance_from_slider)
        self.snr_slider.valueChanged.connect(self.update_snr_from_slider)

        # Connect line edits to update functions
        self.threshold_value.editingFinished.connect(self.update_threshold_from_text)
        self.distance_value.editingFinished.connect(self.update_distance_from_text)
        self.snr_value.editingFinished.connect(self.update_snr_from_text)

    def update_snr_from_slider(self, value):
        self.snr_value.setText(str(value))
        self.parent.snr_threshold = value
        self.parent.signal_analyzer.snr_threshold = value
        self.parent.graph_widget.plot_peaks()

    def update_snr_from_text(self):
        try:
            snr_threshold = int(self.snr_value.text())
            if 1 <= snr_threshold <= 100:
                self.snr_slider.setValue(snr_threshold)
                self.parent.snr_threshold = snr_threshold
                self.parent.signal_analyzer.snr_threshold = snr_threshold
                self.parent.graph_widget.plot_peaks()
            else:
                raise ValueError("SNR threshold must be between 1 and 10.")
        except ValueError:
            pass

    def update_threshold_from_slider(self, value):
        self.threshold_value.setText(str(value))
        self.parent.n_std_dev = value
        self.parent.signal_analyzer.n_std_dev = value
        self.parent.graph_widget.plot_peaks()

    def update_threshold_from_text(self):
        try:
            threshold = int(self.threshold_value.text())
            if 1 <= threshold <= 20:
                self.threshold_slider.setValue(threshold)
                self.parent.n_std_dev = threshold
                self.parent.signal_analyzer.n_std_dev = threshold
                self.parent.graph_widget.plot_peaks()
            else:
                raise ValueError("Threshold must be between 1 and 10.")
        except ValueError:
            pass

    def update_distance_from_slider(self, value):
        self.distance_value.setText(str(value))
        self.parent.distance = value
        if self.parent.signal_analyzer is not None:
            self.parent.signal_analyzer.distance = value
            self.parent.graph_widget.plot_peaks()

    def update_distance_from_text(self):
        try:
            distance = int(self.distance_value.text())
            if 1 <= distance <= 100:
                self.distance_slider.setValue(distance)
                self.parent.distance = distance
                self.parent.signal_analyzer.distance = distance
                self.parent.graph_widget.plot_peaks()
            else:
                raise ValueError("Distance must be between 1 and 100.")
        except ValueError:
            pass


class DBSCANSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setLayout(QVBoxLayout())

        # Epsilon slider
        eps_layout = QHBoxLayout()
        eps_label = QLabel("Epsilon:")
        self.eps_slider = QSlider(Qt.Horizontal)
        self.eps_slider.setRange(0, 100)  # Range 0 to 10, with 0.1 precision
        self.eps_slider.setValue(int(parent.eps * 10))
        self.eps_value = QLineEdit(f"{parent.eps:.1f}")
        eps_layout.addWidget(eps_label)
        eps_layout.addWidget(self.eps_slider)
        eps_layout.addWidget(self.eps_value)
        self.layout().addLayout(eps_layout)

        # Min Samples input
        min_samples_layout = QHBoxLayout()
        min_samples_label = QLabel("Min Samples:")
        self.min_samples_input = QLineEdit(str(parent.min_samples))
        min_samples_layout.addWidget(min_samples_label)
        min_samples_layout.addWidget(self.min_samples_input)
        self.layout().addLayout(min_samples_layout)

        # Max Distance slider (replacing Step Size)
        max_distance_layout = QHBoxLayout()
        max_distance_label = QLabel("Max Distance:")
        self.max_distance_slider = QSlider(Qt.Horizontal)
        self.max_distance_slider.setRange(1, 64)  # Range 1 to 64
        if hasattr(parent, "cluster_tracker"):
            self.max_distance_slider.setValue(int(parent.cluster_tracker.max_distance))
            self.max_distance_value = QLineEdit(
                str(parent.cluster_tracker.max_distance)
            )
        else:
            self.max_distance_slider.setValue(20)
            self.max_distance_value = QLineEdit("20")
        max_distance_layout.addWidget(max_distance_label)
        max_distance_layout.addWidget(self.max_distance_slider)
        max_distance_layout.addWidget(self.max_distance_value)
        self.layout().addLayout(max_distance_layout)

        # Bin size slider
        bin_size_layout = QHBoxLayout()
        bin_size_label = QLabel("Bin Size:")
        self.bin_size_slider = QSlider(Qt.Horizontal)

        # Set the range and scale factor
        self.scale_factor = 10000  # This gives us 0.0001 precision
        self.set_bin_size_range(0.001, 0.5)

        self.bin_size_slider.setValue(int(parent.bin_size * self.scale_factor))
        self.bin_size_value = QLineEdit(f"{parent.bin_size:.4f}")
        bin_size_layout.addWidget(bin_size_label)
        bin_size_layout.addWidget(self.bin_size_slider)
        bin_size_layout.addWidget(self.bin_size_value)
        self.layout().addLayout(bin_size_layout)

        # Connect sliders to update functions
        self.eps_slider.valueChanged.connect(self.update_eps_from_slider)
        self.max_distance_slider.valueChanged.connect(
            self.update_max_distance_from_slider
        )
        self.bin_size_slider.valueChanged.connect(self.update_bin_size_from_slider)

        # Connect line edits to update functions
        self.eps_value.editingFinished.connect(self.update_eps_from_text)
        self.max_distance_value.editingFinished.connect(
            self.update_max_distance_from_text
        )
        self.min_samples_input.editingFinished.connect(self.update_min_samples)
        self.bin_size_value.editingFinished.connect(self.update_bin_size_from_text)

    def set_bin_size_range(self, min_value, max_value):
        if self.parent.sampling_rate is not None:
            min_value = int((1 / self.parent.sampling_rate) * self.scale_factor)
            max_value = int(0.5 * self.scale_factor)
        else:
            min_value = int(0.01 * self.scale_factor)
            max_value = int(0.5 * self.scale_factor)
        self.bin_size_slider.setRange(min_value, max_value)

    def update_eps_from_slider(self, value):
        eps = value / 10
        self.eps_value.setText(f"{eps:.1f}")
        self.parent.eps = eps
        self.parent.update_grid()

    def update_eps_from_text(self):
        try:
            eps = float(self.eps_value.text())
            self.eps_slider.setValue(int(eps * 10))
            self.parent.eps = eps
            self.parent.update_grid()
        except ValueError:
            pass

    def update_max_distance_from_slider(self, value):
        self.max_distance_value.setText(str(value))
        self.parent.cluster_tracker.max_distance = value
        self.parent.update_grid()

    def update_max_distance_from_text(self):
        try:
            max_distance = int(self.max_distance_value.text())
            if 1 <= max_distance <= 64:
                self.max_distance_slider.setValue(max_distance)
                self.parent.cluster_tracker.max_distance = max_distance
                self.parent.update_grid()
            else:
                raise ValueError("Max distance must be between 1 and 64.")
        except ValueError:
            pass

    def update_min_samples(self):
        try:
            min_samples = int(self.min_samples_input.text())
            if min_samples < 1:
                raise ValueError("Min samples must be greater than 0.")
            self.parent.min_samples = min_samples
            self.parent.update_grid()
        except ValueError:
            pass

    def update_bin_size_from_slider(self, value):
        bin_size = value / self.scale_factor
        self.bin_size_value.setText(f"{bin_size:.4f}")
        self.parent.bin_size = bin_size
        self.parent.update_grid()

    def update_bin_size_from_text(self):
        try:
            bin_size = float(self.bin_size_value.text())
            self.bin_size_slider.setValue(int(bin_size * self.scale_factor))
            self.parent.bin_size = bin_size
            self.parent.update_grid()
        except ValueError:
            pass


class SpectrogramSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowFlags(Qt.Popup)
        self.setLayout(QVBoxLayout())

        chunk_layout = QHBoxLayout()
        chunk_label = QLabel("Chunk Size:")
        chunk_input = QLineEdit(str(parent.chunk_size))
        chunk_layout.addWidget(chunk_label)
        chunk_layout.addWidget(chunk_input)
        self.layout().addLayout(chunk_layout)

        overlap_layout = QHBoxLayout()
        overlap_label = QLabel("Overlap:")
        overlap_input = QLineEdit(str(parent.overlap))
        overlap_layout.addWidget(overlap_label)
        overlap_layout.addWidget(overlap_input)
        self.layout().addLayout(overlap_layout)

        fs_range_layout = QHBoxLayout()
        fs_range_label = QLabel("Frequency Range:")
        fs_min_label = QLabel("Min:")
        fs_min_input = QLineEdit(str(parent.fs_range[0]))
        fs_max_label = QLabel("Max:")
        fs_max_input = QLineEdit(str(parent.sampling_rate / 2))
        fs_range_layout.addWidget(fs_range_label)
        fs_range_layout.addWidget(fs_min_label)
        fs_range_layout.addWidget(fs_min_input)
        fs_range_layout.addWidget(fs_max_label)
        fs_range_layout.addWidget(fs_max_input)
        self.layout().addLayout(fs_range_layout)

        # Add the Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        self.layout().addWidget(apply_button)

    def apply_settings(self):
        # Update the spectrogram settings in the main window
        self.main_window.chunk_size = int(
            self.layout().itemAt(0).layout().itemAt(1).widget().text()
        )
        self.main_window.overlap = int(
            self.layout().itemAt(1).layout().itemAt(1).widget().text()
        )
        self.main_window.fs_range = (
            float(self.layout().itemAt(2).layout().itemAt(2).widget().text()),
            float(self.layout().itemAt(2).layout().itemAt(4).widget().text()),
        )

        # Update the spectrograms
        self.main_window.hide_spectrograms()
        self.main_window.show_spectrograms()
