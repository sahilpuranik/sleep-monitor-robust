#!/usr/bin/env python3
"""
Statistics utilities for Sleep Monitor
Handles robust statistics, anomaly detection, and aggregation
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit"""
    return (celsius * 9/5) + 32

def robust_z_score(x: float, median: float, mad: float) -> float:
    """
    Calculate robust z-score using Median Absolute Deviation
    Safe version that handles division by zero
    """
    if mad == 0:
        return 0.0
    return abs(x - median) / (1.4826 * mad)

def median_absolute_deviation(data: List[float]) -> float:
    """Calculate Median Absolute Deviation (MAD)"""
    if not data:
        return 0.0
    
    median = np.median(data)
    mad = np.median([abs(x - median) for x in data])
    return mad

def calculate_minute_stats(readings: List[Tuple]) -> Dict[str, float]:
    """
    Calculate per-minute statistics from readings
    Supports both old format (ts, temp, hum, pressure) and new format with light/sound
    Returns dict with all available sensor statistics
    """
    if not readings:
        return {
            'temp_f_med': 0.0, 'temp_f_mad': 0.0, 'temp_f_std': 0.0,
            'hum_med': 0.0, 'hum_mad': 0.0, 'hum_std': 0.0,
            'lux_med': 0.0, 'lux_mad': 0.0, 'lux_std': 0.0,
            'sound_med': 0.0, 'sound_mad': 0.0, 'sound_std': 0.0,
            'rows': 0
        }
    
    # Extract values based on reading format
    temps = [reading[1] for reading in readings if reading[1] is not None]
    humidities = [reading[2] for reading in readings if reading[2] is not None]
    
    # Check if we have extended readings (with light/sound data)
    has_light = len(readings[0]) > 4 and readings[0][4] is not None
    has_sound = len(readings[0]) > 7 and readings[0][7] is not None
    
    lux_values = []
    sound_values = []
    
    if has_light:
        lux_values = [reading[4] for reading in readings if reading[4] is not None]
    if has_sound:
        sound_values = [reading[7] for reading in readings if reading[7] is not None]
    
    # Calculate statistics for temperature and humidity
    temp_median = np.median(temps) if temps else 0.0
    temp_mad = median_absolute_deviation(temps) if temps else 0.0
    temp_std = np.std(temps) if len(temps) > 1 else 0.0
    
    hum_median = np.median(humidities) if humidities else 0.0
    hum_mad = median_absolute_deviation(humidities) if humidities else 0.0
    hum_std = np.std(humidities) if len(humidities) > 1 else 0.0
    
    # Calculate statistics for light
    lux_median = np.median(lux_values) if lux_values else 0.0
    lux_mad = median_absolute_deviation(lux_values) if lux_values else 0.0
    lux_std = np.std(lux_values) if len(lux_values) > 1 else 0.0
    
    # Calculate statistics for sound
    sound_median = np.median(sound_values) if sound_values else 0.0
    sound_mad = median_absolute_deviation(sound_values) if sound_values else 0.0
    sound_std = np.std(sound_values) if len(sound_values) > 1 else 0.0
    
    return {
        'temp_f_med': temp_median,
        'temp_f_mad': temp_mad,
        'temp_f_std': temp_std,
        'hum_med': hum_median,
        'hum_mad': hum_mad,
        'hum_std': hum_std,
        'lux_med': lux_median,
        'lux_mad': lux_mad,
        'lux_std': lux_std,
        'sound_med': sound_median,
        'sound_mad': sound_mad,
        'sound_std': sound_std,
        'rows': len(readings)
    }

