#!/bin/bash
set -e

echo "Sleep Monitor Setup"

if [[ $EUID -eq 0 ]]; then
   echo "Don't run as root"
   exit 1
fi

echo "Installing packages..."
sudo apt update
sudo apt install -y i2c-tools python3-pip

echo "Enabling I2C..."
sudo raspi-config nonint do_i2c 0

echo "Installing Python deps..."
pip3 install -r requirements.txt

echo "Testing sensor..."
if sudo i2cdetect -y 1 | grep -q "76"; then
    echo "BME280 found"
else
    echo "Warning: BME280 not found at 0x76"
fi

echo "Init database..."
python3 init_db.py

if [ ! -f .env ]; then
    cp env.example .env
    echo "Edit .env with your email config"
fi

chmod +x *.py

echo ""
echo "Done. Next steps:"
echo "1. Edit .env"
echo "2. Run: python3 collect_bme280.py (overnight)"
echo "3. Run: python3 build_baseline.py"
echo "4. Run: python3 run_detector.py"
