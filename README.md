# Sleep Monitor (Raspberry Pi)

A lightweight, local-only sleep environment monitoring system that runs on Raspberry Pi to track room conditions during sleep. Uses BME280 sensor over I²C to monitor temperature, humidity, and pressure with robust statistical anomaly detection.

## Features

- **Calibration Mode (Night 0)**: Build personalized baseline thresholds from overnight data collection
- **Monitoring Mode (Nights 1+)**: Real-time anomaly detection with email alerts
- **Robust Statistics**: Uses Median Absolute Deviation (MAD) and z-scores for reliable detection
- **SQLite Storage**: Efficient local database (~4 MB per 8 hours, ~30k readings)
- **Configurable Thresholds**: Customizable detection rules and cooldown periods
- **Email Alerts**: Gmail integration with App Password authentication
- **AI-Enhanced Alerts**: Optional OpenAI integration for human-readable explanations

## Hardware Requirements

- Raspberry Pi 3B+ (or compatible)
- BME280 sensor module
- I²C connection (SDA=GPIO2, SCL=GPIO3)

## Quick Start

### Setup
```bash
git clone https://github.com/sahilpuranik/sleep-monitor-robust.git
cd sleep-monitor-robust
pip3 install -r requirements.txt
sudo raspi-config  # Enable I²C interface
```

### Calibration (Night 0)
```bash
python3 init_db.py
python3 collect_bme280.py   # Leave running overnight
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
```

## Alert Examples

### Raw Format
```
TEMP_F anomaly, Z-score 7.61, value=81.9°F (baseline=78.0°F ± 0.4°F)
```

### AI-Enhanced Format
```
Your room temperature has risen to 81.9°F, unusually high compared to your normal baseline.
This may be caused by heating, poor ventilation, or a window being left open.
Consider adjusting airflow or checking HVAC settings.
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
├── collect_bme280.py      # Night 0 data collection
├── build_baseline.py      # Baseline computation
├── run_detector.py        # Nights 1+ monitoring
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
```

## Testing

Test email configuration:
```bash
python3 test_email.py
```

Test LLM integration:
```bash
python3 test_llm.py
```

## License

MIT License - see LICENSE file for details.

## Contributing

This is a personal project focused on sleep health monitoring. Feel free to fork and adapt for your own use.