def detect_anomalies(
    current_reading: Tuple,
    baseline_stats: Dict[str, float],
    config: Dict[str, str],
    last_alert_times: Dict[str, str]
) -> List[Dict[str, any]]:
    """
    Detect anomalies using multiple rules:
    1. Robust z-score
    2. Rate of change
    3. Guardrails
    4. Cooldown checks
    Supports both old format (ts, temp, hum, pressure) and new format with light/sound
    """
    ts_utc = current_reading[0]
    temp_f = current_reading[1] if current_reading[1] is not None else None
    humidity = current_reading[2] if current_reading[2] is not None else None
    pressure = current_reading[3] if current_reading[3] is not None else None
    
    # Extract new sensor values if available
    lux = current_reading[4] if len(current_reading) > 4 and current_reading[4] is not None else None
    sound_rms = current_reading[7] if len(current_reading) > 7 and current_reading[7] is not None else None
    
    anomalies = []
    
    # Parse config values
    robust_z_threshold = float(config.get('robust_z_threshold', '6'))
    temp_roc_limit = float(config.get('temp_roc_limit', '3'))
    humidity_roc_limit = float(config.get('humidity_roc_limit', '8'))
    lux_roc_limit = float(config.get('lux_roc_limit', '100'))
    sound_roc_limit = float(config.get('sound_roc_limit', '10'))
    temp_min = float(config.get('temp_min', '50'))
    temp_max = float(config.get('temp_max', '90'))
    humidity_min = float(config.get('humidity_min', '10'))
    humidity_max = float(config.get('humidity_max', '85'))
    lux_min = float(config.get('lux_min', '0'))
    lux_max = float(config.get('lux_max', '10000'))
    sound_min = float(config.get('sound_min', '0'))
    sound_max = float(config.get('sound_max', '100'))
    cooldown_minutes = int(config.get('cooldown_minutes', '15'))
    
    current_time = datetime.fromisoformat(ts_utc.replace('Z', '+00:00'))
    
    # 1. Robust Z-Score Anomaly Detection
    if baseline_stats.get('temp_f_mad', 0) > 0:
        temp_z = robust_z_score(temp_f, baseline_stats['temp_f_med'], baseline_stats['temp_f_mad'])
        if temp_z > robust_z_threshold:
            # Check cooldown
            last_alert = last_alert_times.get('temp', '')
            if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                anomalies.append({
                    'ts_utc': ts_utc,
                    'metric': 'temp_f',
                    'value': temp_f,
                    'rule': 'robust_z_score',
                    'details': f'Z-score: {temp_z:.2f} (threshold: {robust_z_threshold})'
                })
    
    if baseline_stats.get('hum_mad', 0) > 0:
        hum_z = robust_z_score(humidity, baseline_stats['hum_med'], baseline_stats['hum_mad'])
        if hum_z > robust_z_threshold:
            # Check cooldown
            last_alert = last_alert_times.get('humidity', '')
            if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                anomalies.append({
                    'ts_utc': ts_utc,
                    'metric': 'humidity',
                    'value': humidity,
                    'rule': 'robust_z_score',
                    'details': f'Z-score: {hum_z:.2f} (threshold: {robust_z_threshold})'
                })
    
    # 2. Guardrail Anomaly Detection
    if temp_f < temp_min or temp_f > temp_max:
        last_alert = last_alert_times.get('temp', '')
        if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
            anomalies.append({
                'ts_utc': ts_utc,
                'metric': 'temp_f',
                'value': temp_f,
                'rule': 'guardrail',
                'details': f'Value {temp_f:.1f}°F outside range [{temp_min}, {temp_max}]°F'
            })
    
    if humidity and (humidity < humidity_min or humidity > humidity_max):
        last_alert = last_alert_times.get('humidity', '')
        if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
            anomalies.append({
                'ts_utc': ts_utc,
                'metric': 'humidity',
                'value': humidity,
                'rule': 'guardrail',
                'details': f'Value {humidity:.1f}% outside range [{humidity_min}, {humidity_max}]%'
            })
    
    # Light sensor anomaly detection
    if lux is not None:
        # Robust Z-Score for light
        if baseline_stats.get('lux_mad', 0) > 0:
            lux_z = robust_z_score(lux, baseline_stats['lux_med'], baseline_stats['lux_mad'])
            if lux_z > robust_z_threshold:
                last_alert = last_alert_times.get('lux', '')
                if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                    anomalies.append({
                        'ts_utc': ts_utc,
                        'metric': 'lux',
                        'value': lux,
                        'rule': 'robust_z_score',
                        'details': f'Z-score: {lux_z:.2f} (threshold: {robust_z_threshold})'
                    })
        
        # Guardrails for light
        if lux < lux_min or lux > lux_max:
            last_alert = last_alert_times.get('lux', '')
            if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                anomalies.append({
                    'ts_utc': ts_utc,
                    'metric': 'lux',
                    'value': lux,
                    'rule': 'guardrail',
                    'details': f'Value {lux:.1f} lux outside range [{lux_min}, {lux_max}] lux'
                })
    
    # Sound sensor anomaly detection
    if sound_rms is not None:
        # Robust Z-Score for sound
        if baseline_stats.get('sound_mad', 0) > 0:
            sound_z = robust_z_score(sound_rms, baseline_stats['sound_med'], baseline_stats['sound_mad'])
            if sound_z > robust_z_threshold:
                last_alert = last_alert_times.get('sound', '')
                if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                    anomalies.append({
                        'ts_utc': ts_utc,
                        'metric': 'sound_rms',
                        'value': sound_rms,
                        'rule': 'robust_z_score',
                        'details': f'Z-score: {sound_z:.2f} (threshold: {robust_z_threshold})'
                    })
        
        # Guardrails for sound
        if sound_rms < sound_min or sound_rms > sound_max:
            last_alert = last_alert_times.get('sound', '')
            if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
                anomalies.append({
                    'ts_utc': ts_utc,
                    'metric': 'sound_rms',
                    'value': sound_rms,
                    'rule': 'guardrail',
                    'details': f'Value {sound_rms:.1f} RMS outside range [{sound_min}, {sound_max}] RMS'
                })
    
    return anomalies

