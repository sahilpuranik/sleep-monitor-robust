#!/usr/bin/env python3
"""
Build Baseline Script (Night 0 - Calibration)
Processes collected data to compute baseline statistics and thresholds
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import DatabaseManager
from stats_utils import (
    calculate_minute_stats, 
    aggregate_readings_to_minutes,
    calculate_baseline_thresholds
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BaselineBuilder:
    def __init__(self, db_path: str = "sleepmon.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
    
    def get_calibration_data(self) -> list:
        """Get all readings from the database for baseline calculation"""
        try:
            cursor = self.db.execute("SELECT ts_utc, temp_f, humidity, pressure FROM readings ORDER BY ts_utc")
            readings = cursor.fetchall()
            
            logger.info(f"Retrieved {len(readings)} readings for baseline calculation")
            return readings
            
        except Exception as e:
            logger.error(f"Error retrieving calibration data: {e}")
            return []
    
    def compute_minute_statistics(self, readings: list) -> dict:
        """Compute per-minute statistics from raw readings"""
        try:
            logger.info("Computing per-minute statistics...")
            
            # Group readings by minute
            minute_groups = aggregate_readings_to_minutes(readings)
            logger.info(f"Grouped readings into {len(minute_groups)} minute intervals")
            
            # Compute stats for each minute
            minute_stats = {}
            for minute_key, minute_readings in minute_groups.items():
                stats = calculate_minute_stats(minute_readings)
                minute_stats[minute_key] = stats
                
                # Store in database
                self.db.insert_minute_stats(minute_key, stats)
            
            logger.info(f"Computed and stored statistics for {len(minute_stats)} minutes")
            return minute_stats
            
        except Exception as e:
            logger.error(f"Error computing minute statistics: {e}")
            return {}
    
    def calculate_baseline_thresholds(self, readings: list) -> dict:
        """Calculate baseline thresholds from calibration data"""
        try:
            logger.info("Calculating baseline thresholds...")
            
            # Calculate overall baseline statistics
            baseline = calculate_baseline_thresholds(readings)
            
            if not baseline:
                logger.error("No baseline data calculated")
                return {}
            
            # Log baseline values
            logger.info("Baseline thresholds calculated:")
            logger.info(f"  Temperature: median={baseline['temp_f_med']:.2f}°F, MAD={baseline['temp_f_mad']:.2f}°F")
            logger.info(f"  Humidity: median={baseline['hum_med']:.2f}%, MAD={baseline['hum_mad']:.2f}%")
            
            return baseline
            
        except Exception as e:
            logger.error(f"Error calculating baseline thresholds: {e}")
            return {}
    
    def store_baseline_config(self, baseline: dict):
        """Store baseline values in configuration table"""
        try:
            logger.info("Storing baseline configuration...")
            
            # Store baseline statistics
            self.db.set_config('baseline_temp_f_med', str(baseline['temp_f_med']))
            self.db.set_config('baseline_temp_f_mad', str(baseline['temp_f_mad']))
            self.db.set_config('baseline_temp_f_std', str(baseline['temp_f_std']))
            self.db.set_config('baseline_hum_med', str(baseline['hum_med']))
            self.db.set_config('baseline_hum_mad', str(baseline['hum_mad']))
            self.db.set_config('baseline_hum_std', str(baseline['hum_std']))
            
            # Store baseline timestamp
            baseline_time = datetime.utcnow().isoformat()
            self.db.set_config('baseline_computed_at', baseline_time)
            
            logger.info("Baseline configuration stored successfully")
            
        except Exception as e:
            logger.error(f"Error storing baseline configuration: {e}")
    
    def generate_summary_report(self, readings: list, minute_stats: dict, baseline: dict):
        """Generate a summary report of the baseline computation"""
        try:
            # Calculate data quality metrics
            total_readings = len(readings)
            total_minutes = len(minute_stats)
            
            if total_readings > 0:
                # Calculate time span
                first_reading = readings[0][0]
                last_reading = readings[-1][0]
                
                first_dt = datetime.fromisoformat(first_reading.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_reading.replace('Z', '+00:00'))
                duration = last_dt - first_dt
                
                # Calculate average readings per minute
                avg_readings_per_minute = total_readings / total_minutes if total_minutes > 0 else 0
                
                print("\n" + "="*60)
                print("BASELINE COMPUTATION SUMMARY")
                print("="*60)
                print(f"Data Collection Period:")
                print(f"   Start: {first_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   End:   {last_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Duration: {duration}")
                print()
                print(f"Data Volume:")
                print(f"   Total Readings: {total_readings:,}")
                print(f"   Total Minutes: {total_minutes}")
                print(f"   Avg Readings/Minute: {avg_readings_per_minute:.1f}")
                print()
                print(f"Baseline Thresholds:")
                print(f"   Temperature: {baseline['temp_f_med']:.1f}°F ± {baseline['temp_f_mad']:.1f}°F (MAD)")
                print(f"   Humidity: {baseline['hum_med']:.1f}% ± {baseline['hum_mad']:.1f}% (MAD)")
                print()
                print(f"Baseline computation complete!")
                print(f"Next step: Run 'python3 run_detector.py' for monitoring")
                print("="*60)
                
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
    
    def run(self):
        """Main baseline building process"""
        print("Building Sleep Monitor Baseline...")
        print("=" * 50)
        
        try:
            # Check if we have data
            reading_count = self.db.get_reading_count()
            if reading_count == 0:
                print("No readings found in database.")
                print("   Please run 'python3 collect_bme280.py' first to collect calibration data.")
                return
            
            print(f"Found {reading_count:,} readings in database")
            
            # Step 1: Retrieve calibration data
            print("\nRetrieving calibration data...")
            readings = self.get_calibration_data()
            
            if not readings:
                print("Failed to retrieve calibration data")
                return
            
            # Step 2: Compute minute statistics
            print("\nComputing minute statistics...")
            minute_stats = self.compute_minute_statistics(readings)
            
            if not minute_stats:
                print("Failed to compute minute statistics")
                return
            
            # Step 3: Calculate baseline thresholds
            print("\nCalculating baseline thresholds...")
            baseline = self.calculate_baseline_thresholds(readings)
            
            if not baseline:
                print("Failed to calculate baseline thresholds")
                return
            
            # Step 4: Store baseline configuration
            print("\nStoring baseline configuration...")
            self.store_baseline_config(baseline)
            
            # Step 5: Generate summary report
            self.generate_summary_report(readings, minute_stats, baseline)
            
        except Exception as e:
            logger.error(f"Baseline building failed: {e}")
            print(f"Error: {e}")
        finally:
            self.db.close()

def main():
    """Main function"""
    print("Sleep Monitor - Baseline Builder (Night 0)")
    print("=" * 50)
    
    # Check if database exists
    db_path = Path(__file__).parent / "sleepmon.db"
    if not db_path.exists():
        print("Database not found. Please run 'python3 init_db.py' first.")
        sys.exit(1)
    
    # Check if we have readings
    try:
        with DatabaseManager(str(db_path)) as db:
            reading_count = db.get_reading_count()
            if reading_count == 0:
                print("No readings found in database.")
                print("   Please run 'python3 collect_bme280.py' first to collect calibration data.")
                sys.exit(1)
    except Exception as e:
        print(f"Error checking database: {e}")
        sys.exit(1)
    
    print(f"Database: {db_path}")
    print("Starting baseline computation...")
    
    # Build baseline
    builder = BaselineBuilder(str(db_path))
    builder.run()

if __name__ == "__main__":
    main()
