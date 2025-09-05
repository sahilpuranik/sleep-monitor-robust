#!/usr/bin/env python3
"""
Sleep Monitor Detector (Nights 1+)
Continuously monitors environment and detects anomalies
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import DatabaseManager
from stats_utils import (
    celsius_to_fahrenheit, 
    calculate_minute_stats, 
    detect_anomalies,
    aggregate_readings_to_minutes
)
from email_utils import EmailAlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SleepMonitorDetector:
    def __init__(self, db_path: str = "sleepmon.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        self.email_manager = EmailAlertManager()
        self.running = False
        self.sensor = None
        self.reading_count = 0
        self.start_time = None
        
        # Anomaly tracking
        self.last_alert_times = defaultdict(str)
        self.anomaly_count = 0
        
        # Rolling window for anomaly detection (5 minutes)
        self.rolling_window_minutes = 5
        self.reading_buffer = []
        
        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def initialize_sensor(self):
        """Initialize BME280 sensor"""
        try:
            import board
            import busio
            from adafruit_bme280 import basic as adafruit_bme280
            
            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize BME280 sensor
            self.sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
            
            # Set sensor configuration for high accuracy
            self.sensor.sea_level_pressure = 1013.25
            self.sensor.mode = adafruit_bme280.MODE_NORMAL
            self.sensor.standby_period = adafruit_bme280.STANDBY_TC_500
            self.sensor.iir_filter = adafruit_bme280.IIR_FILTER_X16
            self.sensor.overscan_pressure = adafruit_bme280.OVERSCAN_X16
            self.sensor.overscan_humidity = adafruit_bme280.OVERSCAN_X1
            self.sensor.overscan_temperature = adafruit_bme280.OVERSCAN_X2
            
            logger.info("BME280 sensor initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import BME280 libraries: {e}")
            logger.error("Make sure you have installed: pip3 install adafruit-circuitpython-bme280")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize BME280 sensor: {e}")
            return False
    
    def read_sensor(self):
        """Read current sensor values"""
        try:
            if not self.sensor:
                return None
            
            # Read sensor values
            temp_c = self.sensor.temperature
            humidity = self.sensor.relative_humidity
            pressure = self.sensor.pressure
            
            # Convert temperature to Fahrenheit
            temp_f = celsius_to_fahrenheit(temp_c)
            
            return {
                'temp_f': temp_f,
                'humidity': humidity,
                'pressure': pressure
            }
            
        except Exception as e:
            logger.error(f"Error reading sensor: {e}")
            return None
    
    def store_reading(self, reading):
        """Store sensor reading in database"""
        try:
            # Generate UTC timestamp
            ts_utc = datetime.now(timezone.utc).isoformat()
            
            # Store in database
            self.db.insert_reading(
                ts_utc=ts_utc,
                temp_f=reading['temp_f'],
                humidity=reading['humidity'],
                pressure=reading['pressure']
            )
            
            # Add to rolling buffer
            self.reading_buffer.append((ts_utc, reading['temp_f'], reading['humidity'], reading['pressure']))
            
            # Keep only last 5 minutes of readings
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=self.rolling_window_minutes)
            self.reading_buffer = [
                reading for reading in self.reading_buffer
                if datetime.fromisoformat(reading[0].replace('Z', '+00:00')) > cutoff_time
            ]
            
            self.reading_count += 1
            
        except Exception as e:
            logger.error(f"Error storing reading: {e}")
    
    def get_baseline_config(self):
        """Get baseline configuration from database"""
        try:
            config = {}
            config_keys = [
                'baseline_temp_f_med', 'baseline_temp_f_mad', 'baseline_temp_f_std',
                'baseline_hum_med', 'baseline_hum_mad', 'baseline_hum_std',
                'robust_z_threshold', 'temp_roc_limit', 'humidity_roc_limit',
                'temp_min', 'temp_max', 'humidity_min', 'humidity_max', 'cooldown_minutes'
            ]
            
            for key in config_keys:
                value = self.db.get_config(key)
                if value:
                    config[key] = value
            
            # Check if we have baseline data
            if 'baseline_temp_f_med' not in config:
                logger.error("No baseline configuration found. Please run 'python3 build_baseline.py' first.")
                return None
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting baseline configuration: {e}")
            return None
    
    def detect_anomalies_in_window(self):
        """Detect anomalies in the current rolling window"""
        try:
            if len(self.reading_buffer) < 10:  # Need at least 10 readings for meaningful analysis
                return []
            
            # Get baseline configuration
            config = self.get_baseline_config()
            if not config:
                return []
            
            # Create baseline stats from current window
            baseline_stats = {
                'temp_f_med': float(config.get('baseline_temp_f_med', 0)),
                'temp_f_mad': float(config.get('baseline_temp_f_mad', 0)),
                'temp_f_std': float(config.get('baseline_temp_f_std', 0)),
                'hum_med': float(config.get('baseline_hum_med', 0)),
                'hum_mad': float(config.get('baseline_hum_mad', 0)),
                'hum_std': float(config.get('baseline_hum_std', 0))
            }
            
            # Get last alert times from config
            last_alert_times = {
                'temp': self.db.get_config('last_alert_temp') or '',
                'humidity': self.db.get_config('last_alert_humidity') or '',
                'pressure': self.db.get_config('last_alert_pressure') or ''
            }
            
            # Check most recent reading for anomalies
            latest_reading = self.reading_buffer[-1]
            anomalies = detect_anomalies(latest_reading, baseline_stats, config, last_alert_times)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def handle_anomalies(self, anomalies):
        """Handle detected anomalies"""
        if not anomalies:
            return
        
        try:
            logger.warning(f"Detected {len(anomalies)} anomalies!")
            
            # Store anomalies in database
            for anomaly in anomalies:
                self.db.insert_anomaly(
                    ts_utc=anomaly['ts_utc'],
                    metric=anomaly['metric'],
                    value=anomaly['value'],
                    rule=anomaly['rule'],
                    details=anomaly['details']
                )
                
                # Update last alert time for this metric
                if anomaly['metric'] == 'temp_f':
                    self.db.set_config('last_alert_temp', anomaly['ts_utc'])
                elif anomaly['metric'] == 'humidity':
                    self.db.set_config('last_alert_humidity', anomaly['ts_utc'])
                elif anomaly['metric'] == 'pressure':
                    self.db.set_config('last_alert_pressure', anomaly['ts_utc'])
            
            # Prepare sensor context for LLM analysis
            sensor_context = self._prepare_sensor_context()
            
            # Send email alert with sensor context
            if self.email_manager.enabled:
                success = self.email_manager.send_anomaly_alert(anomalies, sensor_context)
                if success:
                    logger.info("Email alert sent successfully")
                else:
                    logger.error("Failed to send email alert")
            
            self.anomaly_count += len(anomalies)
            
        except Exception as e:
            logger.error(f"Error handling anomalies: {e}")
    
    def _prepare_sensor_context(self):
        """Prepare sensor context data for LLM analysis"""
        try:
            # Get recent readings from buffer (last 5 minutes)
            context_data = []
            
            for reading in self.reading_buffer:
                context_data.append({
                    'timestamp': reading[0],
                    'temp_f': reading[1],
                    'humidity': reading[2],
                    'pressure': reading[3]
                })
            
            return context_data
            
        except Exception as e:
            logger.error(f"Error preparing sensor context: {e}")
            return []
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting Sleep Monitor Detector...")
        logger.info("Press Ctrl+C to stop monitoring")
        
        # Check if baseline exists
        config = self.get_baseline_config()
        if not config:
            logger.error("No baseline configuration found. Please run 'python3 build_baseline.py' first.")
            return
        
        if not self.initialize_sensor():
            logger.error("Failed to initialize sensor. Exiting.")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Monitoring started. Reading sensor every second...")
        logger.info("Anomaly detection active with 5-minute rolling window")
        
        try:
            while self.running:
                # Read sensor
                reading = self.read_sensor()
                
                if reading:
                    # Display current values
                    print(f"\rTemp: {reading['temp_f']:.1f}°F  Humidity: {reading['humidity']:.1f}%  Pressure: {reading['pressure']:.1f}hPa  Readings: {self.reading_count}  Anomalies: {self.anomaly_count}", end="", flush=True)
                    
                    # Store reading
                    self.store_reading(reading)
                    
                    # Check for anomalies every 30 seconds
                    if self.reading_count % 30 == 0:
                        anomalies = self.detect_anomalies_in_window()
                        if anomalies:
                            self.handle_anomalies(anomalies)
                else:
                    logger.warning("Failed to read sensor")
                
                # Wait 1 second
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error during monitoring: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Cleanup and shutdown"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(f"Monitoring completed. Duration: {duration}")
        
        logger.info(f"Total readings: {self.reading_count}")
        logger.info(f"Total anomalies detected: {self.anomaly_count}")
        
        # Close database connection
        self.db.close()
        
        print(f"\nMonitoring complete! Processed {self.reading_count} readings, detected {self.anomaly_count} anomalies")

def main():
    """Main function"""
    print("Sleep Monitor Detector - Nights 1+ (Monitoring)")
    print("=" * 50)
    
    # Check if database exists
    db_path = Path(__file__).parent / "sleepmon.db"
    if not db_path.exists():
        print("Database not found. Please run 'python3 init_db.py' first.")
        sys.exit(1)
    
    # Check if baseline exists
    try:
        with DatabaseManager(str(db_path)) as db:
            baseline_exists = db.get_config('baseline_temp_f_med')
            if not baseline_exists:
                print("No baseline configuration found.")
                print("   Please run 'python3 build_baseline.py' first to compute baseline thresholds.")
                sys.exit(1)
    except Exception as e:
        print(f"Error checking database: {e}")
        sys.exit(1)
    
    # Check email configuration
    email_manager = EmailAlertManager()
    if not email_manager.enabled:
        print("Email alerts not configured.")
        print("   Set SMTP_USER, SMTP_PASS_APP, and ALERT_TO environment variables for alerts.")
        print("   Monitoring will continue without email alerts.")
    
    print(f"Database: {db_path}")
    print("Starting monitoring in 3 seconds...")
    print("   Press Ctrl+C to stop at any time")
    
    time.sleep(3)
    
    # Start monitoring
    detector = SleepMonitorDetector(str(db_path))
    detector.run()

if __name__ == "__main__":
    main()
