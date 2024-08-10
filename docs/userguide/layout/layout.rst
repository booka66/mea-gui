==================
Application Layout
==================

Menu Bar
========

File
----
Contains actions regarding opening and saving files.

Open File
~~~~~~~~~
This is the main entry point for starting a new analysis. 
Clicking it will open a file selection dialog where the user can select ``.brw`` files. 
Upon selection, the application will search for an image associated with the recording.
If it doesn't find one, the user must manually select an image.

.. danger::

   Double check the supported image files and the logic for finding an image based on the recording.

Save MEA as Video
~~~~~~~~~~~~~~~~~
Opens a video editor dialog where the user can save the MEA grid as a video.

.. seealso::

   Video Editor Dialog

Save MEA as PNG
~~~~~~~~~~~~~~~
Opens up a file dialog where the user can save the MEA grid as a PNG.

.. tip::

   Left clicking on the MEA grid pulls up a context menu with the option to save the MEA as a PNG or a video.

Save Channel Plots 
~~~~~~~~~~~~~~~~~~
Opens up a file dialog where the user can save all or certain channels plots as a PNG or SVG. It is requisite to have at least one channel plotted to enable this action.

If desired, the user can hide the red playheads by checking or unchecking the box in the dialog.

Scale refers to the size of the saved image. The default is 4. The larger the scale, the larger the file size and longer the save time.

Save MEA with Channel Plots
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Opens up a file dialog where the user can save the MEA grid with channel plots as a PNG or SVG.

Edit
----

Set Peak Settings
~~~~~~~~~~~~~~~~~
Hovering over this action displays a window containing parameters used for a peak finding algorithm. Blah blah blah.

Set Spectrogram Settings
~~~~~~~~~~~~~~~~~~~~~~~~

Set DBSCAN Settings
~~~~~~~~~~~~~~~~~~~

.. seealso::

   TODO: Link to page explaining discharge propagation tracking.

View
----
Each of the following actions toggles the visibility of the corresponding element.

Legend
~~~~~~
The legend appears to the left of the MEA grid and displays a very simple explanation of the colors used in the MEA grid's cells.

Spread Lines
~~~~~~~~~~~~
Spread lines highlight the propagation of the detected events. 
Pink lines are dedicated to the spread of seizures, while darker orange lines display the spread of SE events.

Detected Events
~~~~~~~~~~~~~~~
Show/hide the detected events on the MEA grid.

False Color Map
~~~~~~~~~~~~~~~
Show/hide the false color map on the MEA grid.

.. note::

    By default, both the detected events and the false color map are visible, so the colors blend together.

Mini-map
~~~~~~~~

Playheads
~~~~~~~~~

Anti-aliasing
~~~~~~~~~~~~~

Seizure Regions
~~~~~~~~~~~~~~~

Spectrograms
~~~~~~~~~~~~

Help
----

Main Tab
========

Left Pane
---------

MEA Grid
~~~~~~~~

Raster Plot
~~~~~~~~~~~

Right Pane
----------

Trace Plots
~~~~~~~~~~~

Control Panel
~~~~~~~~~~~~~

Stats Tab
=========



