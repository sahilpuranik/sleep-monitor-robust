#!/usr/bin/env python3
"""
INMP441 Microphone Data Collection Script (Night 0 - Calibration)
Reads INMP441 microphone every second and stores RMS amplitude in database
"""

import os
import sys
import time
import signal
import logging
import math
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

class INMP441Collector:
    def __init__(self, db_path: str = "sleepmon.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        self.running = False
        self.mic = None
        self.reading_count = 0
        self.start_time = None
        
        # Audio capture parameters
        self.sample_rate = 8000  # 8kHz sample rate
        self.sample_duration = 1.0  # 1 second of audio per reading
        self.samples_per_reading = int(self.sample_rate * self.sample_duration)
        
        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def initialize_sensor(self):
        """Initialize INMP441 microphone"""
        try:
            import board
            import audiobusio
            
            # Initialize I2S microphone
            # INMP441 typically uses I2S with these pins on Raspberry Pi
            self.mic = audiobusio.I2SOut(
                board.D18,  # Bit clock (BCLK)
                board.D19,  # Word select (WS/LRCLK) 
                board.D20   # Data (DIN)
            )
            
            # Alternative pin configuration for different setups
            # self.mic = audiobusio.I2SOut(board.D26, board.D19, board.D20)
            
            logger.info("INMP441 microphone initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import I2S libraries: {e}")
            logger.error("Make sure you have installed: pip3 install adafruit-blinka")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize INMP441 microphone: {e}")
            logger.error("Check your I2S wiring: BCLK->D18, WS->D19, DIN->D20")
            return False
    
    def read_sensor(self):
        """Read current microphone values"""
        try:
            if not self.mic:
                return None
            
            # Record audio samples
            samples = []
            for _ in range(self.samples_per_reading):
                # Read 16-bit signed integer from I2S
                sample = self.mic.record(1)[0]
                samples.append(sample)
            
            # Calculate RMS (Root Mean Square) amplitude
            sum_squares = sum(sample * sample for sample in samples)
            rms = math.sqrt(sum_squares / len(samples))
            
            # Convert to dB (relative to full scale)
            if rms > 0:
                db = 20 * math.log10(rms / 32767.0)  # 16-bit full scale
            else:
                db = -96  # Minimum dB for silence
            
            return {
                'sound_rms': rms,
                'sound_db': db
            }
            
        except Exception as e:
            logger.error(f"Error reading microphone: {e}")
            return None
    
    def store_reading(self, reading):
        """Store sensor reading in database"""
        try:
            # Generate UTC timestamp
            ts_utc = datetime.now(timezone.utc).isoformat()
            
            # Store in database (only sound sensor data)
            self.db.insert_sound_reading(
                ts_utc=ts_utc,
                sound_rms=reading['sound_rms']
            )
            
            self.reading_count += 1
            
            # Log every 60 readings (every minute)
            if self.reading_count % 60 == 0:
                logger.info(f"Stored {self.reading_count} readings...")
                
        except Exception as e:
            logger.error(f"Error storing reading: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting INMP441 microphone data collection...")
        logger.info("Press Ctrl+C to stop collection")
        
        if not self.initialize_sensor():
            logger.error("Failed to initialize microphone. Exiting.")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("Collection started. Reading microphone every second...")
        logger.info(f"Sample rate: {self.sample_rate}Hz, Duration: {self.sample_duration}s per reading")
        
        try:
            while self.running:
                # Read sensor
                reading = self.read_sensor()
                
                if reading:
                    # Display current values
                    print(f"\rRMS: {reading['sound_rms']:.1f}  dB: {reading['sound_db']:.1f}  Readings: {self.reading_count}", end="", flush=True)
                    
                    # Store in database
                    self.store_reading(reading)
                else:
                    logger.warning("Failed to read microphone")
                
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
    print("INMP441 Microphone Data Collection - Night 0 (Calibration)")
    print("=" * 60)
    
    # Check if database exists
    db_path = Path(__file__).parent / "sleepmon.db"
    if not db_path.exists():
        print("Database not found. Please run 'python3 init_db.py' first.")
        sys.exit(1)
    
    print(f"Database: {db_path}")
    print("Collection will start in 3 seconds...")
    print("   Press Ctrl+C to stop at any time")
    print("   I2S Wiring: BCLK->D18, WS->D19, DIN->D20")
    
    time.sleep(3)
    
    # Start collection
    collector = INMP441Collector(str(db_path))
    collector.run()

if __name__ == "__main__":
    main()
