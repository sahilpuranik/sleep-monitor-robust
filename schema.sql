-- Sleep Monitor Database Schema
-- Enable WAL mode for safety and speed

-- Raw sensor readings (one per second)
CREATE TABLE IF NOT EXISTS readings (
    ts_utc TEXT PRIMARY KEY,
    temp_f REAL NOT NULL,
    humidity REAL NOT NULL,
    pressure REAL NOT NULL,
    lux REAL,
    full_spectrum REAL,
    ir REAL,
    sound_rms REAL
);

-- Per-minute aggregated statistics
CREATE TABLE IF NOT EXISTS minute_stats (
    ts_min TEXT PRIMARY KEY,
    temp_f_med REAL NOT NULL,
    temp_f_mad REAL NOT NULL,
    temp_f_std REAL NOT NULL,
    hum_med REAL NOT NULL,
    hum_mad REAL NOT NULL,
    hum_std REAL NOT NULL,
    lux_med REAL,
    lux_mad REAL,
    lux_std REAL,
    sound_med REAL,
    sound_mad REAL,
    sound_std REAL,
    rows INTEGER NOT NULL
);

-- Configuration and thresholds
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Anomaly records
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    rule TEXT NOT NULL,
    details TEXT NOT NULL
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(ts_utc);
CREATE INDEX IF NOT EXISTS idx_anom_ts ON anomalies(ts_utc);

-- Insert default configuration values
INSERT OR REPLACE INTO config (key, value) VALUES
    ('robust_z_threshold', '6'),
    ('temp_roc_limit', '3'),
    ('humidity_roc_limit', '8'),
    ('lux_roc_limit', '100'),
    ('sound_roc_limit', '10'),
    ('temp_min', '50'),
    ('temp_max', '90'),
    ('humidity_min', '10'),
    ('humidity_max', '85'),
    ('lux_min', '0'),
    ('lux_max', '10000'),
    ('sound_min', '0'),
    ('sound_max', '100'),
    ('cooldown_minutes', '15'),
    ('last_alert_temp', ''),
    ('last_alert_humidity', ''),
    ('last_alert_pressure', ''),
    ('last_alert_lux', ''),
    ('last_alert_sound', '');
