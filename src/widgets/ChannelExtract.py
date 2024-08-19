import math
import sys
import os
import json
import typing
from PyQt5 import QtGui
import numpy as np
import h5py
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
    QSplitter,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QDoubleSpinBox,
    QFileDialog,
    QHeaderView,
    QSizePolicy,
    QGroupBox,
    QGridLayout,
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
import matplotlib.image as mpimg
import subprocess
import qdarktheme


SIZE = 30
MARKER = "s"


class ScatterPlot(QWidget):
    def __init__(self, parent=None, uploadedImage=None):
        super().__init__(parent)
        self.initUI()
        self.parent = parent
        self.selected_points = []
        self.uploadedImage = uploadedImage
        self.undo_stack = []
        self.redo_stack = []
        self.setFocusPolicy(Qt.StrongFocus)

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        fig = Figure(figsize=(5, 5), dpi=100)
        fig.set_tight_layout(True)
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)

        self.ax = fig.add_subplot(111)
        self.ax.set_aspect("equal")  # Set the aspect ratio to be equal

        self.x = np.arange(1, 65)
        self.y = np.arange(1, 65)
        self.x, self.y = np.meshgrid(self.x, self.y)
        self.x = self.x.flatten()
        self.y = self.y.flatten()

        self.ax.scatter(self.x, self.y, c="k", s=SIZE, alpha=0.3, marker=MARKER)

        self.lasso = LassoSelector(
            self.ax,
            self.lasso_callback,
            button=[1, 3],
            useblit=True,
        )

        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.invert_yaxis()  # Invert the y-axis

        self.canvas.draw()

    def lasso_callback(self, verts):
        if self.parent.inputFileName is None or not os.path.exists(
            self.parent.inputFileName
        ):
            return
        path = Path(verts)
        if self.uploadedImage is not None:
            height, width, _ = self.uploadedImage.shape
            new_selected_points = [
                (x, y)
                for x, y in zip(self.x, self.y)
                if path.contains_point((x * width / 64, y * height / 64))
            ]
        else:
            new_selected_points = [
                (x, y) for x, y in zip(self.x, self.y) if path.contains_point((x, y))
            ]

        self.undo_stack.append(self.selected_points.copy())
        self.redo_stack.clear()
        self.selected_points.extend(new_selected_points)

        self.update_selected_points_plot()

        verts = np.append(verts, [verts[0]], axis=0)
        if hasattr(self, "lasso_line"):
            self.lasso_line.remove()
        self.lasso_line = self.ax.plot(
            verts[:, 0], verts[:, 1], "b-", linewidth=1, alpha=0.8
        )[0]

        self.canvas.draw()
        self.parent.updateChannelCount()

    def update_selected_points_plot(self):
        if hasattr(self, "selected_points_plot"):
            self.selected_points_plot.remove()
        if self.uploadedImage is not None:
            height, width, _ = self.uploadedImage.shape
            self.selected_points_plot = self.ax.scatter(
                [point[0] * width / 64 for point in self.selected_points],
                [point[1] * height / 64 for point in self.selected_points],
                c="red",
                s=SIZE,
                alpha=0.8,
                marker=MARKER,
            )
        else:
            self.selected_points_plot = self.ax.scatter(
                [point[0] for point in self.selected_points],
                [point[1] for point in self.selected_points],
                c="red",
                s=SIZE,
                alpha=0.8,
                marker=MARKER,
            )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self.clear_selection()
        elif event.key() == Qt.Key_Z:
            if event.modifiers() & Qt.ShiftModifier:
                self.redo_selection()
            else:
                self.undo_selection()

    def clear_selection(self):
        if self.lasso.active:
            self.lasso_line.set_visible(False)
            self.canvas.draw()
        self.undo_stack.append(self.selected_points.copy())
        self.redo_stack.clear()
        self.selected_points.clear()
        self.update_selected_points_plot()
        self.canvas.draw()
        self.parent.updateChannelCount()

    def undo_selection(self):
        if self.undo_stack:
            if self.lasso.active:
                self.lasso_line.set_visible(False)
                self.canvas.draw()

            self.redo_stack.append(self.selected_points.copy())
            self.selected_points = self.undo_stack.pop()
            self.update_selected_points_plot()
            self.canvas.draw()
            self.parent.updateChannelCount()

    def redo_selection(self):
        if self.redo_stack:
            if self.lasso.active:
                self.lasso_line.set_visible(False)
                self.canvas.draw()

            self.undo_stack.append(self.selected_points.copy())
            self.selected_points = self.redo_stack.pop()
            self.update_selected_points_plot()
            self.canvas.draw()
            self.parent.updateChannelCount()

    def onrelease(self, event):
        if self.lasso.active:
            self.lasso_line.set_visible(False)
            self.canvas.draw()

    def showHotkeysHelp(self):
        hotkeys = [
            "There is no shift+click to do multiple selections. Just keep drawing and use the hotkeys to clear, undo, or redo.",
            "c: Clear",
            "z: Undo",
            "shift+z: Redo",
        ]
        QMessageBox.information(self, "Plot Hotkeys", "\n".join(hotkeys))


