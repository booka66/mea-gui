import h5py
import numpy as np
from scipy.spatial.distance import cdist
from PyQt5.QtGui import QPen, QColor, QImage, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QMessageBox,
)
from PyQt5.QtGui import QPainterPath
from PyQt5.QtCore import QPointF
from helpers.Constants import CELL_SIZE

from matplotlib import cm
from scipy.ndimage import gaussian_filter


class ClusterTracker:
    def __init__(
        self,
        max_distance=20.0,
        min_consecutive_frames=3,
        sampling_rate=100,
        min_seizure_length=0.5,
    ):
        self.clusters = []
        self.max_distance = max_distance
        self.min_consecutive_frames = min_consecutive_frames
        self.sampling_rate = sampling_rate
        self.min_seizure_length = min_seizure_length
        self.cluster_lines = []
        self.centroid_items = []
        self.colors = [
            QColor(r, g, b)
            for r, g, b in [
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (255, 255, 0),
                (255, 0, 255),
                (0, 255, 255),
                (128, 0, 0),
                (0, 128, 0),
                (0, 0, 128),
                (128, 128, 0),
                (128, 0, 128),
                (0, 128, 128),
            ]
        ]
        self.cluster_colors = {}
        self.current_time = 0
        self.history = []
        self.seizures = []
        self.seizure_graphics_items = []
        self.last_seizure = None

    def update(self, new_centroids, current_time):
        if current_time < self.current_time:
            self._restore_state(current_time)
        else:
            self._process_new_centroids(new_centroids, current_time)

        self.history.append((self._deep_copy_clusters(), current_time))

        self._clean_up_clusters_and_store_seizures()

    def _clean_up_clusters_and_store_seizures(self):
        new_clusters = []
        for cluster in self.clusters:
            if cluster[-1][1] > 0 or len(cluster) < self.min_consecutive_frames:
                new_clusters.append(cluster)
            else:
                self._check_and_store_seizure(cluster)

        self.clusters = new_clusters

    def _check_and_store_seizure(self, cluster):
        valid_points = [point for point, count, time in cluster if point is not None]
        if len(valid_points) > 1:
            length = sum(
                np.linalg.norm(
                    np.array(valid_points[j + 1]) - np.array(valid_points[j])
                )
                for j in range(len(valid_points) - 1)
            )
            length_mm = length * CELL_SIZE / 1000

            if length_mm >= self.min_seizure_length:
                start_time = cluster[0][2]
                end_time = cluster[-1][2]
                duration_s = end_time - start_time
                avg_speed = length_mm / duration_s if duration_s > 0 else 0

                seizure = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration_s * 1000,
                    "length": length_mm,
                    "avg_speed": avg_speed,
                    "points": valid_points,
                    "start_point": valid_points[0],
                    "end_point": valid_points[-1],
                    "time_since_last_discharge": (
                        start_time - self.last_seizure["start_time"]
                    )
                    * 1000
                    if self.last_seizure
                    else 0,
                }
                self.seizures.append(seizure)
                self.last_seizure = seizure

    def save_seizures_to_hdf(self, file_path, start, stop):
        try:
            with h5py.File(file_path, "a") as f:
                if "tracked_discharges" not in f:
                    f.create_group("tracked_discharges")

                discharges_group = f["tracked_discharges"]

                timeframe_group_name = f"{start:.2f}_{stop:.2f}"
                if timeframe_group_name not in discharges_group:
                    timeframe_group = discharges_group.create_group(
                        timeframe_group_name
                    )
                else:
                    timeframe_group = discharges_group[timeframe_group_name]
                for i, seizure in enumerate(self.seizures):
                    if f"discharge_{i}" in timeframe_group:
                        del timeframe_group[f"discharge_{i}"]
                    discharge_group = timeframe_group.create_group(f"discharge_{i}")
                    discharge_group.create_dataset(
                        "start_time", data=seizure["start_time"]
                    )
                    discharge_group.create_dataset("end_time", data=seizure["end_time"])
                    discharge_group.create_dataset("duration", data=seizure["duration"])
                    discharge_group.create_dataset("length", data=seizure["length"])
                    discharge_group.create_dataset(
                        "avg_speed", data=seizure["avg_speed"]
                    )
                    discharge_group.create_dataset("points", data=seizure["points"])
                    discharge_group.create_dataset(
                        "start_point", data=seizure["start_point"]
                    )
                    discharge_group.create_dataset(
                        "end_point", data=seizure["end_point"]
                    )
                    discharge_group.create_dataset(
                        "time_since_last_discharge",
                        data=seizure["time_since_last_discharge"],
                    )
        except Exception as e:
            print(f"Error saving seizures to HDF: {e}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Error saving seizures to HDF file. Double check that the file is not open in another program as that apparently is a big no-no."
            )
            msg.setInformativeText(f"Error: {e}")
            msg.setWindowTitle("Error")
            msg.exec_()

    def _deep_copy_clusters(self):
        return [cluster.copy() for cluster in self.clusters]

    def _restore_state(self, target_time):
        for past_clusters, past_time in reversed(self.history):
            if past_time <= target_time:
                self.clusters = past_clusters
                self.current_time = past_time
                break

        self.history = [h for h in self.history if h[1] <= target_time]

    def _process_new_centroids(self, new_centroids, current_time):
        if len(new_centroids) == 0:
            for cluster in self.clusters:
                cluster.append((None, 0, current_time))
        else:
            if not self.clusters:
                self.clusters = [
                    [(centroid, 1, current_time)] for centroid in new_centroids
                ]
                return

            matched_indices = set()
            for i, cluster in enumerate(self.clusters):
                last_centroid, _, last_time = cluster[-1]
                if last_centroid is not None:
                    distances = cdist([last_centroid], new_centroids)[0]
                    if distances.size > 0:
                        closest_index = np.argmin(distances)
                        if (
                            distances[closest_index] <= self.max_distance
                            and closest_index not in matched_indices
                        ):
                            cluster.append(
                                (
                                    new_centroids[closest_index],
                                    cluster[-1][1] + 1,
                                    current_time,
                                )
                            )
                            matched_indices.add(closest_index)
                        else:
                            cluster.append((None, 0, current_time))
                    else:
                        cluster.append((None, 0, current_time))
                else:
                    cluster.append((None, 0, current_time))

            for i, centroid in enumerate(new_centroids):
                if i not in matched_indices:
                    self.clusters.append([(centroid, 1, current_time)])

            for i, cluster in enumerate(self.clusters):
                if i not in self.cluster_colors:
                    self.cluster_colors[i] = self.colors[i % len(self.colors)]

        self.current_time = current_time

    def _clean_up_clusters(self):
        self.clusters = [
            cluster
            for cluster in self.clusters
            if cluster[-1][1] > 0 or len(cluster) < self.min_consecutive_frames
        ]

    def get_consistent_clusters(self):
        return [
            cluster
            for cluster in self.clusters
            if len(cluster) >= self.min_consecutive_frames
        ]

    def draw_cluster_points(self, scene, cell_width, cell_height):
        for item in self.centroid_items:
            scene.removeItem(item)
        self.centroid_items.clear()

        for i, cluster in enumerate(self.get_consistent_clusters()):
            if cluster[-1][0] is not None:
                centroid = cluster[-1][0]
                color = self.cluster_colors[i]

                centroid_item = QGraphicsEllipseItem(0, 0, 10, 10)
                centroid_item.setBrush(color)
                centroid_item.setPos(
                    centroid[1] * cell_width - 5, centroid[0] * cell_height - 5
                )
                scene.addItem(centroid_item)
                self.centroid_items.append(centroid_item)

    def draw_cluster_lines(self, scene, cell_width, cell_height):
        for item in self.cluster_lines:
            scene.removeItem(item)
        self.cluster_lines.clear()

        for i, cluster in enumerate(self.get_consistent_clusters()):
            points = [
                point
                for point, count, time in cluster
                if point is not None and time <= self.current_time
            ]
            if len(points) > 1:
                path = QPainterPath(
                    QPointF(points[0][1] * cell_width, points[0][0] * cell_height)
                )
                for point in points[1:]:
                    path.lineTo(QPointF(point[1] * cell_width, point[0] * cell_height))
                line_item = QGraphicsPathItem(path)
                line_item.setPen(QPen(QColor(0, 0, 0), 3, Qt.SolidLine))
                scene.addItem(line_item)
                self.cluster_lines.append(line_item)

        self.draw_cluster_points(scene, cell_width, cell_height)

    def get_cluster_stats(self):
        stats = []
        for i, cluster in enumerate(self.get_consistent_clusters()):
            valid_points = [
                (point, time)
                for point, count, time in cluster
                if point is not None and time <= self.current_time
            ]

            if len(valid_points) > 1:
                points, times = zip(*valid_points)

                duration_s = times[-1] - times[0]
                duration_ms = duration_s * 1000

                length = sum(
                    np.linalg.norm(np.array(points[j + 1]) - np.array(points[j]))
                    for j in range(len(points) - 1)
                )
                length_mm = length * CELL_SIZE / 1000

                avg_speed = length_mm / duration_s if duration_s > 0 else 0

                stats.append(
                    {
                        "color": self.cluster_colors[i],
                        "duration": duration_ms,
                        "length": length_mm,
                        "avg_speed": avg_speed,
                    }
                )
        return stats

    def get_seizures(self):
        return self.seizures

    def create_continuous_heatmap(self, scene, cell_width, cell_height, rows, cols):
        for item in self.seizure_graphics_items:
            scene.removeItem(item)
        self.seizure_graphics_items.clear()

        heatmap = np.zeros((rows, cols))

        for seizure in self.seizures:
            for point in seizure["points"]:
                row, col = point
                if 0 <= row < rows and 0 <= col < cols:
                    heatmap[int(row), int(col)] += 1

        smoothed_heatmap = gaussian_filter(heatmap, sigma=1)

        max_count = np.max(smoothed_heatmap)
        if max_count > 0:
            smoothed_heatmap = smoothed_heatmap / max_count

        image_width = int(cols * cell_width)
        image_height = int(rows * cell_height)
        image = QImage(image_width, image_height, QImage.Format_RGBA8888)
        image.fill(Qt.transparent)

        for row in range(rows):
            for col in range(cols):
                intensity = smoothed_heatmap[row, col]
                color = self.get_continuous_heatmap_color(intensity)
                for x in range(int(cell_width)):
                    for y in range(int(cell_height)):
                        image.setPixelColor(
                            int(col * cell_width + x), int(row * cell_height + y), color
                        )

        pixmap = QPixmap.fromImage(image)
        pixmap_item = QGraphicsPixmapItem(pixmap)
        pixmap_item.setOpacity(0.7)
        scene.addItem(pixmap_item)
        self.seizure_graphics_items.append(pixmap_item)

    def get_continuous_heatmap_color(self, intensity):
        r = int(255 * intensity)
        g = int(255 * (1 - intensity))
        b = int(255 * (1 - intensity))
        return QColor(r, g, b, 200)

    def reset_graphics_items(self, scene):
        if scene is None:
            return

        # Create a new list for valid items
        valid_items = []

        for item in self.seizure_graphics_items:
            try:
                if item.scene() == scene:
                    scene.removeItem(item)
                else:
                    valid_items.append(item)
            except RuntimeError:
                # Item has been deleted, so we ignore it
                pass

        # Update the list with only valid items
        self.seizure_graphics_items = valid_items

    def draw_heatmap(
        self, scene, cell_width, cell_height, rows, cols, painter=None, reset_scene=True
    ):
        if reset_scene:
            self.reset_graphics_items(scene)

        heatmap = np.zeros((rows, cols))

        for seizure in self.seizures:
            for point in seizure["points"]:
                row, col = point
                if 0 <= row < rows and 0 <= col < cols:
                    heatmap[int(row), int(col)] += 1

        max_count = np.max(heatmap)
        if max_count > 0:
            heatmap = heatmap / max_count

        for row in range(rows):
            for col in range(cols):
                intensity = heatmap[row, col]
                if intensity > 0:
                    color = self.get_heatmap_color(intensity)
                    rect = QGraphicsRectItem(
                        col * cell_width, row * cell_height, cell_width, cell_height
                    )
                    rect.setBrush(color)
                    scene.addItem(rect)
                    self.seizure_graphics_items.append(rect)
                    if painter:
                        painter.setBrush(rect.brush())
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(rect.rect().translated(rect.pos()))

    def get_heatmap_color(self, intensity):
        r = int(255 * intensity)
        g = 0
        b = int(255 * (1 - intensity))
        return QColor(r, g, b)

    def get_color_for_time(self, fraction):
        r = int(255 * fraction)
        g = int(255 * (1 - fraction))
        b = 0
        return QColor(r, g, b)

    def draw_beginning_points(
        self, scene, cell_width, cell_height, painter=None, reset_scene=True
    ):
        if reset_scene:
            self.reset_graphics_items(scene)
        if not self.seizures:
            return
        start_times = [seizure["start_time"] for seizure in self.seizures]
        earliest_start = min(start_times)
        latest_start = max(start_times)

        colormap = cm.get_cmap("cool")

        for i, seizure in enumerate(self.seizures):
            points = seizure["points"]
            if len(points) < 1:
                continue
            start_point = points[0]
            time_fraction = (
                (seizure["start_time"] - earliest_start)
                / (latest_start - earliest_start)
                if latest_start != earliest_start
                else 0
            )

            # Use the colormap to get the color
            color_rgba = colormap(time_fraction)
            color = QColor.fromRgbF(color_rgba[0], color_rgba[1], color_rgba[2])

            start_marker = QGraphicsEllipseItem(0, 0, 10, 10)
            start_marker.setBrush(color)
            start_marker.setPos(
                start_point[1] * cell_width - 5, start_point[0] * cell_height - 5
            )
            scene.addItem(start_marker)
            self.seizure_graphics_items.append(start_marker)
            if painter:
                painter.setBrush(start_marker.brush())
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(start_marker.rect().translated(start_marker.pos()))

    def draw_seizures(
        self, scene, cell_width, cell_height, painter=None, reset_scene=True
    ):
        if reset_scene:
            self.reset_graphics_items(scene)

        colormap = cm.get_cmap("cool")
        start_color = colormap(0.1)  # First color in the colormap
        end_color = colormap(0.9)  # Last color in the colormap

        for seizure in self.seizures:
            points = seizure["points"]
            if len(points) < 2:
                continue

            # Draw the seizure path
            path = QPainterPath(
                QPointF(points[0][1] * cell_width, points[0][0] * cell_height)
            )
            for point in points[1:]:
                path.lineTo(QPointF(point[1] * cell_width, point[0] * cell_height))
            path_item = QGraphicsPathItem(path)
            path_item.setPen(QPen(QColor(0, 0, 0, int(255 * 0.1)), 2, Qt.DashLine))
            scene.addItem(path_item)
            self.seizure_graphics_items.append(path_item)

            if painter:
                painter.setPen(path_item.pen())
                painter.setBrush(Qt.NoBrush)  # Ensure no fill
                painter.drawPath(path_item.path())

            # Draw start point
            start_point = QGraphicsEllipseItem(0, 0, 10, 10)
            start_point.setBrush(QColor.fromRgbF(*start_color))
            start_point.setPos(
                points[0][1] * cell_width - 5, points[0][0] * cell_height - 5
            )
            scene.addItem(start_point)
            self.seizure_graphics_items.append(start_point)

            if painter:
                painter.setBrush(start_point.brush())
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(start_point.rect().translated(start_point.pos()))

            # Draw end point
            end_point = QGraphicsEllipseItem(0, 0, 10, 10)
            end_point.setBrush(QColor.fromRgbF(*end_color))
            end_point.setPos(
                points[-1][1] * cell_width - 5, points[-1][0] * cell_height - 5
            )
            scene.addItem(end_point)
            self.seizure_graphics_items.append(end_point)

            if painter:
                painter.setBrush(end_point.brush())
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(end_point.rect().translated(end_point.pos()))

    def clear(self):
        self.clusters.clear()
        self.cluster_lines.clear()
        self.centroid_items.clear()
        self.cluster_colors.clear()
        self.current_time = 0
        self.history.clear()
        self.seizures.clear()
        self.seizure_graphics_items.clear()

    def clear_plot(self, scene: QGraphicsScene):
        for item in scene.items():
            if item in self.seizure_graphics_items:
                scene.removeItem(item)
        self.seizure_graphics_items.clear()
