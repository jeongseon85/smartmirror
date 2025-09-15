#!/usr/bin/env bash
set -euo pipefail

# Jetson Nano setup for this project (2025-09-05)
# - Use system OpenCV/PyQt via apt
# - Create venv that reuses system packages
# - Install minimal pip deps (no scikit-learn/scipy)
# - EasyOCR requires PyTorch (L4T). Install torch first, then pip install easyocr inside the venv.

echo "[1/5] apt update + base packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-opencv \
    gstreamer1.0-tools gstreamer1.0-plugins-{good,bad,ugly} \
    libqt5gui5 libqt5widgets5 libqt5x11extras5 libqt5svg5 \
    libopenblas-dev

echo "[2/5] create venv with system-site-packages"
python3 -m venv .venv --system-site-packages
source .venv/bin/activate

echo "[3/5] upgrade pip + install core deps (no sklearn/scipy)"
pip install --upgrade pip
pip install numpy==1.24.4 pillow colormath imutils

echo "[4/5] (Optional) Install PyTorch for Jetson (L4T) before EasyOCR."
echo "      After torch is installed and importable, run: pip install easyocr"
python - <<'PY'
import importlib.util
print("torch importable:", importlib.util.find_spec("torch") is not None)
print("cv2 from:", __import__("cv2").__file__)
PY

echo "[5/5] done. To run: source .venv/bin/activate && python3 main.py"
