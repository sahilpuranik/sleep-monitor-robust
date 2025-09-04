#!/bin/bash

# Sleep Monitor Setup Script
# Automates installation and initial configuration

set -e  # Exit on any error

echo "Sleep Monitor - Automated Setup"
echo "================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root"
   echo "Please run as regular user (pi)"
   exit 1
fi

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    echo "Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt install -y i2c-tools python3-pip python3-venv

# Enable I²C
echo "Enabling I²C interface..."
if ! grep -q "i2c_arm=on" /boot/config.txt; then
    echo "i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "I²C enabled in config.txt (reboot required)"
fi

# Check if I²C is already enabled
if sudo raspi-config nonint get_i2c | grep -q "0"; then
    echo "I²C is already enabled"
else
    echo "Enabling I²C via raspi-config..."
    sudo raspi-config nonint do_i2c 0
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv sleepmon_env
source sleepmon_env/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Test I²C detection
echo "Testing I²C sensor detection..."
if sudo i2cdetect -y 1 | grep -q "76"; then
    echo "BME280 sensor detected at address 0x76"
else
    echo "Warning: BME280 sensor not detected at address 0x76"
    echo "Please check your wiring:"
    echo "  SDA: GPIO2 (pin 3)"
    echo "  SCL: GPIO3 (pin 5)"
    echo "  3.3V power and ground"
    echo ""
    echo "Continue with setup? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Initialize database
echo "Initializing database..."
python3 Main.py init

# Create systemd service
echo "Setting up systemd service..."
sudo cp sleepmon.service /etc/systemd/system/
sudo sed -i "s|your.email@gmail.com|$USER@gmail.com|g" /etc/systemd/system/sleepmon.service
sudo sed -i "s|your-app-password|CHANGE_ME|g" /etc/systemd/system/sleepmon.service
sudo sed -i "s|alert.recipient@gmail.com|$USER@gmail.com|g" /etc/systemd/system/sleepmon.service

# Set permissions
echo "Setting file permissions..."
chmod +x Main.py
chmod +x *.py

# Create environment file
if [ ! -f .env ]; then
    echo "Creating environment file template..."
    cp env.example .env
    echo ""
    echo "Please edit .env file with your email configuration:"
    echo "  SMTP_USER=your.email@gmail.com"
    echo "  SMTP_PASS_APP=your-app-password"
    echo "  ALERT_TO=alert.recipient@gmail.com"
fi

# Setup complete
echo ""
echo "Setup complete!"
echo "==============="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your email configuration"
echo "2. Run calibration: python3 Main.py calibrate"
echo "3. Start monitoring: python3 Main.py monitor"
echo "4. Check status: python3 Main.py status"
echo ""
echo "Optional: Enable auto-startup:"
echo "  sudo systemctl enable sleepmon"
echo "  sudo systemctl start sleepmon"
echo ""
echo "For help: python3 Main.py help"
echo ""
echo "Note: I²C changes may require a reboot to take effect"