class ChannelExtract(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection GUI")
        self.resize(1200, 800)

        # Create main widget and layout
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)

        self.createHeader()
        self.createDataTable()
        self.createChannelSelectionSection()
        self.createSplitter()

        # Initialize variables
        self.inputFileName = ""
        self.uploadedImage = None
        self.typ = None
        self.size = [0, 65, 65, 0]
        self.dataTable.status_items = {}
        self.dataTable.select_buttons = {}
        self.folderName = None
        self.previously_selected_row = None
        self.theme = "dark"
        self.last_exported_selection = None

        self.showMaximized()

    def toggleTheme(self):
        if self.theme == "dark":
            qdarktheme.setup_theme("light")
            self.theme = "light"
        else:
            qdarktheme.setup_theme("dark")
            self.theme = "dark"

    def createHeader(self):
        headerLayout = QHBoxLayout()
        # Add application title
        self.headerLabel = QLabel("Channel Selection GUI")
        self.headerLabel.setFont(QFont("Arial", 16, QFont.Bold))
        self.headerLabel.setAlignment(Qt.AlignCenter)
        headerLayout.addWidget(self.headerLabel)

        # Add spacer to push title to the center
        headerLayout.addStretch()

        self.mainLayout.addLayout(headerLayout)

    def createDataTable(self):
        self.dataTableWidget = QWidget()
        self.dataTableLayout = QVBoxLayout()
        self.dataTableWidget.setLayout(self.dataTableLayout)

        self.dataTable = QTableWidget()
        self.dataTable.setColumnCount(10)
        self.dataTable.setHorizontalHeaderLabels(
            [
                "File Path",
                "File Name",
                "Version",
                "Data Format",
                "Active Channels",
                "Data per Channel",
                "Recording Time (s)",
                "Sampling (Hz)",
                "Status",
                "Select",
            ]
        )
        self.dataTable.horizontalHeader().setFont(QFont("Arial", 10))
        self.dataTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.dataTableLayout.addWidget(self.dataTable)

    def createChannelSelectionSection(self):
        self.channelSelectionWidget = QWidget()
        self.channelSelectionLayout = QVBoxLayout()
        self.channelSelectionWidget.setLayout(self.channelSelectionLayout)

        groupBox = QGroupBox("Channel Selection")
        groupBox.setFont(QFont("Arial", 12))

        gridLayout = QGridLayout()

        # Create input grid
        self.inputGridWidget = ScatterPlot(self)
        self.inputGridWidget.setMinimumSize(500, 500)
        self.inputGridWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        gridLayout.addWidget(self.inputGridWidget, 0, 0)

        # Create channel settings section
        settingsWidget = QWidget()
        settingsLayout = QVBoxLayout()
        settingsWidget.setLayout(settingsLayout)

        uploadButton = QPushButton("Upload Folder")
        uploadButton.clicked.connect(self.uploadFiles)
        settingsLayout.addWidget(uploadButton)

        self.channelCountLabel = QLabel("Channel Count: 0")
        self.channelCountLabel.setFont(QFont("Arial", 10))
        settingsLayout.addWidget(self.channelCountLabel)

        rowSkipLabel = QLabel("# Rows to Skip:")
        self.rowSkipSpinBox = QSpinBox()
        self.rowSkipSpinBox.setRange(0, 3)
        self.rowSkipSpinBox.valueChanged.connect(self.updateChannelCount)
        settingsLayout.addWidget(rowSkipLabel)
        settingsLayout.addWidget(self.rowSkipSpinBox)

        colSkipLabel = QLabel("# Columns to Skip:")
        self.colSkipSpinBox = QSpinBox()
        self.colSkipSpinBox.setRange(0, 3)
        self.colSkipSpinBox.valueChanged.connect(self.updateChannelCount)
        settingsLayout.addWidget(colSkipLabel)
        settingsLayout.addWidget(self.colSkipSpinBox)

        downsampleLabel = QLabel("Downsampling (Hz):")
        self.downsampleSpinBox = QDoubleSpinBox()
        self.downsampleSpinBox.setRange(0, 100000)
        self.downsampleSpinBox.setValue(300)
        settingsLayout.addWidget(downsampleLabel)
        settingsLayout.addWidget(self.downsampleSpinBox)

        startTimeLabel = QLabel("Start Time (s):")
        self.startTimeSpinBox = QDoubleSpinBox()
        self.startTimeSpinBox.setRange(0, 100000)
        settingsLayout.addWidget(startTimeLabel)
        settingsLayout.addWidget(self.startTimeSpinBox)

        endTimeLabel = QLabel("End Time (s):")
        self.endTimeSpinBox = QDoubleSpinBox()
        settingsLayout.addWidget(endTimeLabel)
        settingsLayout.addWidget(self.endTimeSpinBox)

        exportButton = QPushButton("Export Channels")
        exportButton.clicked.connect(self.exportChannels)
        settingsLayout.addWidget(exportButton)

        # Add "Restore selection" button
        restoreButton = QPushButton("Restore Selection")
        restoreButton.clicked.connect(self.restoreSelection)
        settingsLayout.addWidget(restoreButton)

        downsampleExportButton = QPushButton("Downsample Export")
        downsampleExportButton.clicked.connect(self.runDownsampleExport)
        settingsLayout.addWidget(downsampleExportButton)

        settingsLayout.addStretch()

        gridLayout.addWidget(settingsWidget, 0, 1)

        # Create output grid
        self.outputGridWidget = ScatterPlot()
        self.outputGridWidget.setMinimumSize(500, 500)
        self.outputGridWidget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        gridLayout.addWidget(self.outputGridWidget, 0, 2)

        groupBox.setLayout(gridLayout)
        self.channelSelectionLayout.addWidget(groupBox)

    def createStatusBar(self):
        self.statusBar().setFont(QFont("Arial", 10))
        print("Ready")

        themeButton = QPushButton("Toggle Theme")
        themeButton.clicked.connect(self.toggleTheme)
        self.statusBar().addPermanentWidget(themeButton)

        helpButton = QPushButton("Help")
        helpButton.clicked.connect(self.inputGridWidget.showHotkeysHelp)
        self.statusBar().addPermanentWidget(helpButton)

    def createSplitter(self):
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.dataTableWidget)
        splitter.addWidget(self.channelSelectionWidget)
        self.mainLayout.addWidget(splitter)

    def updateChannelCount(self):
        selectedPoints = self.inputGridWidget.selected_points
        if selectedPoints:
            row_step = self.rowSkipSpinBox.value()
            col_step = self.colSkipSpinBox.value()

            channel_count = sum(
                1
                for x, y in selectedPoints
                if y % (row_step + 1) == 0 and x % (col_step + 1) == 0
            )

            self.channelCountLabel.setText(f"Channel Count: {channel_count}")

    def uploadFiles(self):
        options = QFileDialog.Options()
        self.folderName = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", options=options
        )
        print(self.folderName)
        if self.folderName:
            tableData = []
            self.imageDict = {}

            brwFiles = [f for f in os.listdir(self.folderName) if f.endswith(".brw")]

            for brwFile in brwFiles:
                try:
                    fileName = os.path.join(self.folderName, brwFile)
                    fileName = os.path.normpath(fileName)
                    if fileName.__contains__("resample") or fileName.__contains__(
                        "exportCh"
                    ):
                        continue
                    h5 = h5py.File(fileName, "r")
                    self.get_type(h5)
                    parameters = self.parameter(h5)
                except Exception as e:
                    print(f"Error reading file {brwFile}: {str(e)}")
                    continue
                chsList = parameters["recElectrodeList"]
                filePath = self.folderName
                baseName = os.path.basename(fileName)
                dateSlice = "_".join(baseName.split("_")[:4])
                dateSliceNumber = (
                    dateSlice.split("slice")[0]
                    + "slice"
                    + dateSlice.split("slice")[1][:1]
                )
                imageName = f"{dateSliceNumber}_pic_cropped.jpg".lower()
                imageFolder = self.folderName
                imagePath = os.path.join(imageFolder, imageName)

                if os.path.exists(imagePath):
                    image = mpimg.imread(imagePath)
                else:
                    imageFiles = [
                        f for f in os.listdir(imageFolder) if f.lower() == imageName
                    ]
                    if imageFiles:
                        imagePath = os.path.join(imageFolder, imageFiles[0])
                        image = mpimg.imread(imagePath)
                    else:
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Information)
                        msg.setText(
                            f"No image found, manually select image for {baseName}"
                        )
                        msg.setWindowTitle("Image Not Found")
                        msg.exec_()
                        imageFileName, _ = QFileDialog.getOpenFileName(
                            self,
                            "Upload Slice Image",
                            "",
                            "Image Files (*.jpg *.png)",
                            options=options,
                        )
                        if imageFileName:
                            image = mpimg.imread(imageFileName)
                        else:
                            image = None

                self.imageDict[fileName] = image

                tableData.append(
                    [
                        filePath,
                        baseName,
                        parameters["Ver"],
                        parameters["Typ"],
                        len(chsList),
                        parameters["nRecFrames"],
                        round(parameters["nRecFrames"] / parameters["samplingRate"]),
                        parameters["samplingRate"],
                        "Not Exported",
                        QPushButton("Select"),
                    ]
                )

                h5.close()

            self.populateTable(tableData)

    def populateTable(self, data):
        self.dataTable.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, item in enumerate(row):
                if isinstance(item, QPushButton):
                    self.dataTable.setCellWidget(i, j, item)
                    item.clicked.connect(lambda _, r=i: self.selectFile(r))
                else:
                    table_item = QTableWidgetItem(str(item))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table_item.setTextAlignment(Qt.AlignCenter)
                    if j == len(row) - 2:
                        table_item.setBackground(QColor("#bc4749"))
                    self.dataTable.setItem(i, j, table_item)

        self.dataTable.resizeColumnsToContents()

    def selectFile(self, row):
        fileName = os.path.join(
            self.dataTable.item(row, 0).text(), self.dataTable.item(row, 1).text()
        )
        fileName = os.path.normpath(fileName)
        self.inputFileName = fileName
        self.uploadedImage = self.imageDict.get(fileName)
        self.updateGrid()

        if (
            self.previously_selected_row is not None
            and self.previously_selected_row != row
        ):
            self.dataTable.cellWidget(
                self.previously_selected_row, self.dataTable.columnCount() - 1
            ).setEnabled(True)

        self.dataTable.cellWidget(row, self.dataTable.columnCount() - 1).setEnabled(
            False
        )

        if self.inputGridWidget.selected_points:
            self.inputGridWidget.selected_points = []
            self.inputGridWidget.undo_stack.append(
                self.inputGridWidget.selected_points.copy()
            )
            self.inputGridWidget.redo_stack.clear()
            self.inputGridWidget.update_selected_points_plot()
            self.inputGridWidget.canvas.draw()
            self.updateChannelCount()

        self.outputGridWidget.ax.clear()
        self.outputGridWidget.canvas.draw()

        self.dataTable.selectRow(row)
        self.previously_selected_row = row

    def updateGrid(self):
        if self.inputFileName and os.path.exists(self.inputFileName):
            h5 = h5py.File(self.inputFileName, "r")
            self.get_type(h5)
            parameters = self.parameter(h5)
            chsList = parameters["recElectrodeList"]
            endTime = parameters["recordingLength"]

            Xs, Ys, idx = self.getChMap(chsList)

            self.inputGridWidget.ax.clear()
            self.inputGridWidget.uploadedImage = (
                self.uploadedImage
            )  # Pass the uploadedImage to the ScatterPlot instance
            if self.uploadedImage is not None:
                # Calculate the aspect ratio based on the image dimensions
                height, width, _ = self.uploadedImage.shape
                aspect_ratio = width / height

                # Set the aspect ratio of the grid to match the image aspect ratio
                self.inputGridWidget.ax.set_aspect(aspect_ratio)

                # Display the image and set the x and y limits based on the image dimensions
                self.inputGridWidget.ax.imshow(
                    self.uploadedImage, extent=[0, width, height, 0]
                )

                # Scale the grid coordinates to match the image dimensions
                Xs = [x * width / 64 for x in Xs]
                Ys = [y * height / 64 for y in Ys]

                self.inputGridWidget.ax.set_xlim(0, width)
                self.inputGridWidget.ax.set_ylim(height, 0)
            else:
                self.inputGridWidget.ax.set_aspect("equal")
                self.inputGridWidget.ax.set_xlim(self.size[0], self.size[2])
                self.inputGridWidget.ax.set_ylim(self.size[2], self.size[3])

            self.inputGridWidget.ax.scatter(
                Xs, Ys, c="k", s=SIZE, alpha=0.3, marker=MARKER
            )
            self.inputGridWidget.ax.set_xticks([])
            self.inputGridWidget.ax.set_yticks([])
            self.inputGridWidget.ax.invert_yaxis()

            self.inputGridWidget.canvas.draw()

            self.endTimeSpinBox.setRange(0, endTime)
            self.endTimeSpinBox.setValue(endTime)

            h5.close()
        else:
            print("No .brw file selected")

            self.inputGridWidget.ax.clear()
            self.inputGridWidget.canvas.draw()

    def restoreSelection(self):
        if self.last_exported_selection:
            self.inputGridWidget.selected_points = self.last_exported_selection.copy()
            self.inputGridWidget.update_selected_points_plot()
            self.inputGridWidget.canvas.draw()
            self.updateChannelCount()
            print("Previous selection restored")
        else:
            print("No previous selection to restore")

    def exportChannels(self):
        selectedPoints = None
        try:
            selectedPoints = self.inputGridWidget.selected_points
        except Exception:
            print("No points selected")
            return
        if selectedPoints:
            self.last_exported_selection = selectedPoints.copy()
            chX = []
            chY = []
            for point in selectedPoints:
                x, y = point
                if (
                    round(y) % (self.rowSkipSpinBox.value() + 1) == 0
                    and round(x) % (self.colSkipSpinBox.value() + 1) == 0
                ):
                    chX.append(x)
                    chY.append(y)

            h5 = h5py.File(self.inputFileName, "r")
            parameters = self.parameter(h5)
            chsList = parameters["recElectrodeList"]
            xs, ys, idx = self.getChMap(chsList)
            h5.close()

            self.outputGridWidget.ax.clear()
            self.outputGridWidget.uploadedImage = (
                self.uploadedImage
            )  # Pass the uploadedImage to the ScatterPlot instance
            if self.uploadedImage is not None:
                height, width, _ = self.uploadedImage.shape
                aspect_ratio = width / height

                # Set the aspect ratio of the grid to match the image aspect ratio
                self.outputGridWidget.ax.set_aspect(aspect_ratio)

                # Display the image and set the x and y limits based on the image dimensions
                self.outputGridWidget.ax.imshow(
                    self.uploadedImage, extent=[0, width, height, 0]
                )

                # Scale the grid coordinates to match the image dimensions
                xs = [x * width / 64 for x in xs]
                ys = [y * height / 64 for y in ys]
                chX = [x * width / 64 for x in chX]
                chY = [y * height / 64 for y in chY]

                self.outputGridWidget.ax.set_xlim(0, width)
                self.outputGridWidget.ax.set_ylim(height, 0)
            else:
                self.outputGridWidget.ax.set_aspect("equal")
                self.outputGridWidget.ax.set_xlim(self.size[0], self.size[2])
                self.outputGridWidget.ax.set_ylim(self.size[2], self.size[3])

            # Plot the gray dots
            self.outputGridWidget.ax.scatter(
                xs, ys, c="grey", s=SIZE, alpha=0.1, marker=MARKER
            )

            # Plot the red dots on top with a higher zorder
            self.outputGridWidget.ax.scatter(
                chX, chY, c="red", s=SIZE, alpha=0.8, zorder=10, marker=MARKER
            )

            self.outputGridWidget.ax.set_xticks([])
            self.outputGridWidget.ax.set_yticks([])
            self.outputGridWidget.ax.invert_yaxis()
            self.outputGridWidget.canvas.draw()

            newChs = np.zeros(len(chX), dtype=[("Row", "<i2"), ("Col", "<i2")])
            for idx, (x, y) in enumerate(zip(chX, chY)):
                if self.uploadedImage is not None:
                    newChs[idx] = (np.int16(y * 64 / height), np.int16(x * 64 / width))
                else:
                    newChs[idx] = (np.int16(y), np.int16(x))

            newChs = newChs[np.lexsort((newChs["Col"], newChs["Row"]))]

            inputFilePath = os.path.dirname(self.inputFileName)
            inputFileName = os.path.basename(self.inputFileName)
            outputFileName = inputFileName.split(".")[0] + "_exportCh"
            outputFileNameBrw = outputFileName + ".brw"
            outputPath = os.path.join(inputFilePath, outputFileNameBrw)

            dset = self.writeCBrw(
                inputFilePath, outputFileName, inputFileName, parameters
            )
            dset.createNewBrw()
            dset.appendBrw(
                outputPath,
                parameters["nRecFrames"],
                newChs,
                parameters["samplingRate"],
                self.downsampleSpinBox.value(),
                self.startTimeSpinBox.value(),
                self.endTimeSpinBox.value(),
            )

            selected_row = self.dataTable.currentRow()
            if selected_row >= 0:
                status_item = self.dataTable.item(selected_row, 8)
                status_item.setText("Exported")
                status_item.setBackground(QColor("#386641"))

                select_button = self.dataTable.cellWidget(selected_row, 9)
                select_button.setText("Redo")
                select_button.setEnabled(True)

            print("Channels exported successfully")

    def runDownsampleExport(self):
        home_dir = os.path.expanduser("~")
        local_path = os.path.join(home_dir, "ChannelExtract")

        if not self.folderName:
            QMessageBox.information(
                self, "No Folder Uploaded", "Please upload a folder first."
            )
            return

        green_rows = [
            row
            for row in range(self.dataTable.rowCount())
            if self.dataTable.item(row, 8).text() == "Exported"
        ]

        green_row_file_names = [
            self.dataTable.item(row, 1).text() for row in green_rows
        ]

        if green_rows:
            reply = QMessageBox.question(
                self,
                "Run Downsample Export",
                f"Do you want to run the downsample export on {len(green_rows)} exported files?\nFiles:\n{', '.join(green_row_file_names)}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                folderName = os.path.normpath(self.folderName)
                driveLetter = os.path.splitdrive(folderName)[0]

                commands = [
                    f"cd {local_path}",
                    f"py export_to_brw.py {driveLetter} {folderName}",
                ]
                run_commands_in_terminal(commands)
        else:
            brwFiles = [f for f in os.listdir(self.folderName) if f.endswith(".brw")]
            exportChFiles = [f for f in brwFiles if f.__contains__("exportCh")]
            files_string = "\n".join(exportChFiles)
            if exportChFiles:
                reply = QMessageBox.question(
                    self,
                    "Run Downsample Export",
                    f"Do you want to run the downsample export on {len(exportChFiles)} previously exported files?\nFiles:\n{files_string}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    folderName = os.path.normpath(self.folderName)
                    driveLetter = os.path.splitdrive(folderName)[0]

                    commands = [
                        f"cd {local_path}",
                        f"py export_to_brw.py {driveLetter} {folderName}",
                    ]
                    run_commands_in_terminal(commands)
            else:
                QMessageBox.information(
                    self, "No Files Exported", "No files have been exported."
                )

    def parameter(self, h5):
        if self.typ == "bw4":
            parameters = {}
            parameters["Ver"] = "BW4"

            parameters["nRecFrames"] = h5["/3BRecInfo/3BRecVars/NRecFrames"][0]
            parameters["samplingRate"] = h5["/3BRecInfo/3BRecVars/SamplingRate"][0]
            parameters["recordingLength"] = (
                parameters["nRecFrames"] / parameters["samplingRate"]
            )
            parameters["signalInversion"] = h5["/3BRecInfo/3BRecVars/SignalInversion"][
                0
            ]  # depending on the acq version it can be 1 or -1
            # in uVolt
            parameters["maxUVolt"] = h5["/3BRecInfo/3BRecVars/MaxVolt"][0]
            # in uVolt
            parameters["minUVolt"] = h5["/3BRecInfo/3BRecVars/MinVolt"][0]
            parameters["bitDepth"] = h5["/3BRecInfo/3BRecVars/BitDepth"][
                0
            ]  # number of used bit of the 2 byte coding
            parameters["qLevel"] = (
                2 ^ parameters["bitDepth"]
            )  # quantized levels corresponds to 2^num of bit to encode the signal
            parameters["fromQLevelToUVolt"] = (
                parameters["maxUVolt"] - parameters["minUVolt"]
            ) / parameters["qLevel"]
            try:
                parameters["recElectrodeList"] = h5["/3BRecInfo/3BMeaStreams/Raw/Chs"][
                    :
                ]  # list of the recorded channels
                parameters["Typ"] = "RAW"
            except Exception:
                parameters["recElectrodeList"] = h5[
                    "/3BRecInfo/3BMeaStreams/WaveletCoefficients/Chs"
                ][:]
                parameters["Typ"] = "WAV"
            parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])

        else:
            if "Raw" in h5["Well_A1"].keys():
                json_s = json.loads(h5["ExperimentSettings"][0].decode("utf8"))
                parameters = {}
                parameters["Ver"] = "BW5"
                parameters["Typ"] = "RAW"
                parameters["nRecFrames"] = h5["Well_A1/Raw"].shape[0] // 4096
                parameters["samplingRate"] = json_s["TimeConverter"]["FrameRate"]
                parameters["recordingLength"] = (
                    parameters["nRecFrames"] / parameters["samplingRate"]
                )
                parameters["signalInversion"] = int(
                    1
                )  # depending on the acq version it can be 1 or -1
                parameters["maxUVolt"] = int(4125)  # in uVolt
                parameters["minUVolt"] = int(-4125)  # in uVolt
                # number of used bit of the 2 byte coding
                parameters["bitDepth"] = int(12)
                parameters["qLevel"] = (
                    2 ^ parameters["bitDepth"]
                )  # quantized levels corresponds to 2^num of bit to encode the signal
                parameters["fromQLevelToUVolt"] = (
                    parameters["maxUVolt"] - parameters["minUVolt"]
                ) / parameters["qLevel"]
                parameters["recElectrodeList"] = self.getChMap()[
                    :
                ]  # list of the recorded channels
                parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])
            else:
                json_s = json.loads(h5["ExperimentSettings"][0].decode("utf8"))
                parameters = {}
                parameters["Ver"] = "BW5"
                parameters["Typ"] = "WAV"

                samplingRate = h5.attrs["SamplingRate"]
                nChannels = len(h5["Well_A1/StoredChIdxs"])
                coefsTotalLength = len(h5["Well_A1/WaveletBasedEncodedRaw"])
                compressionLevel = h5["Well_A1/WaveletBasedEncodedRaw"].attrs[
                    "CompressionLevel"
                ]
                framesChunkLength = h5["Well_A1/WaveletBasedEncodedRaw"].attrs[
                    "DataChunkLength"
                ]
                coefsChunkLength = (
                    math.ceil(framesChunkLength / pow(2, compressionLevel)) * 2
                )
                numFrames = 0
                chIdx = 1
                coefsPosition = chIdx * coefsChunkLength
                while coefsPosition < coefsTotalLength:
                    length = int(coefsChunkLength / 2)
                    for i in range(compressionLevel):
                        length *= 2
                    numFrames += length
                    coefsPosition += coefsChunkLength * nChannels

                parameters["nRecFrames"] = numFrames
                parameters["recordingLength"] = numFrames / samplingRate

                parameters["samplingRate"] = json_s["TimeConverter"]["FrameRate"]
                parameters["signalInversion"] = int(
                    1
                )  # depending on the acq version it can be 1 or -1
                parameters["maxUVolt"] = int(4125)  # in uVolt
                parameters["minUVolt"] = int(-4125)  # in uVolt
                # number of used bit of the 2 byte coding
                parameters["bitDepth"] = int(12)
                parameters["qLevel"] = (
                    2 ^ parameters["bitDepth"]
                )  # quantized levels corresponds to 2^num of bit to encode the signal
                parameters["fromQLevelToUVolt"] = (
                    parameters["maxUVolt"] - parameters["minUVolt"]
                ) / parameters["qLevel"]
                parameters["recElectrodeList"] = self.getChMap()[
                    :
                ]  # list of the recorded channels
                parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])

        return parameters

    def getChMap(self, chsList=None):
        # Get channel map coordinates
        newChs = np.zeros(4096, dtype=[("Row", "<i2"), ("Col", "<i2")])
        for idx in range(4096):
            column = (idx // 64) + 1
            row = idx % 64 + 1
            if row == 0:
                row = 64
            if column == 0:
                column = 1
            newChs[idx] = (np.int16(row), np.int16(column))

        if chsList is None:
            return newChs[np.lexsort((newChs["Col"], newChs["Row"]))]
        else:
            Ys = []
            Xs = []
            idx = []
            for n, item in enumerate(chsList):
                Ys.append(item["Col"])
                Xs.append(item["Row"])
                idx.append(n)
            return Xs, Ys, idx

    def writeCBrw(self, path, name, template, parameters):
        dset = writeCBrw(path, name, template, parameters)
        return dset


class writeCBrw:
    def __init__(self, path, name, template, parameters):
        self.path = path
        self.fileName = name
        self.template = template
        self.description = parameters["Ver"]
        self.version = parameters["Typ"]
        self.brw = h5py.File(os.path.join(self.path, self.template), "r")
        self.samplingrate = parameters["samplingRate"]
        self.frames = parameters["nRecFrames"]
        self.signalInversion = parameters["signalInversion"]
        self.maxVolt = parameters["maxUVolt"]
        self.minVolt = parameters["minUVolt"]
        self.bitdepth = parameters["bitDepth"]
        self.chs = parameters["recElectrodeList"]
        self.QLevel = np.power(2, parameters["bitDepth"])
        self.fromQLevelToUVolt = (self.maxVolt - self.minVolt) / self.QLevel

    def createNewBrw(self):
        newName = os.path.join(self.path, self.fileName + ".brw")
        new = h5py.File(newName, "w")
        new.attrs.__setitem__("Description", self.description)
        new.attrs.__setitem__("Version", self.version)
        new.create_dataset("/3BRecInfo/3BRecVars/SamplingRate", data=[np.float64(100)])
        new.create_dataset(
            "/3BRecInfo/3BRecVars/NewSampling", data=[np.float64(self.samplingrate)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/NRecFrames", data=[np.float64(self.frames)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/SignalInversion",
            data=[np.float64(self.signalInversion)],
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/MaxVolt", data=[np.float64(self.maxVolt)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/MinVolt", data=[np.float64(self.minVolt)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/BitDepth", data=[np.float64(self.bitdepth)]
        )
        new.create_dataset("/3BRecInfo/3BMeaStreams/Raw/Chs", data=[self.chs])
        new.create_dataset("/3BRecInfo/3BRecVars/Ver", data=[self.description])
        new.create_dataset("/3BRecInfo/3BRecVars/Typ", data=[self.version])
        self.newDataset = new
        self.newDataset.close()

    def appendBrw(self, fName, frames, chs, fs, NewSampling, ss, st):
        brwAppend = h5py.File(fName, "a")
        del brwAppend["/3BRecInfo/3BRecVars/NewSampling"]
        try:
            del brwAppend["/3BRecInfo/3BMeaStreams/Raw/Chs"]
        except Exception:
            del brwAppend["/3BRecInfo/3BMeaStreams/WaveletCoefficients/Chs"]
        del brwAppend["/3BRecInfo/3BRecVars/NRecFrames"]
        del brwAppend["/3BRecInfo/3BRecVars/SamplingRate"]
        brwAppend.create_dataset("/3BRecInfo/3BMeaStreams/Raw/Chs", data=chs)
        brwAppend.create_dataset(
            "/3BRecInfo/3BRecVars/NRecFrames", data=[np.int64(frames)]
        )
        brwAppend.create_dataset(
            "/3BRecInfo/3BRecVars/SamplingRate", data=[np.float64(fs)]
        )
        brwAppend.create_dataset(
            "/3BRecInfo/3BRecVars/NewSampling", data=[np.float64(NewSampling)]
        )
        brwAppend.create_dataset(
            "/3BRecInfo/3BRecVars/startTime", data=[np.float64(ss)]
        )
        brwAppend.create_dataset("/3BRecInfo/3BRecVars/endTime", data=[np.float64(st)])
        brwAppend.close()

    def close(self):
        self.newDataset.close()
        self.brw.close()


def create_batch_file():
    home_dir = os.path.expanduser("~")

    channel_extract_path = os.path.join(home_dir, "ChannelExtract")

    script_path = os.path.join(channel_extract_path, "ChannelExtract.py")

    batch_content = f"""@echo off
    python "{script_path}"
    """

    batch_file_path = os.path.join(channel_extract_path, "ChannelExtract.bat")

    with open(batch_file_path, "w") as batch_file:
        batch_file.write(batch_content)

    print(f"Batch file created successfully: {batch_file_path}")
    return batch_file_path


def run_commands_in_terminal(commands):
    try:
        if sys.platform == "darwin":  # macOS
            script = "#!/bin/bash\n"
            script += "\n".join(commands)
            subprocess.Popen(
                [
                    "osascript",
                    "-e",
                    f'tell application "Terminal" to do script "{script}"',
                ]
            )
        elif sys.platform == "win32":  # Windows
            script = " & ".join(commands)
            subprocess.Popen(["start", "cmd", "/k", script], shell=True)
        else:  # Linux or other Unix-like systems
            script = "\n".join(commands)
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script])
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running commands: {str(e)}")
    except Exception as e:
        print(f"Error occurred: {str(e)}")


def make_silly_message():
    silly_messages = [
        "Update complete! Imma go ahead and restart the application for you. xoxo - Love, Jake",
        "*insert Norby's waaaaaaaa happy sound* Update complete! Restarting the application for you :D",
        "Enjoy your bug free app. Well. Mostly bug free. I mean, I tried. - Jake",
    ]
    message = np.random.choice(silly_messages)
    separator = "*" * len(message)
    output = [
        "echo.",
        f"echo {separator}",
        f"echo {message}",
        f"echo {separator}",
        "echo.",
    ]
    return output


def update_MEA_GUI():
    print("Updating MEA GUI...")
    repo_url = "https://github.com/jhnorby/Jake-Squared.git"

    home_dir = os.path.expanduser("~")

    local_path = os.path.join(home_dir, "Jake-Squared")

    try:
        # Don't check the hashes, just pull the latest changes
        if os.path.exists(local_path):
            subprocess.call(
                ["git", "-C", local_path, "pull"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.call(
                ["git", "clone", repo_url, local_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        print("MEA GUI update complete.")
    except subprocess.CalledProcessError as e:
        error_message = f"Error occurred during MEA GUI update: {str(e)}"
        print(error_message)
        QMessageBox.critical(None, "Update Error Womp Womp", error_message)


def check_for_updates():
    update_MEA_GUI()
    repo_url = "https://github.com/booka66/ChannelExtract.git"

    # Check if E: drive exists
    home_dir = os.path.expanduser("~")

    local_path = os.path.join(home_dir, "ChannelExtract")
    converter_path = os.path.join(local_path, "batch_convert.bat")

    try:
        remote_commit = (
            subprocess.check_output(
                ["git", "ls-remote", repo_url, "HEAD"], stderr=subprocess.PIPE
            )
            .decode("utf-8")
            .split()[0]
        )

        if os.path.exists(local_path):
            local_commit = (
                subprocess.check_output(
                    ["git", "-C", local_path, "rev-parse", "HEAD"],
                    stderr=subprocess.PIPE,
                )
                .decode("utf-8")
                .strip()
            )
        else:
            local_commit = ""

        if remote_commit != local_commit:
            reply = QMessageBox.question(
                None,
                "Update Available",
                "A new version is available :D Do you want to update?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                if os.path.exists(local_path):
                    subprocess.call(
                        ["git", "-C", local_path, "pull"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.call(
                        ["git", "clone", repo_url, local_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                batch_file_path = create_batch_file()
                initial_commands = [
                    f"cd {local_path}",
                    "pip install -r requirements.txt",
                    "echo Converting batch to exe...",
                    f"start {converter_path} {batch_file_path}",
                ]
                silly_message_commands = make_silly_message()
                kill_commands = [
                    "timeout /t 5 /nobreak",
                    f"start {batch_file_path}",
                    "taskkill /IM cmd.exe /F",
                ]
                commands = initial_commands + silly_message_commands + kill_commands
                run_commands_in_terminal(commands)
                sys.exit()
    except subprocess.CalledProcessError as e:
        error_message = f"Error occurred during update check: {str(e)}"
        print(error_message)
        QMessageBox.critical(None, "Update Error Womp Womp", error_message)
    except Exception as e:
        error_message = f"Error occurred during update check: {str(e)}"
        print(error_message)
        QMessageBox.critical(None, "Update Error Womp Womp", error_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    window = ChannelExtract()
    check_for_updates()

    sys.exit(app.exec_())
