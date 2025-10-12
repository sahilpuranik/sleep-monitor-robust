# Sleep Monitor

Monitors room conditions during sleep on Raspberry Pi. Detects anomalies in temperature, humidity, light, and sound.

## Hardware

- Raspberry Pi 3B+
- BME280 sensor (temp/humidity/pressure)
- TSL2591 light sensor (optional)
- INMP441 microphone (optional)

## Setup

```bash
git clone https://github.com/sahilpuranik/sleep-monitor-robust.git
cd sleep-monitor-robust
pip3 install -r requirements.txt
sudo raspi-config  # Enable I2C
```

## Usage

**Night 0 (Calibration):**
```bash
python3 init_db.py
python3 collect_bme280.py  # Run overnight
python3 build_baseline.py
```

**Night 1+ (Monitoring):**
```bash
export SMTP_USER="email@gmail.com"
export SMTP_PASS_APP="app_password"
export ALERT_TO="email@gmail.com"
export OPENAI_API_KEY="sk-..."  # optional

python3 run_detector.py
# Ctrl+C to stop and get email summary
```

## Config

Create `.env` from `env.example`:
```bash
SMTP_USER=email@gmail.com
SMTP_PASS_APP=app_password
ALERT_TO=email@gmail.com
OPENAI_API_KEY=sk-...
```