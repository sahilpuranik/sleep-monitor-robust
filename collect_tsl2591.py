#!/usr/bin/env python3
"""
TSL2591 Light Sensor Data Collection Script (Night 0 - Calibration)
Reads TSL2591 sensor every second and stores readings in database
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class TSL2591Collector:
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
        """Initialize TSL2591 sensor"""
        try:
            import board
            import busio
            from adafruit_tsl2591 import TSL2591
            
            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize TSL2591 sensor
            self.sensor = TSL2591(i2c)
            
            # Set sensor configuration for high accuracy
            self.sensor.gain = 0x01  # Low gain (1x) for high light levels
            self.sensor.integration_time = 0x02  # 200ms integration time
            
            logger.info("TSL2591 sensor initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import TSL2591 libraries: {e}")
            logger.error("Make sure you have installed: pip3 install adafruit-circuitpython-tsl2591")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize TSL2591 sensor: {e}")
            return False
    
    def read_sensor(self):
        """Read current sensor values"""
        try:
            if not self.sensor:
                return None
            
            # Read sensor values
            lux = self.sensor.lux
            full_spectrum = self.sensor.full_spectrum
            ir = self.sensor.infrared
            
            return {
                'lux': lux,
                'full_spectrum': full_spectrum,
                'ir': ir
            }
            
        except Exception as e:
            logger.error(f"Error reading sensor: {e}")
            return None
    
    def store_reading(self, reading):
        """Store sensor reading in database"""
        try:
            # Generate UTC timestamp
            ts_utc = datetime.now(timezone.utc).isoformat()
            
            # Store in database (only light sensor data)
            self.db.insert_light_reading(
                ts_utc=ts_utc,
                lux=reading['lux'],
                full_spectrum=reading['full_spectrum'],
                ir=reading['ir']
            )
            
            self.reading_count += 1
            
            # Log every 60 readings (every minute)
            if self.reading_count % 60 == 0:
                logger.info(f"Stored {self.reading_count} readings...")
                
        except Exception as e:
            logger.error(f"Error storing reading: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting TSL2591 data collection...")
        logger.info("Press Ctrl+C to stop collection")
        
        if not self.initialize_sensor():
            logger.error("Failed to initialize sensor. Exiting.")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Collection started. Reading sensor every second...")
        
        try:
            while self.running:
                # Read sensor
                reading = self.read_sensor()
                
                if reading:
                    # Display current values
                    print(f"\rLux: {reading['lux']:.1f}  Full: {reading['full_spectrum']}  IR: {reading['ir']}  Readings: {self.reading_count}", end="", flush=True)
                    
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
    print("TSL2591 Light Sensor Data Collection - Night 0 (Calibration)")
    print("=" * 60)
    
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
    collector = TSL2591Collector(str(db_path))
    collector.run()

if __name__ == "__main__":
    main()
