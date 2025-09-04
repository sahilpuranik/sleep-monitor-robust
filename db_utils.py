#!/usr/bin/env python3
"""
Database utilities for Sleep Monitor
Handles SQLite connection, WAL mode, and common operations
"""

import sqlite3
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "sleepmon.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self) -> sqlite3.Connection:
        """Create database connection with WAL mode enabled"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better performance and safety
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=10000")
            self.conn.execute("PRAGMA temp_store=MEMORY")
            logger.info(f"Connected to database: {self.db_path}")
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL statement"""
        conn = self.connect()
        return conn.execute(sql, params)
    
    def executemany(self, sql: str, params: List[tuple]) -> sqlite3.Cursor:
        """Execute SQL statement with multiple parameter sets"""
        conn = self.connect()
        return conn.executemany(sql, params)
    
    def commit(self):
        """Commit pending transactions"""
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        """Rollback pending transactions"""
        if self.conn:
            self.conn.rollback()
    
    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value"""
        cursor = self.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def set_config(self, key: str, value: str):
        """Set configuration value"""
        self.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.commit()
    
    def insert_reading(self, ts_utc: str, temp_f: float, humidity: float, pressure: float):
        """Insert a single sensor reading"""
        self.execute(
            "INSERT OR REPLACE INTO readings (ts_utc, temp_f, humidity, pressure) VALUES (?, ?, ?, ?)",
            (ts_utc, temp_f, humidity, pressure)
        )
        self.commit()
    
    def insert_minute_stats(self, ts_min: str, stats: Dict[str, float]):
        """Insert minute-level statistics"""
        self.execute(
            """INSERT OR REPLACE INTO minute_stats 
               (ts_min, temp_f_med, temp_f_mad, temp_f_std, hum_med, hum_mad, hum_std, rows)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts_min, stats['temp_f_med'], stats['temp_f_mad'], stats['temp_f_std'],
             stats['hum_med'], stats['hum_mad'], stats['hum_std'], stats['rows'])
        )
        self.commit()
    
    def insert_anomaly(self, ts_utc: str, metric: str, value: float, rule: str, details: str):
        """Insert anomaly record"""
        self.execute(
            "INSERT INTO anomalies (ts_utc, metric, value, rule, details) VALUES (?, ?, ?, ?, ?)",
            (ts_utc, metric, value, rule, details)
        )
        self.commit()
    
    def get_readings_for_window(self, start_time: str, end_time: str) -> List[Tuple[str, float, float, float]]:
        """Get readings within a time window"""
        cursor = self.execute(
            "SELECT ts_utc, temp_f, humidity, pressure FROM readings WHERE ts_utc BETWEEN ? AND ? ORDER BY ts_utc",
            (start_time, end_time)
        )
        return cursor.fetchall()
    
    def get_minute_stats_for_window(self, start_time: str, end_time: str) -> List[Tuple[str, float, float, float, float, float, float, int]]:
        """Get minute stats within a time window"""
        cursor = self.execute(
            """SELECT ts_min, temp_f_med, temp_f_mad, temp_f_std, hum_med, hum_mad, hum_std, rows 
               FROM minute_stats WHERE ts_min BETWEEN ? AND ? ORDER BY ts_min""",
            (start_time, end_time)
        )
        return cursor.fetchall()
    
    def get_reading_count(self) -> int:
        """Get total number of readings"""
        cursor = self.execute("SELECT COUNT(*) FROM readings")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def get_last_reading_time(self) -> Optional[str]:
        """Get timestamp of last reading"""
        cursor = self.execute("SELECT MAX(ts_utc) FROM readings")
        result = cursor.fetchone()
        return result[0] if result else None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def init_database(db_path: str = "sleepmon.db"):
    """Initialize database with schema"""
    if not os.path.exists(db_path):
        logger.info(f"Creating new database: {db_path}")
    
    with DatabaseManager(db_path) as db:
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        for statement in statements:
            if statement:
                db.execute(statement)
        
        db.commit()
        logger.info("Database initialized successfully")
        
        # Verify tables were created
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Created tables: {tables}")
