Quick Start
===========

.. toctree::
   :maxdepth: 4
   :hidden:

   self


Installation
------------

There are two ways to install the application:

1. Downloading an installer for your operating system and following the instructions (recommended):

    - `Download <https://github.com/booka66/mea-gui/releases/latest/download/MEA_GUI_Windows.exe>`__ for Windows
    - `Download <https://github.com/booka66/mea-gui/releases/latest/download/MEA_GUI_MacOS.pkg>`__ for MacOS


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

.. note::
  The instructions for building from the source code assume that you have Python 3.11 installed on your system. 
  If you don't have it, you can download it from the `official website <https://www.python.org/downloads/release/python-3118/>`__.

Configuration
-------------
MATLAB
^^^^^^
Certain features of the application require MATLAB to be installed on your system. 
If you have MATLAB installed in a non-standard location, you can specify the path to the MATLAB executable in the configuration file. 
To do this, open the configuration file located at ``src/helpers/config.json`` and change the value of the ``matlab_path`` key to the path to the MATLAB executable on your system.
For example:

.. code-block:: json

    {
        "matlab_path": "C:/Program Files/MATLAB/R2021b/bin/matlab.exe"
    }

.. code-block:: json

    {
        "matlab_path": "/Applications/MATLAB_R2021b.app/bin/matlab"
    }

.. note::
  Luckily, the application will automatically detect the MATLAB installation on your system if it is installed in the default location.

.. note::
  If you cannot install MATLAB on your system, when using the application, make sure the ``Use c++`` option is checked before running an analysis.

Font
^^^^
Using the installer will automatically install the required font.
However, if you are installing the application manually or if the font installation failed, you will need to install the font yourself.
You can download the font `here <https://raw.githubusercontent.com/booka66/mea-gui/main/resources/fonts/HackNerdFontMono-Regular.ttf>`__.
Open the downloaded font file and click the "Install" button.

