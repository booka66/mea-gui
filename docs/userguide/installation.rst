.. _installation:

Installation
============

There are two ways to install the application:

1. Downloading an installer for your operating system and following the instructions (recommended):

    - `Download <https://github.com/booka66/mea-gui/releases/latest/download/MEA_GUI_Windows.exe>`__ for Windows
    - `Download <https://github.com/booka66/mea-gui/releases/latest/download/MEA_GUI_MacOS_arm64.pkg>`__ for MacOS (Apple Silicon)
    - `Download <https://github.com/booka66/mea-gui/releases/latest/download/MEA_GUI_MacOS_x86_64.pkg>`__ for MacOS (Intel)

    .. note::
      The installers are not signed, so you may need to allow the installation in the system settings. On Windows, it may be flagged as a potential threat, but choose to keep it anyway.


2. Manually from the source code:

    - Clone the repository and navigate to the project directory:
        .. code-block:: bash

          git clone https://github.com/booka66/mea-gui.git
          cd mea-gui

    - Create a virtual environment:
        .. code-block:: bash

          python -m venv mea_env

    - Activate the virtual environment:
        - Windows:

        .. code-block:: bash

          mea_env/Scripts/activate

        - MacOS:

        .. code-block:: bash

          source mea_env/bin/activate

    - Install the dependencies:
        .. code-block:: bash

          pip install -r src/helpers/update/requirements.txt

    - Run the application:
        .. code-block:: bash

          python src/main.py

.. important::
  The instructions for building from the source code assume that you have Python 3.10.9 installed on your system. 
  If you don't have it, you can download it from the `official website <https://www.python.org/downloads/release/python-3109/>`__.

.. note::
  Some algorithms have the option of using a MATLAB implementation. If you want to use them, you need to have MATLAB installed on your system, build from source, and use pip to install the ``matlab`` and ``matlabengine`` packages. Note that you'll need to download the correct version of matlabengine to work with your MATLAB installation.


