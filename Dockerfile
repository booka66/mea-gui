FROM python:3.11-slim-buster

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    qt5-default \
    libqt5gui5 \
    libqt5core5a \
    libqt5dbus5 \
    qttools5-dev-tools \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libportaudio2 \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Upgrade pip, install numpy, then other requirements including PyQt5 and PyInstaller
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir --config-settings --confirm-license= --verbose pyqt5 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyinstaller

# Copy the rest of your application
COPY . .

# Command to run PyInstaller
CMD ["pyinstaller", "--noconfirm", "--onedir", "--windowed", "./main.py", "--add-data", "./SzDetectCat.m:.", "--add-data", "./save_channel_to_mat.m:.", "--add-data", "./getChs.m:.", "--add-data", "./get_cat_envelop.m:.", "--additional-hooks-dir", "./hooks", "--add-data", "./*.m:."]
