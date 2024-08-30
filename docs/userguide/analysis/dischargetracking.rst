.. _discharge_propagation_tracking:

==============================
Discharge Propagation Tracking
==============================
Tracking the propagation of discharges is one of the more difficult tasks to complete with the GUI.
Given the complexity of the task, it may take the user some time to become familiar with the process.

Introduction
============
Before starting, it is important to understand what the discharge propagation tracking algorithm is doing behind the scenes.
This understanding will help the user better able to set and fine tune the parameters of the algorithm.
Admittedly, the algorithm is not perfect and may require some manual intervention to get the best results.

There are two main steps to the discharge propagation tracking algorithm:

  1. Discharge detection with a peak finding algorithm
  2. Clustering of detected discharges with a DBSCAN algorithm

While seemingly simple, each step has its own set of parameters that can greatly affect the final results.
With many different variables to consider and the nature of the data, it is difficult to provide a one-size-fits-all solution.
