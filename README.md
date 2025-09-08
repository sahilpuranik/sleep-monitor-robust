# Sleep Monitor (Raspberry Pi)

A comprehensive, local-only sleep environment monitoring system that runs on Raspberry Pi to track room conditions during sleep. Supports multiple sensors including BME280 (temperature/humidity/pressure), TSL2591 (light), and INMP441 (sound) with robust statistical anomaly detection and batch email reporting.

## Features

- **Multi-Sensor Support**: BME280 (temp/humidity/pressure), TSL2591 (light), INMP441 (sound)
- **Calibration Mode (Night 0)**: Build personalized baseline thresholds from overnight data collection
- **Monitoring Mode (Nights 1+)**: Real-time anomaly detection with batch email reporting
- **Robust Statistics**: Uses Median Absolute Deviation (MAD) and z-scores for reliable detection
- **SQLite Storage**: Efficient local database with support for all sensor types
- **Configurable Thresholds**: Customizable detection rules and cooldown periods
- **Batch Email Alerts**: Single comprehensive email at session end (Ctrl+C)
- **AI-Enhanced Alerts**: Optional OpenAI integration for human-readable explanations
- **Backward Compatibility**: Works with any combination of available sensors

## Hardware Requirements

- Raspberry Pi 3B+ (or compatible)
- **BME280 sensor module** (temperature, humidity, pressure)
- **TSL2591 light sensor** (optional - ambient light levels)
- **INMP441 microphone** (optional - sound intensity)
- I²C connection (SDA=GPIO2, SCL=GPIO3)
- I²S connection for microphone (BCLK=GPIO18, WS=GPIO19, DIN=GPIO20)

## Quick Start

### Setup
```bash
git clone https://github.com/sahilpuranik/sleep-monitor-robust.git
cd sleep-monitor-robust
pip3 install -r requirements.txt
sudo raspi-config  # Enable I²C and I²S interfaces
```

### Calibration (Night 0)
```bash
python3 init_db.py

# Option 1: Collect from all available sensors
python3 collect_bme280.py   # Leave running overnight

# Option 2: Collect from individual sensors (optional)
python3 collect_tsl2591.py  # Light sensor only
python3 collect_inmp441.py  # Microphone only

python3 build_baseline.py
```

### Monitoring (Nights 1+)
```bash
export SMTP_USER="your_email@gmail.com"
export SMTP_PASS_APP="your_app_password"
export ALERT_TO="your_email@gmail.com"

# Optional: AI-enhanced alerts
export OPENAI_API_KEY="sk-..."

python3 run_detector.py
# Press Ctrl+C to stop and receive batch email summary
```

## Alert Examples

### Batch Email Summary (Ctrl+C)
```
SLEEP MONITOR NIGHT SUMMARY

Time: 2024-01-15 07:30:00 UTC
Total Anomalies Detected: 3

1. TEMP_F ANOMALY
   Time: 2024-01-15T02:15:30Z
   Value: 81.9
   Rule: robust_z_score
   Details: Z-score: 7.61 (threshold: 6.0)

2. LUX ANOMALY
   Time: 2024-01-15T06:45:12Z
   Value: 1250.5
   Rule: guardrail
   Details: Value 1250.5 lux outside range [0, 1000] lux

3. SOUND_RMS ANOMALY
   Time: 2024-01-15T03:22:45Z
   Value: 45.2
   Rule: robust_z_score
   Details: Z-score: 8.3 (threshold: 6.0)
```

### AI-Enhanced Format
```
Your sleep environment had 3 anomalies tonight. Temperature rose to 81.9°F around 2:15 AM, 
likely due to heating or poor ventilation. Light levels spiked to 1250 lux at 6:45 AM, 
suggesting early morning sunlight or artificial lighting. Sound levels increased to 45.2 RMS 
at 3:22 AM, possibly from external noise or movement.
```

## System Design

- **Lightweight**: Simple Python scripts, no heavy ML models
- **Reliable**: Optimized for 24/7 runtime on Raspberry Pi
- **Robust**: Graceful error handling, WAL database mode
- **Modular**: Easy to run manually or integrate with systemd
- **Minimal Dependencies**: Works with or without OpenAI integration

## File Structure

```
sleep-monitor-robust/
├── Main.py                 # Unified command-line interface
├── init_db.py             # Database initialization
├── collect_bme280.py      # BME280 data collection
├── collect_tsl2591.py     # TSL2591 light sensor collection
├── collect_inmp441.py     # INMP441 microphone collection
├── build_baseline.py      # Baseline computation for all sensors
├── run_detector.py        # Multi-sensor monitoring with batch alerts
├── llm_utils.py           # OpenAI integration
├── email_utils.py         # Email alert system
├── db_utils.py            # Database operations
├── stats_utils.py         # Statistical analysis
├── schema.sql             # Database schema
├── requirements.txt       # Python dependencies
├── env.example            # Environment variables template
├── test_llm.py            # LLM integration testing
└── setup.sh               # Automated setup script
```

## Configuration

Copy `env.example` to `.env` and configure:

```bash
# Required for email alerts
SMTP_USER=your.email@gmail.com
SMTP_PASS_APP=your_app_password
ALERT_TO=alert.recipient@gmail.com

# Optional for AI-enhanced alerts
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional threshold customization
ROBUST_Z_THRESHOLD=6
TEMP_ROC_LIMIT=3
HUMIDITY_ROC_LIMIT=8
LUX_ROC_LIMIT=100
SOUND_ROC_LIMIT=10
```

## Multi-Sensor Support

The system supports three types of sensors with graceful fallback:

### BME280 (Required)
- **Temperature**: Fahrenheit readings with anomaly detection
- **Humidity**: Relative humidity percentage monitoring  
- **Pressure**: Atmospheric pressure tracking

### TSL2591 (Optional)
- **Lux**: Ambient light level measurements
- **Full Spectrum**: Visible light intensity
- **Infrared**: IR light detection

### INMP441 (Optional)
- **Sound RMS**: Audio amplitude as proxy for sound intensity
- **8kHz Sampling**: High-quality audio capture
- **I²S Interface**: Digital audio processing

### Backward Compatibility
- System works with any combination of available sensors
- Missing sensors are gracefully handled with warnings
- Existing BME280-only setups continue to work unchanged

## Testing

Test email configuration:
```bash
python3 test_email.py
```

Test LLM integration:
```bash
python3 test_llm.py
```

Test individual sensors:
```bash
python3 collect_tsl2591.py  # Test light sensor
python3 collect_inmp441.py  # Test microphone
```

## License

MIT License - see LICENSE file for details.

## Contributing

This is a personal project focused on sleep health monitoring. Feel free to fork and adapt for your own use.