def should_send_alert(last_alert_time: str, current_time: datetime, cooldown_minutes: int) -> bool:
    """Check if enough time has passed since last alert to send a new one"""
    if not last_alert_time:
        return True
    
    try:
        last_alert = datetime.fromisoformat(last_alert_time.replace('Z', '+00:00'))
        time_diff = current_time - last_alert
        return time_diff.total_seconds() > (cooldown_minutes * 60)
    except ValueError:
        # If we can't parse the last alert time, allow the alert
        return True

def aggregate_readings_to_minutes(readings: List[Tuple]) -> Dict[str, List[Tuple]]:
    """
    Group readings by minute for statistical analysis
    Supports both old format (ts, temp, hum, pressure) and new format with light/sound
    Returns dict with minute timestamps as keys
    """
    minute_groups = {}
    
    for reading in readings:
        ts_utc = reading[0]
        # Convert to datetime and round down to minute
        dt = datetime.fromisoformat(ts_utc.replace('Z', '+00:00'))
        minute_key = dt.replace(second=0, microsecond=0).isoformat()
        
        if minute_key not in minute_groups:
            minute_groups[minute_key] = []
        
        minute_groups[minute_key].append(reading)
    
    return minute_groups

def calculate_baseline_thresholds(readings: List[Tuple]) -> Dict[str, float]:
    """
    Calculate baseline thresholds from calibration data
    Supports both old format (ts, temp, hum, pressure) and new format with light/sound
    Returns dict with median and MAD values for all available sensors
    """
    if not readings:
        return {}
    
    # Extract values based on reading format
    temps = [reading[1] for reading in readings if reading[1] is not None]
    humidities = [reading[2] for reading in readings if reading[2] is not None]
    
    # Check if we have extended readings (with light/sound data)
    has_light = len(readings[0]) > 4 and readings[0][4] is not None
    has_sound = len(readings[0]) > 7 and readings[0][7] is not None
    
    lux_values = []
    sound_values = []
    
    if has_light:
        lux_values = [reading[4] for reading in readings if reading[4] is not None]
    if has_sound:
        sound_values = [reading[7] for reading in readings if reading[7] is not None]
    
    # Calculate robust statistics for temperature and humidity
    temp_median = np.median(temps) if temps else 0.0
    temp_mad = median_absolute_deviation(temps) if temps else 0.0
    temp_std = np.std(temps) if len(temps) > 1 else 0.0
    
    hum_median = np.median(humidities) if humidities else 0.0
    hum_mad = median_absolute_deviation(humidities) if humidities else 0.0
    hum_std = np.std(humidities) if len(humidities) > 1 else 0.0
    
    # Calculate robust statistics for light
    lux_median = np.median(lux_values) if lux_values else 0.0
    lux_mad = median_absolute_deviation(lux_values) if lux_values else 0.0
    lux_std = np.std(lux_values) if len(lux_values) > 1 else 0.0
    
    # Calculate robust statistics for sound
    sound_median = np.median(sound_values) if sound_values else 0.0
    sound_mad = median_absolute_deviation(sound_values) if sound_values else 0.0
    sound_std = np.std(sound_values) if len(sound_values) > 1 else 0.0
    
    return {
        'temp_f_med': temp_median,
        'temp_f_mad': temp_mad,
        'temp_f_std': temp_std,
        'hum_med': hum_median,
        'hum_mad': hum_mad,
        'hum_std': hum_std,
        'lux_med': lux_median,
        'lux_mad': lux_mad,
        'lux_std': lux_std,
        'sound_med': sound_median,
        'sound_mad': sound_mad,
        'sound_std': sound_std
    }
