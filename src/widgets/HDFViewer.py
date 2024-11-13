import h5py
import time
from PyQt5.QtWidgets import (
    QMainWindow,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QMenuBar,
    QMenu,
    QAction,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QApplication,
    QShortcut,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeySequence
import numpy as np
from collections import deque


class DeleteOperation:
    def __init__(self, path, item_type, value, parent_path=None, attributes=None):
        self.path = path
        self.item_type = item_type
        self.value = value
        self.parent_path = parent_path
        self.attributes = attributes or {}


class HDF5TreeModel(QStandardItemModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.root_item = self.invisibleRootItem()
        self.setup_model_data(data, self.root_item)

    def setup_model_data(self, hdf5_file, parent_item, path="/"):
        try:
            # Iterate through groups
            for name, item in hdf5_file[path].items():
                current_path = f"{path}/{name}".replace("//", "/")
                node = QStandardItem(name)
                node.setData(current_path, Qt.UserRole)

                if isinstance(item, h5py.Group):
                    node.setData("group", Qt.UserRole + 1)
                    self.setup_model_data(hdf5_file, node, current_path)
                else:  # Dataset
                    node.setData("dataset", Qt.UserRole + 1)
                    shape_str = str(item.shape) if hasattr(item, "shape") else ""
                    dtype_str = str(item.dtype) if hasattr(item, "dtype") else ""
                    info_item = QStandardItem(f"Shape: {shape_str}, Type: {dtype_str}")
                    node.appendRow(info_item)

                # Add attributes if any
                if hasattr(item, "attrs"):
                    attrs_node = QStandardItem("Attributes")
                    for attr_name, attr_value in item.attrs.items():
                        attr_item = QStandardItem(f"{attr_name}: {attr_value}")
                        attr_item.setData(f"{current_path}/@{attr_name}", Qt.UserRole)
                        attr_item.setData("attribute", Qt.UserRole + 1)
                        attrs_node.appendRow(attr_item)
                    node.appendRow(attrs_node)

                parent_item.appendRow(node)
        except Exception as e:
            print(f"Error loading HDF5 data: {e}")

    def remove_item(self, index):
        """Remove an item from the model without reloading the entire tree."""
        if index.isValid():
            parent = index.parent()
            self.removeRow(index.row(), parent)

    def insert_item(self, path, item_type, parent_path=None):
        """Insert an item back into the tree model with full data."""
        try:
            parts = path.split("/")
            name = parts[-1]

            # Find the parent item
            if parent_path:
                parent_item = self.find_item_by_path(parent_path)
            else:
                parent_item = self.invisibleRootItem()

            if parent_item:
                node = QStandardItem(name)
                node.setData(path, Qt.UserRole)
                node.setData(item_type, Qt.UserRole + 1)

                # Add additional info based on type
                if item_type == "dataset":
                    item = self.hdf5[path]
                    shape_str = str(item.shape) if hasattr(item, "shape") else ""
                    dtype_str = str(item.dtype) if hasattr(item, "dtype") else ""
                    info_item = QStandardItem(f"Shape: {shape_str}, Type: {dtype_str}")
                    node.appendRow(info_item)

                    # Add attributes
                    if hasattr(item, "attrs") and len(item.attrs) > 0:
                        attrs_node = QStandardItem("Attributes")
                        for attr_name, attr_value in item.attrs.items():
                            attr_item = QStandardItem(f"{attr_name}: {attr_value}")
                            attr_item.setData(f"{path}/@{attr_name}", Qt.UserRole)
                            attr_item.setData("attribute", Qt.UserRole + 1)
                            attrs_node.appendRow(attr_item)
                        node.appendRow(attrs_node)

                elif item_type == "group":
                    item = self.hdf5[path]
                    # Recursively add group contents
                    for child_name, child_item in item.items():
                        child_path = f"{path}/{child_name}"
                        child_type = (
                            "group" if isinstance(child_item, h5py.Group) else "dataset"
                        )
                        self.setup_model_data(self.hdf5, node, path)

                    # Add attributes
                    if hasattr(item, "attrs") and len(item.attrs) > 0:
                        attrs_node = QStandardItem("Attributes")
                        for attr_name, attr_value in item.attrs.items():
                            attr_item = QStandardItem(f"{attr_name}: {attr_value}")
                            attr_item.setData(f"{path}/@{attr_name}", Qt.UserRole)
                            attr_item.setData("attribute", Qt.UserRole + 1)
                            attrs_node.appendRow(attr_item)
                        node.appendRow(attrs_node)

                parent_item.appendRow(node)
                return node
        except Exception as e:
            print(f"Error inserting item: {e}")
        return None

    def find_item_by_path(self, path):
        """Find an item in the tree model by its path."""

        def search_recursive(parent_item):
            for row in range(parent_item.rowCount()):
                current_item = parent_item.child(row)
                if current_item.data(Qt.UserRole) == path:
                    return current_item
                if current_item.hasChildren():
                    result = search_recursive(current_item)
                    if result:
                        return result
            return None

        return search_recursive(self.invisibleRootItem())


class HDF5Viewer(QMainWindow):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.file_path = file_path
        self.hdf5 = None
        self.tree = None
        self.tree_model = None
        self.tree_view = None
        self.read_only = False
        self.undo_stack = deque(maxlen=100)  # Store up to 100 operations
        self.setup_ui()
        self.load_hdf5()

    def setup_ui(self):
        self.setWindowTitle("HDF5 Viewer")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        self.mode_button = QPushButton("Mode: Read-Write")
        self.mode_button.clicked.connect(self.toggle_mode)
        toolbar_layout.addWidget(self.mode_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_hdf5)
        toolbar_layout.addWidget(refresh_button)

        # Add undo button
        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo_last_deletion)
        toolbar_layout.addWidget(self.undo_button)

        toolbar_layout.addStretch()
        main_layout.addWidget(toolbar)

        self.tree_view = QTreeView()
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.tree_view)

        menubar = QMenuBar()
        self.setMenuBar(menubar)

        file_menu = QMenu("File", self)
        menubar.addMenu(file_menu)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.load_hdf5)
        file_menu.addAction(refresh_action)

        # Add Ctrl+Z shortcut
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo_last_deletion)

    def get_item_attributes(self, item):
        """Get all attributes of an HDF5 item."""
        if hasattr(item, "attrs"):
            return dict(item.attrs)
        return {}

    def store_delete_operation(self, path, item_type, parent_path=None):
        """Store information about the deleted item for potential undo."""
        try:
            if item_type == "dataset":
                value = np.array(self.hdf5[path])
                attributes = self.get_item_attributes(self.hdf5[path])
            elif item_type == "attribute":
                group_path, attr_name = path.split("@")
                value = self.hdf5[group_path].attrs[attr_name]
                attributes = {}
            elif item_type == "group":
                # For groups, we need to store all nested items
                value = self.store_group_structure(self.hdf5[path])
                attributes = self.get_item_attributes(self.hdf5[path])

            operation = DeleteOperation(path, item_type, value, parent_path, attributes)
            self.undo_stack.append(operation)
            self.undo_button.setEnabled(True)

        except Exception as e:
            print(f"Error storing delete operation: {e}")

    def store_group_structure(self, group):
        """Recursively store the structure and content of a group."""
        structure = {}
        for name, item in group.items():
            if isinstance(item, h5py.Group):
                structure[name] = {
                    "type": "group",
                    "attributes": dict(item.attrs),
                    "content": self.store_group_structure(item),
                }
            else:  # Dataset
                structure[name] = {
                    "type": "dataset",
                    "value": np.array(item),
                    "attributes": dict(item.attrs),
                }
        return structure

    def restore_group_structure(self, path, structure):
        """Recursively restore a group structure."""
        try:
            group = self.hdf5.create_group(path)
            for name, item in structure.items():
                item_path = f"{path}/{name}"
                if item["type"] == "group":
                    self.restore_group_structure(item_path, item["content"])
                else:  # Dataset
                    dataset = self.hdf5.create_dataset(item_path, data=item["value"])
                    for attr_name, attr_value in item["attributes"].items():
                        dataset.attrs[attr_name] = attr_value

            # Restore group attributes
            for attr_name, attr_value in structure.get("attributes", {}).items():
                group.attrs[attr_name] = attr_value

        except Exception as e:
            print(f"Error restoring group structure: {e}")

    def undo_last_deletion(self):
        """Undo the last deletion operation."""
        if not self.undo_stack or self.read_only:
            return

        try:
            operation = self.undo_stack.pop()

            if operation.item_type == "dataset":
                dataset = self.hdf5.create_dataset(operation.path, data=operation.value)
                for attr_name, attr_value in operation.attributes.items():
                    dataset.attrs[attr_name] = attr_value

            elif operation.item_type == "attribute":
                group_path, attr_name = operation.path.split("@")
                self.hdf5[group_path].attrs[attr_name] = operation.value

            elif operation.item_type == "group":
                self.restore_group_structure(operation.path, operation.value)

            # Refresh the tree view
            self.load_hdf5()

            if not self.undo_stack:
                self.undo_button.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to undo deletion: {str(e)}")

    def get_item_value(self, path, item_type):
        """Get the value of a dataset, group, or attribute."""
        try:
            if item_type == "dataset":
                return np.array(self.hdf5[path])
            elif item_type == "attribute":
                group_path, attr_name = path.split("@")
                return self.hdf5[group_path].attrs[attr_name]
            elif item_type == "group":
                return list(self.hdf5[path].keys())
            return None
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to get value: {str(e)}")
            return None

    def copy_to_clipboard(self, path, item_type):
        """Copy the value to clipboard."""
        value = self.get_item_value(path, item_type)
        if value is not None:
            clipboard = QApplication.clipboard()
            if isinstance(value, np.ndarray):
                text = np.array2string(value, separator=", ")
            else:
                text = str(value)
            clipboard.setText(text)

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        item = self.tree_model.itemFromIndex(index)
        item_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)

        if item_type not in ["dataset", "attribute", "group"]:
            return

        menu = QMenu()

        copy_action = QAction("Copy Value", self)
        copy_action.triggered.connect(
            lambda: self.copy_to_clipboard(item_path, item_type)
        )
        menu.addAction(copy_action)

        if not self.read_only:
            menu.addSeparator()
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(
                lambda: self.delete_item(item_path, item_type, index)
            )
            menu.addAction(delete_action)

        menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def delete_item(self, path, item_type, index):
        """Delete an item and update the tree view without reloading."""
        if self.read_only:
            QMessageBox.warning(self, "Warning", "File is opened in read-only mode")
            return

        try:
            # Store the delete operation before actually deleting
            parent_index = index.parent()
            parent_path = (
                self.tree_model.itemFromIndex(parent_index).data(Qt.UserRole)
                if parent_index.isValid()
                else None
            )
            self.store_delete_operation(path, item_type, parent_path)

            # Perform the deletion
            if item_type == "dataset":
                del self.hdf5[path]
            elif item_type == "attribute":
                group_path, attr_name = path.split("@")
                del self.hdf5[group_path].attrs[attr_name]
            elif item_type == "group":
                del self.hdf5[path]

            self.tree_model.remove_item(index)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to delete {item_type}: {str(e)}"
            )

    def toggle_mode(self):
        self.read_only = not self.read_only
        self.mode_button.setText(
            f"Mode: {'Read-Only' if self.read_only else 'Read-Write'}"
        )
        self.load_hdf5()

    def load_hdf5(self, retries=3, delay=1):
        if self.hdf5 is not None:
            try:
                self.hdf5.close()
            except:
                pass

        for attempt in range(retries):
            try:
                mode = "r" if self.read_only else "r+"
                self.hdf5 = h5py.File(self.file_path, mode)

                self.tree_model = HDF5TreeModel(self.hdf5)
                self.tree_view.setModel(self.tree_model)

                # Tree starts fully collapsed by default
                self.tree_view.collapseAll()

                self.setWindowTitle(f"HDF5 Viewer - {self.file_path} ({mode})")
                return

            except OSError as e:
                if e.errno == 35:
                    if attempt < retries - 1:
                        time.sleep(delay)
                        continue
                    else:
                        if not self.read_only:
                            response = QMessageBox.question(
                                self,
                                "File Access Error",
                                "File appears to be locked. Would you like to open in read-only mode?",
                                QMessageBox.Yes | QMessageBox.No,
                            )
                            if response == QMessageBox.Yes:
                                self.read_only = True
                                self.mode_button.setText("Mode: Read-Only")
                                self.load_hdf5()
                                return

                        QMessageBox.critical(
                            self,
                            "Error",
                            f"Failed to open file after {retries} attempts. File may be locked by another process.",
                        )
                else:
                    QMessageBox.critical(
                        self, "Error", f"Failed to load HDF5 file: {str(e)}"
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load HDF5 file: {str(e)}"
                )
                break

    def closeEvent(self, event):
        if self.hdf5 is not None:
            try:
                self.hdf5.close()
            except:
                pass
        # Emit the destroyed signal before accepting the event
        self.destroyed.emit()
        event.accept()
