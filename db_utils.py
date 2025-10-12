#!/usr/bin/env python3

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
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=10000")
            self.conn.execute("PRAGMA temp_store=MEMORY")
            logger.info(f"Connected: {self.db_path}")
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self.connect()
        return conn.execute(sql, params)
    
    def executemany(self, sql: str, params: List[tuple]) -> sqlite3.Cursor:
        conn = self.connect()
        return conn.executemany(sql, params)
    
    def commit(self):
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        if self.conn:
            self.conn.rollback()
    
    def get_config(self, key: str) -> Optional[str]:
        cursor = self.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def set_config(self, key: str, value: str):
        self.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.commit()
    
    def insert_reading(self, ts_utc: str, temp_f: float, humidity: float, pressure: float, 
                      lux: float = None, full_spectrum: float = None, ir: float = None, 
                      sound_rms: float = None):
        self.execute(
            """INSERT OR REPLACE INTO readings 
               (ts_utc, temp_f, humidity, pressure, lux, full_spectrum, ir, sound_rms) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts_utc, temp_f, humidity, pressure, lux, full_spectrum, ir, sound_rms)
        )
        self.commit()
    
    def insert_light_reading(self, ts_utc: str, lux: float, full_spectrum: float, ir: float):
        cursor = self.execute(
            "UPDATE readings SET lux = ?, full_spectrum = ?, ir = ? WHERE ts_utc = ?",
            (lux, full_spectrum, ir, ts_utc)
        )
        
        if cursor.rowcount == 0:
            self.execute(
                """INSERT INTO readings 
                   (ts_utc, temp_f, humidity, pressure, lux, full_spectrum, ir, sound_rms) 
                   VALUES (?, NULL, NULL, NULL, ?, ?, ?, NULL)""",
                (ts_utc, lux, full_spectrum, ir)
            )
        self.commit()
    
    def insert_sound_reading(self, ts_utc: str, sound_rms: float):
        cursor = self.execute(
            "UPDATE readings SET sound_rms = ? WHERE ts_utc = ?",
            (sound_rms, ts_utc)
        )
        
        if cursor.rowcount == 0:
            self.execute(
                """INSERT INTO readings 
                   (ts_utc, temp_f, humidity, pressure, lux, full_spectrum, ir, sound_rms) 
                   VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, ?)""",
                (ts_utc, sound_rms)
            )
        self.commit()
    
    def insert_minute_stats(self, ts_min: str, stats: Dict[str, float]):
        self.execute(
            """INSERT OR REPLACE INTO minute_stats 
               (ts_min, temp_f_med, temp_f_mad, temp_f_std, hum_med, hum_mad, hum_std, 
                lux_med, lux_mad, lux_std, sound_med, sound_mad, sound_std, rows)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts_min, 
             stats.get('temp_f_med'), stats.get('temp_f_mad'), stats.get('temp_f_std'),
             stats.get('hum_med'), stats.get('hum_mad'), stats.get('hum_std'),
             stats.get('lux_med'), stats.get('lux_mad'), stats.get('lux_std'),
             stats.get('sound_med'), stats.get('sound_mad'), stats.get('sound_std'),
             stats['rows'])
        )
        self.commit()
    
    def insert_anomaly(self, ts_utc: str, metric: str, value: float, rule: str, details: str):
        self.execute(
            "INSERT INTO anomalies (ts_utc, metric, value, rule, details) VALUES (?, ?, ?, ?, ?)",
            (ts_utc, metric, value, rule, details)
        )
        self.commit()
    
    def get_readings_for_window(self, start_time: str, end_time: str) -> List[Tuple[str, float, float, float]]:
        cursor = self.execute(
            "SELECT ts_utc, temp_f, humidity, pressure FROM readings WHERE ts_utc BETWEEN ? AND ? ORDER BY ts_utc",
            (start_time, end_time)
        )
        return cursor.fetchall()
    
    def get_minute_stats_for_window(self, start_time: str, end_time: str) -> List[Tuple[str, float, float, float, float, float, float, int]]:
        cursor = self.execute(
            """SELECT ts_min, temp_f_med, temp_f_mad, temp_f_std, hum_med, hum_mad, hum_std, rows 
               FROM minute_stats WHERE ts_min BETWEEN ? AND ? ORDER BY ts_min""",
            (start_time, end_time)
        )
        return cursor.fetchall()
    
    def get_reading_count(self) -> int:
        cursor = self.execute("SELECT COUNT(*) FROM readings")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def get_last_reading_time(self) -> Optional[str]:
        cursor = self.execute("SELECT MAX(ts_utc) FROM readings")
        result = cursor.fetchone()
        return result[0] if result else None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def init_database(db_path: str = "sleepmon.db"):
    if not os.path.exists(db_path):
        logger.info(f"Creating db: {db_path}")
    
    with DatabaseManager(db_path) as db:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        for statement in statements:
            if statement:
                db.execute(statement)
        
        db.commit()
        logger.info("DB initialized")
        
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables: {tables}")
