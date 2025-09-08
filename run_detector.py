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
        self.sensors = {
            'bme280': None,
            'tsl2591': None,
            'inmp441': None
        }
        self.reading_count = 0
        self.start_time = None
        
        # Anomaly tracking
        self.last_alert_times = defaultdict(str)
        self.anomaly_count = 0
        self.session_anomalies = []  # Collect all anomalies for batch processing
        
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
    
    def initialize_sensors(self):
        """Initialize all available sensors"""
        sensors_initialized = 0
        
        # Initialize BME280 sensor
        try:
            import board
            import busio
            from adafruit_bme280 import basic as adafruit_bme280
            
            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize BME280 sensor
            self.sensors['bme280'] = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
            
            # Set sensor configuration for high accuracy
            self.sensors['bme280'].sea_level_pressure = 1013.25
            self.sensors['bme280'].mode = adafruit_bme280.MODE_NORMAL
            self.sensors['bme280'].standby_period = adafruit_bme280.STANDBY_TC_500
            self.sensors['bme280'].iir_filter = adafruit_bme280.IIR_FILTER_X16
            self.sensors['bme280'].overscan_pressure = adafruit_bme280.OVERSCAN_X16
            self.sensors['bme280'].overscan_humidity = adafruit_bme280.OVERSCAN_X1
            self.sensors['bme280'].overscan_temperature = adafruit_bme280.OVERSCAN_X2
            
            logger.info("BME280 sensor initialized successfully")
            sensors_initialized += 1
            
        except ImportError as e:
            logger.warning(f"BME280 libraries not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize BME280 sensor: {e}")
        
        # Initialize TSL2591 light sensor
        try:
            from adafruit_tsl2591 import TSL2591
            
            # Use existing I2C bus
            if 'i2c' not in locals():
                import board
                import busio
                i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize TSL2591 sensor
            self.sensors['tsl2591'] = TSL2591(i2c)
            
            # Set sensor configuration for high accuracy
            self.sensors['tsl2591'].gain = 0x01  # Low gain (1x) for high light levels
            self.sensors['tsl2591'].integration_time = 0x02  # 200ms integration time
            
            logger.info("TSL2591 light sensor initialized successfully")
            sensors_initialized += 1
            
        except ImportError as e:
            logger.warning(f"TSL2591 libraries not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize TSL2591 sensor: {e}")
        
        # Initialize INMP441 microphone
        try:
            import audiobusio
            
            # Initialize I2S microphone
            self.sensors['inmp441'] = audiobusio.I2SOut(
                board.D18,  # Bit clock (BCLK)
                board.D19,  # Word select (WS/LRCLK) 
                board.D20   # Data (DIN)
            )
            
            logger.info("INMP441 microphone initialized successfully")
            sensors_initialized += 1
            
        except ImportError as e:
            logger.warning(f"I2S libraries not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize INMP441 microphone: {e}")
        
        if sensors_initialized == 0:
            logger.error("No sensors could be initialized")
            return False
        
        logger.info(f"Successfully initialized {sensors_initialized} sensor(s)")
        return True
    
    def read_sensors(self):
        """Read current values from all available sensors"""
        reading = {
            'temp_f': None,
            'humidity': None,
            'pressure': None,
            'lux': None,
            'full_spectrum': None,
            'ir': None,
            'sound_rms': None
        }
        
        # Read BME280 sensor
        if self.sensors['bme280']:
            try:
                temp_c = self.sensors['bme280'].temperature
                reading['temp_f'] = celsius_to_fahrenheit(temp_c)
                reading['humidity'] = self.sensors['bme280'].relative_humidity
                reading['pressure'] = self.sensors['bme280'].pressure
            except Exception as e:
                logger.warning(f"Error reading BME280: {e}")
        
        # Read TSL2591 light sensor
        if self.sensors['tsl2591']:
            try:
                reading['lux'] = self.sensors['tsl2591'].lux
                reading['full_spectrum'] = self.sensors['tsl2591'].full_spectrum
                reading['ir'] = self.sensors['tsl2591'].infrared
            except Exception as e:
                logger.warning(f"Error reading TSL2591: {e}")
        
        # Read INMP441 microphone
        if self.sensors['inmp441']:
            try:
                import math
                # Record audio samples for 1 second
                sample_rate = 8000
                samples = []
                for _ in range(sample_rate):
                    sample = self.sensors['inmp441'].record(1)[0]
                    samples.append(sample)
                
                # Calculate RMS amplitude
                sum_squares = sum(sample * sample for sample in samples)
                reading['sound_rms'] = math.sqrt(sum_squares / len(samples))
            except Exception as e:
                logger.warning(f"Error reading INMP441: {e}")
        
        # Return None if no sensors are working
        if all(v is None for v in reading.values()):
            return None
        
        return reading
    
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
                pressure=reading['pressure'],
                lux=reading['lux'],
                full_spectrum=reading['full_spectrum'],
                ir=reading['ir'],
                sound_rms=reading['sound_rms']
            )
            
            # Add to rolling buffer (create tuple with all values)
            buffer_reading = (
                ts_utc, 
                reading['temp_f'], 
                reading['humidity'], 
                reading['pressure'],
                reading['lux'],
                reading['full_spectrum'],
                reading['ir'],
                reading['sound_rms']
            )
            self.reading_buffer.append(buffer_reading)
            
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
                'baseline_lux_med', 'baseline_lux_mad', 'baseline_lux_std',
                'baseline_sound_med', 'baseline_sound_mad', 'baseline_sound_std',
                'robust_z_threshold', 'temp_roc_limit', 'humidity_roc_limit',
                'lux_roc_limit', 'sound_roc_limit',
                'temp_min', 'temp_max', 'humidity_min', 'humidity_max',
                'lux_min', 'lux_max', 'sound_min', 'sound_max', 'cooldown_minutes'
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
                'hum_std': float(config.get('baseline_hum_std', 0)),
                'lux_med': float(config.get('baseline_lux_med', 0)),
                'lux_mad': float(config.get('baseline_lux_mad', 0)),
                'lux_std': float(config.get('baseline_lux_std', 0)),
                'sound_med': float(config.get('baseline_sound_med', 0)),
                'sound_mad': float(config.get('baseline_sound_mad', 0)),
                'sound_std': float(config.get('baseline_sound_std', 0))
            }
            
            # Get last alert times from config
            last_alert_times = {
                'temp': self.db.get_config('last_alert_temp') or '',
                'humidity': self.db.get_config('last_alert_humidity') or '',
                'pressure': self.db.get_config('last_alert_pressure') or '',
                'lux': self.db.get_config('last_alert_lux') or '',
                'sound': self.db.get_config('last_alert_sound') or ''
            }
            
            # Check most recent reading for anomalies
            latest_reading = self.reading_buffer[-1]
            anomalies = detect_anomalies(latest_reading, baseline_stats, config, last_alert_times)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def handle_anomalies(self, anomalies):
        """Handle detected anomalies - collect for batch processing"""
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
                elif anomaly['metric'] == 'lux':
                    self.db.set_config('last_alert_lux', anomaly['ts_utc'])
                elif anomaly['metric'] == 'sound_rms':
                    self.db.set_config('last_alert_sound', anomaly['ts_utc'])
            
            # Collect anomalies for batch processing at shutdown
            self.session_anomalies.extend(anomalies)
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
                    'pressure': reading[3],
                    'lux': reading[4] if len(reading) > 4 else None,
                    'full_spectrum': reading[5] if len(reading) > 5 else None,
                    'ir': reading[6] if len(reading) > 6 else None,
                    'sound_rms': reading[7] if len(reading) > 7 else None
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
        
        if not self.initialize_sensors():
            logger.error("Failed to initialize any sensors. Exiting.")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Monitoring started. Reading sensor every second...")
        logger.info("Anomaly detection active with 5-minute rolling window")
        
        try:
            while self.running:
                # Read sensors
                reading = self.read_sensors()
                
                if reading:
                    # Display current values (only show non-None values)
                    display_parts = []
                    if reading['temp_f'] is not None:
                        display_parts.append(f"Temp: {reading['temp_f']:.1f}°F")
                    if reading['humidity'] is not None:
                        display_parts.append(f"Humidity: {reading['humidity']:.1f}%")
                    if reading['pressure'] is not None:
                        display_parts.append(f"Pressure: {reading['pressure']:.1f}hPa")
                    if reading['lux'] is not None:
                        display_parts.append(f"Lux: {reading['lux']:.1f}")
                    if reading['sound_rms'] is not None:
                        display_parts.append(f"Sound: {reading['sound_rms']:.1f}")
                    
                    display_parts.append(f"Readings: {self.reading_count}")
                    display_parts.append(f"Anomalies: {self.anomaly_count}")
                    
                    print(f"\r{'  '.join(display_parts)}", end="", flush=True)
                    
                    # Store reading
                    self.store_reading(reading)
                    
                    # Check for anomalies every 30 seconds
                    if self.reading_count % 30 == 0:
                        anomalies = self.detect_anomalies_in_window()
                        if anomalies:
                            self.handle_anomalies(anomalies)
                else:
                    logger.warning("Failed to read any sensors")
                
                # Wait 1 second
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error during monitoring: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Cleanup and shutdown with batch anomaly processing"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(f"Monitoring completed. Duration: {duration}")
        
        logger.info(f"Total readings: {self.reading_count}")
        logger.info(f"Total anomalies detected: {self.anomaly_count}")
        
        # Process all collected anomalies with single API call
        if self.email_manager.enabled:
            if self.session_anomalies:
                logger.info(f"Processing {len(self.session_anomalies)} anomalies for batch email")
                sensor_context = self._prepare_sensor_context()
                success = self.email_manager.send_batch_anomaly_alert(self.session_anomalies, sensor_context)
                if success:
                    logger.info("Batch anomaly email sent successfully")
                else:
                    logger.error("Failed to send batch anomaly email")
            else:
                logger.info("No anomalies detected - sending no-anomaly email")
                success = self.email_manager.send_no_anomaly_alert()
                if success:
                    logger.info("No-anomaly email sent successfully")
                else:
                    logger.error("Failed to send no-anomaly email")
        
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
