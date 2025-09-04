#!/usr/bin/env python3
"""
Main Sleep Monitor Entry Point
Unified interface for the robust statistical sleep monitoring system
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import DatabaseManager
from collect_bme280 import BME280Collector
from build_baseline import BaselineBuilder
from run_detector import SleepMonitorDetector
from test_email import main as test_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import board
        import busio
        from adafruit_bme280 import basic as adafruit_bme280
        return True
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.error("Install with: pip3 install --break-system-packages -r requirements.txt")
        return False

def check_database():
    """Check if database exists and has required tables"""
    db_path = Path(__file__).parent / "sleepmon.db"
    if not db_path.exists():
        return False, "Database not found"
    
    try:
        with DatabaseManager(str(db_path)) as db:
            # Check if we have the required tables
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            required_tables = ['readings', 'minute_stats', 'config', 'anomalies']
            
            missing_tables = [table for table in required_tables if table not in tables]
            if missing_tables:
                return False, f"Missing tables: {missing_tables}"
            
            return True, "Database ready"
    except Exception as e:
        return False, f"Database error: {e}"

def initialize_system():
    """Initialize the complete sleep monitoring system"""
    print("Initializing Sleep Monitor System...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("Dependencies check failed. Please install required packages.")
        return False
    
    # Check database
    db_ready, db_message = check_database()
    if not db_ready:
        print(f"Database not ready: {db_message}")
        print("Running database initialization...")
        
        try:
            from init_db import main as init_db
            init_db()
        except Exception as e:
            print(f"Database initialization failed: {e}")
            return False
    
    print("System initialization complete!")
    return True

def run_calibration():
    """Run the calibration process (Night 0)"""
    print("\nStarting Calibration Process (Night 0)...")
    print("This will collect baseline data for anomaly detection.")
    print("Press Ctrl+C when you have enough data (recommended: 8+ hours)")
    
    try:
        from collect_bme280 import main as collect_data
        collect_data()
        
        print("\nCalibration data collection complete!")
        print("Building baseline statistics...")
        
        from build_baseline import main as build_baseline
        build_baseline()
        
        print("\nCalibration complete! System is ready for monitoring.")
        return True
        
    except KeyboardInterrupt:
        print("\nCalibration stopped by user.")
        return False
    except Exception as e:
        print(f"Calibration failed: {e}")
        return False

def run_monitoring():
    """Run the monitoring process (Nights 1+)"""
    print("\nStarting Monitoring Process (Nights 1+)...")
    print("This will continuously monitor for anomalies.")
    print("Press Ctrl+C to stop monitoring.")
    
    try:
        from run_detector import main as run_detector
        run_detector()
        return True
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
        return False
    except Exception as e:
        print(f"Monitoring failed: {e}")
        return False

def show_status():
    """Show current system status"""
    print("\nSleep Monitor System Status")
    print("=" * 40)
    
    # Check database
    db_ready, db_message = check_database()
    print(f"Database: {'Ready' if db_ready else 'Not Ready'}")
    if not db_ready:
        print(f"  Issue: {db_message}")
        return
    
    # Check sensor dependencies
    sensor_ready = check_dependencies()
    print(f"Sensors: {'Ready' if sensor_ready else 'Not Ready'}")
    
    # Check baseline
    try:
        with DatabaseManager("sleepmon.db") as db:
            baseline_exists = db.get_config('baseline_temp_f_med')
            if baseline_exists:
                print("Baseline: Ready")
                print(f"  Temperature: {float(baseline_exists):.1f}°F")
                
                hum_med = db.get_config('baseline_hum_med')
                if hum_med:
                    print(f"  Humidity: {float(hum_med):.1f}%")
            else:
                print("Baseline: Not Ready (run calibration first)")
            
            # Check readings count
            reading_count = db.get_reading_count()
            print(f"Total Readings: {reading_count:,}")
            
            # Check anomalies
            cursor = db.execute("SELECT COUNT(*) FROM anomalies")
            anomaly_count = cursor.fetchone()[0]
            print(f"Total Anomalies: {anomaly_count}")
            
    except Exception as e:
        print(f"Status check failed: {e}")

def show_help():
    """Show help information"""
    print("""
Sleep Monitor - Robust Statistical Anomaly Detection

This system monitors your sleep environment using a BME280 sensor and detects
anomalies using robust statistical methods instead of machine learning.

USAGE:
  python3 Main.py [command] [options]

COMMANDS:
  init          Initialize the system (database, tables)
  calibrate     Run calibration process (Night 0)
  monitor       Start monitoring for anomalies (Nights 1+)
  status        Show current system status
  test-email    Test email configuration
  help          Show this help message

EXAMPLES:
  # First time setup
  python3 Main.py init
  python3 Main.py calibrate
  
  # Daily monitoring
  python3 Main.py monitor
  
  # Check system status
  python3 Main.py status

FEATURES:
  - Robust statistical anomaly detection (MAD-based)
  - SQLite database with WAL mode for reliability
  - Email alerts via Gmail SMTP
  - Rolling window analysis (5-minute context)
  - Cooldown system to prevent alert spam
  - Graceful shutdown handling

For detailed documentation, see README.md
""")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sleep Monitor - Robust Statistical Anomaly Detection",
        add_help=False
    )
    parser.add_argument('command', nargs='?', default='help',
                       help='Command to run (init, calibrate, monitor, status, test-email)')
    
    args = parser.parse_args()
    command = args.command.lower()
    
    print("Sleep Monitor - Main Control")
    print("=" * 40)
    
    if command == 'init':
        if initialize_system():
            print("System initialization successful!")
        else:
            print("System initialization failed!")
            sys.exit(1)
    
    elif command == 'calibrate':
        if not initialize_system():
            print("System not ready for calibration.")
            sys.exit(1)
        run_calibration()
    
    elif command == 'monitor':
        if not initialize_system():
            print("System not ready for monitoring.")
            sys.exit(1)
        
        # Check if baseline exists
        db_ready, _ = check_database()
        if db_ready:
            with DatabaseManager("sleepmon.db") as db:
                baseline_exists = db.get_config('baseline_temp_f_med')
                if not baseline_exists:
                    print("No baseline found. Please run calibration first:")
                    print("  python3 Main.py calibrate")
                    sys.exit(1)
        
        run_monitoring()
    
    elif command == 'status':
        show_status()
    
    elif command == 'test-email':
        test_email()
    
    elif command in ['help', '--help', '-h']:
        show_help()
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python3 Main.py help' for available commands")
        sys.exit(1)

if __name__ == "__main__":
    main()
