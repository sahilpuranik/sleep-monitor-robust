#!/usr/bin/env python3
"""
BME280 Data Collection Script (Night 0 - Calibration)
Reads BME280 sensor every second and stores readings in database
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import DatabaseManager
from stats_utils import celsius_to_fahrenheit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BME280Collector:
    def __init__(self, db_path: str = "sleepmon.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        self.running = False
        self.sensor = None
        self.reading_count = 0
        self.start_time = None
        
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
            self.sensor.sea_level_pressure = 1013.25  # Default sea level pressure
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
            
            self.reading_count += 1
            
            # Log every 60 readings (every minute)
            if self.reading_count % 60 == 0:
                logger.info(f"Stored {self.reading_count} readings...")
                
        except Exception as e:
            logger.error(f"Error storing reading: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting BME280 data collection...")
        logger.info("Press Ctrl+C to stop collection")
        
        if not self.initialize_sensor():
            logger.error("Failed to initialize sensor. Exiting.")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Collection started. Reading sensor every second...")
        logger.info("Temperature will be displayed in Fahrenheit")
        
        try:
            while self.running:
                # Read sensor
                reading = self.read_sensor()
                
                if reading:
                    # Display current values
                    print(f"\rTemp: {reading['temp_f']:.1f}°F  Humidity: {reading['humidity']:.1f}%  Pressure: {reading['pressure']:.1f}hPa  Readings: {self.reading_count}", end="", flush=True)
                    
                    # Store in database
                    self.store_reading(reading)
                else:
                    logger.warning("Failed to read sensor")
                
                # Wait 1 second
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Collection stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error during collection: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Cleanup and shutdown"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(f"Collection completed. Duration: {duration}")
        
        logger.info(f"Total readings collected: {self.reading_count}")
        
        # Close database connection
        self.db.close()
        
        print(f"\nCollection complete! Stored {self.reading_count} readings in {self.db_path}")
        print("Next step: Run 'python3 build_baseline.py' to compute baseline statistics")

def main():
    """Main function"""
    print("BME280 Data Collection - Night 0 (Calibration)")
    print("=" * 50)
    
    # Check if database exists
    db_path = Path(__file__).parent / "sleepmon.db"
    if not db_path.exists():
        print("Database not found. Please run 'python3 init_db.py' first.")
        sys.exit(1)
    
    print(f"Database: {db_path}")
    print("Collection will start in 3 seconds...")
    print("   Press Ctrl+C to stop at any time")
    
    time.sleep(3)
    
    # Start collection
    collector = BME280Collector(str(db_path))
    collector.run()

if __name__ == "__main__":
    main()
