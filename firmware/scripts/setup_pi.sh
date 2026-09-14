#!/usr/bin/env bash
# Open Walking Safety Helmet - Raspberry Pi OS Bookworm (64-bit) setup.
# Run from the firmware directory as the normal user (not root):  bash scripts/setup_pi.sh
# Options:  --no-service   do not install/enable the systemd service
#           --ocr          also install the optional OCR package (RapidOCR)
set -euo pipefail

FIRMWARE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
INSTALL_SERVICE=1
WITH_OCR=0
for arg in "$@"; do
  case "$arg" in
    --no-service) INSTALL_SERVICE=0 ;;
    --ocr) WITH_OCR=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run as your normal user; the script uses sudo where needed." >&2
  exit 1
fi

echo "==> Installing system packages"
sudo apt-get update
sudo apt-get install -y \
  python3-venv python3-pip python3-dev \
  python3-picamera2 python3-libcamera \
  python3-lgpio python3-gpiozero \
  espeak-ng alsa-utils \
  i2c-tools \
  bluez bluez-tools

echo "==> Enabling I2C (400 kHz) and the camera"
sudo raspi-config nonint do_i2c 0
CONFIG_TXT=/boot/firmware/config.txt
[[ -f "$CONFIG_TXT" ]] || CONFIG_TXT=/boot/config.txt
if ! grep -q "i2c_arm_baudrate=400000" "$CONFIG_TXT"; then
  echo "dtparam=i2c_arm=on,i2c_arm_baudrate=400000" | sudo tee -a "$CONFIG_TXT" >/dev/null
fi
if ! grep -q "^camera_auto_detect=1" "$CONFIG_TXT"; then
  echo "camera_auto_detect=1" | sudo tee -a "$CONFIG_TXT" >/dev/null
fi
sudo usermod -aG gpio,i2c,video,audio,bluetooth "$RUN_USER" || true

echo "==> Creating virtual environment (with system site packages for picamera2/libcamera)"
cd "$FIRMWARE_DIR"
python3 -m venv --system-site-packages .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
# Keep the apt numpy (picamera2/simplejpeg are built against it); install a headless OpenCV
# new enough for YuNet 2023mar (>= 4.8). Bookworm's apt python3-opencv (4.6) is too old.
echo "numpy<2" > /tmp/owsh-constraints.txt
python -m pip install -c /tmp/owsh-constraints.txt "opencv-python-headless>=4.10,<5"
python -m pip install -c /tmp/owsh-constraints.txt -e ".[pi,ble]"
if [[ "$WITH_OCR" -eq 1 ]]; then
  python -m pip install -c /tmp/owsh-constraints.txt -e ".[ocr]"
fi

echo "==> Downloading models"
python -m owsh.tools.download_models

echo "==> Self-test"
python -m pytest -q || echo "WARNING: some tests failed - check before relying on the helmet"

if [[ "$INSTALL_SERVICE" -eq 1 ]]; then
  echo "==> Installing systemd service"
  sed -e "s|@USER@|$RUN_USER|g" -e "s|@FIRMWARE_DIR@|$FIRMWARE_DIR|g" systemd/owsh.service \
    | sudo tee /etc/systemd/system/owsh.service >/dev/null
  sudo install -m 0644 systemd/owsh-bt-agent.service /etc/systemd/system/owsh-bt-agent.service
  # Safe shutdown (B1 + B3 held 5 s) runs "systemctl poweroff" as the service user.
  echo "$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff" \
    | sudo tee /etc/sudoers.d/owsh-poweroff >/dev/null
  sudo chmod 0440 /etc/sudoers.d/owsh-poweroff
  sudo visudo -cf /etc/sudoers.d/owsh-poweroff
  sudo systemctl daemon-reload
  sudo systemctl enable owsh-bt-agent.service owsh.service
  echo "Services enabled. They start after reboot, or now with: sudo systemctl start owsh-bt-agent owsh"
fi

cat <<EOF

Done. Next steps:
  1. Reboot (I2C, camera and group membership):  sudo reboot
  2. Check the I2C bus:  i2cdetect -y 1   -> expect 0x10 (TF-Luna), 0x68 (MPU-6050)
  3. Change the DOWN TF-Luna address once (only that sensor connected):
       .venv/bin/python -m owsh.tools.tfluna_addr --from 0x10 --to 0x11
  4. Logs:  journalctl -u owsh -f
EOF
