# Migration Guide: LSTM to Robust Statistics

This guide helps you transition from the previous LSTM-based sleep monitoring system to the new robust statistical approach.

## Why Migrate?

The new system offers significant advantages:

- **Immediate Results**: No training time required
- **Better Reliability**: Statistical methods are predictable and stable
- **Faster Performance**: Minimal CPU usage, real-time response
- **Easier Maintenance**: No model retraining or validation needed
- **Simpler Debugging**: Clear statistical thresholds vs. black-box neural networks

## Migration Steps

### 1. Backup Existing Data

```bash
# Backup your existing LSTM system data
cp -r /path/to/old/system /path/to/backup/
cp sleep-climate-monitor.db /path/to/backup/  # if you have old database
```

### 2. Install New System

```bash
# Clone or download the new system
cd /home/pi/
git clone https://github.com/sahilpuranik/sleep-climate-monitor.git
cd sleep-climate-monitor

# Install dependencies
pip3 install --break-system-packages -r requirements.txt
```

### 3. Initialize New System

```bash
# Initialize the new database and system
python3 Main.py init
```

### 4. Run Calibration

```bash
# Collect baseline data (recommended: 8+ hours overnight)
python3 Main.py calibrate

# Let this run overnight to collect your room's normal patterns
# Press Ctrl+C when you have enough data
```

### 5. Start Monitoring

```bash
# Configure email alerts (optional)
export SMTP_USER="your.email@gmail.com"
export SMTP_PASS_APP="your-app-password"
export ALERT_TO="alert.recipient@gmail.com"

# Start monitoring
python3 Main.py monitor
```

## Key Differences

### Old LSTM System
- Required extensive training data (weeks of data)
- Complex model training and validation
- Unpredictable behavior in edge cases
- Heavy computational overhead
- Required periodic retraining

### New Statistical System
- Works immediately after calibration (8+ hours)
- Clear, interpretable thresholds
- Predictable and stable behavior
- Minimal computational overhead
- Self-adjusting baselines

## Data Migration

### Can I Use My Old Data?

The new system uses a different approach, but you can:

1. **Export old data** for analysis:
   ```bash
   # If you have old CSV files
   # The new system will create its own database structure
   ```

2. **Compare patterns** between old and new systems
3. **Keep old data** for historical analysis

### New Data Structure

The new system creates:
- `sleepmon.db` - SQLite database with WAL mode
- Tables: `readings`, `minute_stats`, `config`, `anomalies`
- Automatic indexing for performance

## Configuration Changes

### Old System
- Model parameters in `DSmodel/` folder
- Training scripts and validation
- Complex configuration files

### New System
- Simple environment variables
- Statistical thresholds in database
- Command-line interface via `Main.py`

## Testing the Migration

### 1. Verify Sensor Connection
```bash
# Check I²C detection
sudo i2cdetect -y 1
# Should show BME280 at address 0x76
```

### 2. Test Email Configuration
```bash
# Test email setup
python3 Main.py test-email
```

### 3. Check System Status
```bash
# Verify system readiness
python3 Main.py status
```

## Troubleshooting Migration

### Common Issues

1. **Old Dependencies Conflict**
   ```bash
   # Remove old packages if needed
   pip3 uninstall tensorflow keras
   pip3 install --break-system-packages -r requirements.txt
   ```

2. **Database Permission Issues**
   ```bash
   # Fix permissions
   sudo chown -R pi:pi sleepmon.db*
   ```

3. **Sensor Not Detected**
   ```bash
   # Check I²C is enabled
   sudo raspi-config
   # Interface Options > I²C > Enable
   ```

### Rollback Plan

If you need to revert:

1. **Stop new system**: `Ctrl+C` if running
2. **Restore backup**: Copy back your old system
3. **Restart old system**: Use your previous LSTM setup

## Performance Comparison

| Metric | LSTM System | New Statistical System |
|--------|-------------|------------------------|
| **Startup Time** | 30+ seconds | <5 seconds |
| **Memory Usage** | 200-500 MB | <50 MB |
| **CPU Usage** | 15-30% | <5% |
| **Training Required** | Yes (weeks) | No |
| **Reliability** | Variable | High |
| **Maintenance** | Complex | Simple |

## Support

### Getting Help

1. **Check system status**: `python3 Main.py status`
2. **Review logs**: Check console output for errors
3. **Test components**: Use individual test commands
4. **Documentation**: See `README.md` for detailed information

### Community

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions and share experiences
- Wiki: Community-maintained documentation

## Conclusion

The migration to the robust statistical system provides:
- **Better performance** on Raspberry Pi hardware
- **Improved reliability** for long-term monitoring
- **Simplified maintenance** and operation
- **Immediate results** without training delays

The new system maintains all the core functionality of anomaly detection while providing a more robust and efficient foundation for sleep environment monitoring.

---

**Need Help?** Open an issue on GitHub or check the troubleshooting section in the README.
