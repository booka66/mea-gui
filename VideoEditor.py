import math
from time import perf_counter
from alert import alert
import numpy as np
import cv2
from PyQt5.QtCore import QEvent, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class VideoTrimmer(QWidget):
    rangeChanged = pyqtSignal(int, float, float)
    timeChanged = pyqtSignal(float)
    segmentSelected = pyqtSignal(int)

    def __init__(self, duration, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.segments = [(0, duration)]
        self.current_pos = 0
        self.dragging = None
        self.dragging_segment = None
        self.zoom_level = 1.0
        self.offset = 0
        self.setFixedHeight(70)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.panning = False
        self.last_mouse_pos = None
        self.hover_handle = None
        self.selected_segment = 0
        self.markers = []

    def set_markers(self, markers):
        self.markers = markers
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        height = self.height()

        visible_duration = self.duration / self.zoom_level
        start_time = self.offset
        end_time = start_time + visible_duration

        # Draw background
        painter.fillRect(0, 0, width, height, QColor(200, 200, 200))

        # Draw time markers
        painter.setPen(QPen(Qt.black))
        marker_interval = self.get_marker_interval()
        first_marker = math.ceil(start_time / marker_interval) * marker_interval
        current_marker = first_marker
        while current_marker <= end_time:
            x = int((current_marker - start_time) / visible_duration * width)
            painter.drawLine(x, 0, x, height)
            time_str = f"{current_marker:.2f}"
            painter.drawText(x + 2, height - 2, time_str)
            current_marker += marker_interval

        # Draw segments
        for i, (start, end) in enumerate(self.segments):
            start_x = int(
                (max(start, start_time) - start_time) / visible_duration * width
            )
            end_x = int((min(end, end_time) - start_time) / visible_duration * width)
            color = (
                QColor(100, 100, 255, 128)
                if i == self.selected_segment
                else QColor(150, 150, 255, 128)
            )
            painter.fillRect(start_x, 0, end_x - start_x, height, color)

            # Draw handles
            handle_color = (
                QColor(50, 50, 255)
                if self.hover_handle != f"start_{i}"
                else QColor(100, 100, 255)
            )
            painter.setBrush(QBrush(handle_color))
            painter.setPen(QPen(Qt.NoPen))
            painter.drawRect(start_x - 5, 0, 10, height)

            handle_color = (
                QColor(50, 50, 255)
                if self.hover_handle != f"end_{i}"
                else QColor(100, 100, 255)
            )
            painter.setBrush(QBrush(handle_color))
            painter.drawRect(end_x - 5, 0, 10, height)

        # Draw current position
        if start_time <= self.current_pos <= end_time:
            current_x = int((self.current_pos - start_time) / visible_duration * width)
            painter.setPen(QPen(Qt.red, 2))
            painter.drawLine(current_x, 0, current_x, height)

        # Draw markers
        painter.setPen(QPen(Qt.green, 2))
        for marker_time in self.markers:
            if start_time <= marker_time <= end_time:
                x = int((marker_time - start_time) / visible_duration * width)
                painter.drawLine(x, 0, x, height)

    def get_marker_interval(self):
        visible_duration = self.duration / self.zoom_level
        if visible_duration > 100:
            return 10
        elif visible_duration > 50:
            return 5
        elif visible_duration > 10:
            return 1
        elif visible_duration > 5:
            return 0.5
        elif visible_duration > 1:
            return 0.1
        else:
            return 0.05

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ShiftModifier:
                self.panning = True
                self.last_mouse_pos = event.pos()
            else:
                x = event.pos().x()
                width = self.width()
                visible_duration = self.duration / self.zoom_level
                start_time = self.offset

                time_at_click = start_time + (x / width) * visible_duration

                for i, (start, end) in enumerate(self.segments):
                    start_x = int((start - start_time) / visible_duration * width)
                    end_x = int((end - start_time) / visible_duration * width)

                    if abs(x - start_x) < 10:
                        self.dragging = f"start_{i}"
                        self.dragging_segment = i
                        break
                    elif abs(x - end_x) < 10:
                        self.dragging = f"end_{i}"
                        self.dragging_segment = i
                        break
                    elif start_x <= x <= end_x:
                        self.selected_segment = i
                        self.segmentSelected.emit(i)
                        self.update()
                        break
                else:
                    self.dragging = "current"
                    self.current_pos = time_at_click
                    self.timeChanged.emit(self.current_pos)

    def mouseMoveEvent(self, event: QMouseEvent):
        x = event.pos().x()
        width = self.width()
        visible_duration = self.duration / self.zoom_level
        start_time = self.offset

        self.hover_handle = None
        for i, (start, end) in enumerate(self.segments):
            start_x = int((start - start_time) / visible_duration * width)
            end_x = int((end - start_time) / visible_duration * width)

            if abs(x - start_x) < 10:
                self.hover_handle = f"start_{i}"
                break
            elif abs(x - end_x) < 10:
                self.hover_handle = f"end_{i}"
                break

        self.update()

        if self.panning and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.offset -= delta.x() / self.width() * (self.duration / self.zoom_level)
            self.offset = max(
                0, min(self.offset, self.duration - self.duration / self.zoom_level)
            )
            self.last_mouse_pos = event.pos()
            self.update()
        elif self.dragging:
            new_pos = start_time + (x / width) * visible_duration
            new_pos = max(0, min(self.duration, new_pos))

            if self.dragging.startswith("start"):
                self.segments[self.dragging_segment] = (
                    new_pos,
                    self.segments[self.dragging_segment][1],
                )
            elif self.dragging.startswith("end"):
                self.segments[self.dragging_segment] = (
                    self.segments[self.dragging_segment][0],
                    new_pos,
                )
            else:  # 'current'
                self.current_pos = new_pos

            self.update()
            if self.dragging.startswith("start") or self.dragging.startswith("end"):
                self.rangeChanged.emit(
                    self.dragging_segment, *self.segments[self.dragging_segment]
                )
            else:
                self.timeChanged.emit(self.current_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = None
        self.dragging_segment = None
        self.panning = False
        self.last_mouse_pos = None

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        mouse_x = event.pos().x()
        visible_duration = self.duration / self.zoom_level
        time_at_mouse = self.offset + (mouse_x / self.width()) * visible_duration
        self.zoom_level *= zoom_factor
        self.zoom_level = max(1, min(self.zoom_level, self.duration * 1000))
        new_visible_duration = self.duration / self.zoom_level
        self.offset = time_at_mouse - (mouse_x / self.width()) * new_visible_duration
        self.offset = max(0, min(self.offset, self.duration - new_visible_duration))
        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        if self.parent() and hasattr(self.parent(), "main_window"):
            sampling_rate = self.parent().main_window.sampling_rate
            frame_duration = 1 / sampling_rate
        else:
            frame_duration = 1 / 30

        if event.key() == Qt.Key_Left:
            self.current_pos = max(0, self.current_pos - frame_duration)
        elif event.key() == Qt.Key_Right:
            self.current_pos = min(self.duration, self.current_pos + frame_duration)
        elif event.key() == Qt.Key_BracketLeft:
            self.snap_start_to_current()
        elif event.key() == Qt.Key_BracketRight:
            self.snap_end_to_current()
        elif event.key() == Qt.Key_N:
            self.add_segment(self.current_pos)
        else:
            super().keyPressEvent(event)

        self.timeChanged.emit(self.current_pos)
        self.update()

    def snap_start_to_current(self):
        self.segments[self.selected_segment] = (
            self.current_pos,
            self.segments[self.selected_segment][1],
        )
        self.rangeChanged.emit(
            self.selected_segment, *self.segments[self.selected_segment]
        )
        self.update()

    def snap_end_to_current(self):
        self.segments[self.selected_segment] = (
            self.segments[self.selected_segment][0],
            self.current_pos,
        )
        self.rangeChanged.emit(
            self.selected_segment, *self.segments[self.selected_segment]
        )
        self.update()

    def leaveEvent(self, event):
        self.hover_handle = None
        self.update()

    def add_segment(self, time):
        for i, (start, end) in enumerate(self.segments):
            if start <= time < end:
                self.segments[i] = (start, time)
                self.segments.insert(i + 1, (time, end))
                self.selected_segment = i + 1
                self.segmentSelected.emit(self.selected_segment)
                break
        self.update()


class VideoEditor(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.markers = []
        self.setWindowTitle("Video Editor")
        self.showMaximized()

        self.frame_cache = {}

        self.layout = QVBoxLayout()

        # Preview area
        self.preview_view = QGraphicsView()
        self.preview_scene = QGraphicsScene()
        self.preview_view.setScene(self.preview_scene)
        self.preview_item = QGraphicsPixmapItem()
        self.preview_scene.addItem(self.preview_item)
        self.layout.addWidget(self.preview_view)

        # Custom trimmer
        self.trimmer = VideoTrimmer(self.main_window.recording_length)
        self.trimmer.rangeChanged.connect(self.update_range)
        self.trimmer.timeChanged.connect(self.update_current_time)
        self.trimmer.segmentSelected.connect(self.update_selected_segment)
        self.layout.addWidget(self.trimmer)

        # Time labels
        self.time_layout = QHBoxLayout()
        self.start_time_label = QLabel("Start: 0.000s")
        self.current_time_label = QLabel("Current: 0.000s")
        self.end_time_label = QLabel(f"End: {self.main_window.recording_length:.3f}s")
        self.time_layout.addWidget(self.start_time_label)
        self.time_layout.addWidget(self.current_time_label)
        self.time_layout.addWidget(self.end_time_label)
        self.layout.addLayout(self.time_layout)

        # Settings
        self.settings_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS:")
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 240)
        self.fps_spin.setValue(30)
        self.settings_layout.addWidget(self.fps_label)
        self.settings_layout.addWidget(self.fps_spin)
        self.layout.addLayout(self.settings_layout)

        # Snap buttons
        self.snap_layout = QHBoxLayout()
        self.snap_start_button = QPushButton("Snap Start to Current")
        self.snap_start_button.clicked.connect(self.trimmer.snap_start_to_current)
        self.snap_end_button = QPushButton("Snap End to Current")
        self.snap_end_button.clicked.connect(self.trimmer.snap_end_to_current)
        self.snap_layout.addWidget(self.snap_start_button)
        self.snap_layout.addWidget(self.snap_end_button)
        self.layout.addLayout(self.snap_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_video)
        self.export_button.setDefault(True)
        self.add_segment_button = QPushButton("Add Segment")
        self.add_segment_button.clicked.connect(self.add_segment)
        self.button_layout.addWidget(self.play_button)
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addWidget(self.add_segment_button)
        self.layout.addLayout(self.button_layout)

        self.segment_list = QListWidget()
        self.segment_list.itemClicked.connect(self.select_segment_from_list)
        self.layout.addWidget(self.segment_list)
        self.update_segment_list()

        self.setLayout(self.layout)

        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.advance_frame)
        self.is_playing = False

        # Install event filter to capture key presses
        self.installEventFilter(self)

    def set_markers(self, markers):
        self.markers = markers
        self.trimmer.set_markers(self.markers)

    def add_segment(self):
        self.trimmer.add_segment(self.trimmer.current_pos)
        self.update_segment_list()

    def update_segment_list(self):
        self.segment_list.clear()
        for i, (start, end) in enumerate(self.trimmer.segments):
            self.segment_list.addItem(f"Segment {i+1}: {start:.2f}s - {end:.2f}s")

    def select_segment_from_list(self, item):
        index = self.segment_list.row(item)
        self.trimmer.selected_segment = index
        self.trimmer.update()
        self.update_range(index, *self.trimmer.segments[index])

    def update_range(self, segment_index, start, end):
        self.start_time_label.setText(f"Start: {start:.3f}s")
        self.end_time_label.setText(f"End: {end:.3f}s")
        self.update_preview(start)
        self.update_segment_list()

    def update_current_time(self, time):
        self.current_time_label.setText(f"Current: {time:.3f}s")
        self.update_preview(time)

    def update_selected_segment(self, index):
        self.segment_list.setCurrentRow(index)

    def update_preview(self, time):
        frame = int(time * self.main_window.sampling_rate)
        pixmap = self.render_frame(frame)
        self.preview_item.setPixmap(pixmap)
        self.preview_scene.setSceneRect(QRectF(pixmap.rect()))
        self.preview_view.fitInView(self.preview_scene.sceneRect(), Qt.KeepAspectRatio)

    def toggle_play(self):
        if self.is_playing:
            self.play_timer.stop()
            self.play_button.setText("Play")
        else:
            self.play_timer.start(1000 // self.fps_spin.value())
            self.play_button.setText("Pause")
        self.is_playing = not self.is_playing

    def advance_frame(self):
        current_time = self.trimmer.current_pos + 1 / self.fps_spin.value()
        current_segment = self.trimmer.segments[self.trimmer.selected_segment]
        if current_time <= current_segment[1]:
            self.trimmer.current_pos = current_time
        else:
            self.trimmer.current_pos = current_segment[0]
        self.update_current_time(self.trimmer.current_pos)
        self.trimmer.update()

    def render_frame(self, frame):
        if frame in self.frame_cache:
            return self.frame_cache[frame]

        self.main_window.progress_bar.setValue(frame)
        self.main_window.update_grid()

        # Render the grid
        grid_pixmap = self.main_window.grid_widget.grab()

        # Render the graphs
        graph_pixmaps = []
        for i in range(4):
            if self.main_window.plotted_channels[i] is not None:
                self.main_window.graph_widget.update_red_lines(
                    frame, self.main_window.sampling_rate
                )
                graph_pixmap = self.main_window.graph_widget.plot_widgets[i].grab()
                graph_pixmaps.append(graph_pixmap)

        combined_pixmap = self.combine_pixmaps(grid_pixmap, graph_pixmaps)

        self.frame_cache[frame] = combined_pixmap
        return combined_pixmap

    def combine_pixmaps(self, grid_pixmap, graph_pixmaps):
        grid_width = grid_pixmap.width()
        grid_height = grid_pixmap.height()

        graph_width = grid_width
        total_width = grid_width * 2

        combined_pixmap = QPixmap(total_width, grid_height)
        combined_pixmap.fill(Qt.white)

        painter = QPainter(combined_pixmap)
        painter.drawPixmap(0, 0, grid_pixmap)

        num_graphs = len(graph_pixmaps)
        if num_graphs > 0:
            graph_height = grid_height // len(graph_pixmaps)

            for i, graph_pixmap in enumerate(graph_pixmaps):
                scaled_graph = graph_pixmap.scaled(
                    graph_width,
                    graph_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                painter.drawPixmap(grid_width, i * graph_height, scaled_graph)

        painter.end()
        return combined_pixmap

    def export_video(self):
        start_time = perf_counter()
        fps = self.fps_spin.value()

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", "output.mp4", "MP4 Files (*.mp4)"
        )

        if output_path:
            sample_frame = self.render_frame(0)
            width, height = sample_frame.width(), sample_frame.height()

            # Use H.264 codec with hardware acceleration if available
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            total_frames = sum(
                int((end - start) * self.main_window.sampling_rate)
                for start, end in self.trimmer.segments
            )
            progress_dialog = QProgressDialog(
                "Exporting Video...", "Cancel", 0, total_frames, self
            )
            progress_dialog.setWindowModality(Qt.WindowModal)

            try:
                frames_processed = 0
                for start, end in self.trimmer.segments:
                    start_frame = int(start * self.main_window.sampling_rate)
                    end_frame = int(end * self.main_window.sampling_rate)

                    for frame in range(start_frame, end_frame):
                        if progress_dialog.wasCanceled():
                            raise Exception("Export canceled by user")

                        pixmap = self.render_frame(frame)
                        image = self.qpixmap_to_cvimg(pixmap)
                        out.write(image)

                        frames_processed += 1
                        progress_dialog.setValue(frames_processed)
                        QApplication.processEvents()  # Allow GUI updates

            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))
            finally:
                end_time = perf_counter()
                total_time = end_time - start_time
                out.release()
                progress_dialog.close()
                alert(f"Video saved to {output_path} in {total_time:.2f} seconds.")

            if not progress_dialog.wasCanceled():
                QMessageBox.information(
                    self, "Video Created", f"Video saved to {output_path}"
                )

    def qpixmap_to_cvimg(self, pixmap):
        qimage = pixmap.toImage()
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.constBits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Space:
                self.toggle_play()
                return True
            elif event.key() == Qt.Key_N:
                self.add_segment()
                return True
            else:
                self.trimmer.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)
