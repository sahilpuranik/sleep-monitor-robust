#!/usr/bin/env python3
"""
Initialize Sleep Monitor Database
Creates SQLite database with schema and enables WAL mode
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main function to initialize the database"""
    print("Initializing Sleep Monitor Database...")
    
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.absolute()
        db_path = script_dir / "sleepmon.db"
        
        print(f"Database will be created at: {db_path}")
        
        # Initialize database
        init_database(str(db_path))
        
        print("Database initialized successfully!")
        print(f"Database file: {db_path}")
        
        # Verify database was created
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"Database size: {size_mb:.2f} MB")
            
            # Check for WAL mode
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                print(f"Journal mode: {journal_mode}")
                
                if journal_mode == "wal":
                    print("WAL mode enabled successfully")
                else:
                    print("WAL mode not enabled - this may affect performance")
        
        print("\nNext steps:")
        print("1. Run: python3 collect_bme280.py (for Night 0 calibration)")
        print("2. Or run: python3 run_detector.py (for Nights 1+ monitoring)")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
