FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV GENICAM_GENTL64_PATH=/usr/lib/ids/cti

# 🧱 Installa dipendenze generiche: sistema, Qt, Python, ZeroMQ
RUN apt-get update && apt-get install apt-utils -y \
    wget curl gnupg lsb-release \
    udev usbutils libusb-1.0-0 \
    python3 python3-pip python3-dev \
    libqt5core5a libqt5gui5 libqt5widgets5 \
    libqt5quick5 libqt5x11extras5 qtbase5-dev \
    libqt5multimedia5 qml-module-qtquick-window2 \
    libudev-dev \
    qml-module-qtquick2 qtdeclarative5-dev \
    libatomic1 cmake g++ \
    qml-module-qtquick-dialogs \
    qml-module-qtquick-controls \
    qml-module-qtquick-layouts \
    qml-module-qt-labs-settings \
    qml-module-qt-labs-folderlistmodel \
    libzmq3-dev \
    wget curl gnupg2 unzip \
    libusb-1.0-0 \
    libgtk-3-0 \
    libgl1 \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 🐍 Installa pacchetti Python comuni (pip + zmq)
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install pyzmq

# 📦 Copia script IDS e avvia setup IDS
COPY sdk/ /sdk/
RUN chmod +rwx /sdk/entrypoint.sh && /sdk/entrypoint.sh

# 🎯 Copia gli script Python
COPY camera_listener.py /app/
COPY device_watcher.py /app/

# # ▶️ Comando finale
# CMD ["python3", "camera_listener.py"]
