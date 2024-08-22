=========
Left Pane
=========

In this region of the application, the user can visualize the trace activity on a grid of cells or on a raster plot.

MEA Grid
========
Upon loading a ``.brw`` file and running either :ref:`quick_view` or :ref:`run_analysis`, the multi-electrode array (MEA) grid will be populated with active channels displayed in a light gray shade.
Hovering over a channel or clicking a channel will display a tooltip containing the channel's location in ``(row, column)`` format.
The user may select an active cell by clicking on it, which will highlight the currently selected cell with an outline.
With a cell selected, the user may then press the ``1``, ``2``, ``3``, or ``4`` key to plot the trace activity of the selected cell in the corresponding :ref:`trace_plot` in the right pane.
Once a cell is plotted, a shape will appear on the MEA grid to indicate the selected cell, which can also be seen on the corresponding trace plot.
