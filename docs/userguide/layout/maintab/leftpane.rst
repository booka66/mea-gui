=========
Left Pane
=========
In this region of the application, the user can visualize the trace activity on a grid of cells or on a raster plot.

.. _mea_grid:

MEA Grid
========
Upon loading a ``.brw`` file and running either :ref:`quick_view` or :ref:`run_analysis`, the multi-electrode array (MEA) grid will be populated with active channels displayed in a light gray shade.
Hovering over a channel or clicking a channel will display a tooltip containing the channel's location in ``(row, column)`` format.
The user may select an active cell by clicking on it, which will highlight the currently selected cell with an outline.
With a cell selected, the user may then press the ``1``, ``2``, ``3``, or ``4`` key to plot the trace activity of the selected cell in the corresponding trace plot in the right pane.
Once a cell is plotted, a shape will appear on the MEA grid to indicate the selected cell, which can also be seen on the corresponding trace plot.

Context Menus
-------------
There are many useful features and settings that can be accessed by either right-clicking on the MEA grid or by using the :ref:`menu_bar` at the top of the application.
These features include the ability to change visual settings of the MEA grid, to save the current grid state as an image, or to save the grid animation as a video.

.. _raster_plot:

Raster Plot
===========
The raster plot is a visual representation of the spike activity of the cells on the MEA grid.
Each row of the raster plot corresponds to a cell on the MEA grid, and each dot represents a spike event.
The threshold for a spike even can be changed by clicking the ``Edit Raster Settings`` button near the bottom of the left pane.
When the trace exceeds the spike threshold, a spike event is recorded in the raster plot.

Blue dots represent spike events that occurred during a seizure event, while orange dots represent spike evens that occurred during a status epilepticus (SE) event.
Black dots represent spike events that occurred outside of a seizure or SE event.

Unlike the trace plots in the right pane, the raster plot's mouse interaction mode is set to pan by default. The controls are as follows:

  - ``Left click`` and drag to pane
  - ``Right click`` and drag to zoom

    - Dragging left and right zooms in/out horizontally
    - Dragging up and down zooms in/out vertically

  - ``Scroll wheel`` to zoom in/out
  - ``Left click`` on a spike event to seek the playback to that event's time

    - This also selects the corresponding cell on the MEA grid and can be plotted in the trace plot by pressing the ``1``, ``2``, ``3``, or ``4`` key
  
  - Hover over a spike event to display the event's channel and timestamp

.. _row_order:

Row Order
---------
Right-clicking on the raster plot will display a context menu with options to change the order of the rows in the raster plot.
By default, the raster plot will display the active channels in the order that they appear on the MEA grid from left to right, top to bottom.
However, assuming that the user has run an analysis, she/he may choose to sort the rows of the plot in three ways:

  - By the order of entrance into an SE event
  - By the order of entrance into a seizure event
  - By clustering the cells based on similar entrance times into an SE event

Spatial Groups
--------------
Sometimes it may be helpful to group the raster plot by spatial regions of the MEA grid (e.g. hippocampus and neocortex).
To do this, the user may click the ``Create Groups`` button near the bottom of the left pane, which will open a new window in which she/he can lasso select channels to group together.
The controls for lasso selecting are as follows:

  - ``Left click`` and drag to draw a lasso
    
    - Upon releasing the left click, the user may add to the current selection by simply drawing another lasso

  - ``c`` key to clear the current selection
  - ``z`` key to undo the last selection
  - ``Shift`` + ``z`` to redo undone changes
  - ``Enter`` key to confirm the selection and create a group

    - This can also be done by clicking the ``Save Group`` button

  - ``Confrim`` button to confirm all groups and close the window

.. tip::
   When clustering by entrance into an SE event or creating groups, the user may toggle the color mode of the raster plot to display the clusters/groups in different colors by clicking the ``Toggle Color Mode`` button.

After grouping the channels, the tooltip will now display the group name in addition to the other information. To see useful information/statistics about the groups, the user may switch from the ``Main`` tab to the ``Stats`` tab.
