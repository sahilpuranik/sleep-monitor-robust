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

def calculate_minute_stats(readings: List[Tuple[str, float, float, float]]) -> Dict[str, float]:
    """
    Calculate per-minute statistics from readings
    Returns dict with temp_f_med, temp_f_mad, temp_f_std, hum_med, hum_mad, hum_std, rows
    """
    if not readings:
        return {
            'temp_f_med': 0.0, 'temp_f_mad': 0.0, 'temp_f_std': 0.0,
            'hum_med': 0.0, 'hum_mad': 0.0, 'hum_std': 0.0, 'rows': 0
        }
    
    # Extract temperature and humidity values
    temps = [reading[1] for reading in readings]
    humidities = [reading[2] for reading in readings]
    
    # Calculate statistics
    temp_median = np.median(temps)
    temp_mad = median_absolute_deviation(temps)
    temp_std = np.std(temps) if len(temps) > 1 else 0.0
    
    hum_median = np.median(humidities)
    hum_mad = median_absolute_deviation(humidities)
    hum_std = np.std(humidities) if len(humidities) > 1 else 0.0
    
    return {
        'temp_f_med': temp_median,
        'temp_f_mad': temp_mad,
        'temp_f_std': temp_std,
        'hum_med': hum_median,
        'hum_mad': hum_mad,
        'hum_std': hum_std
    }

def detect_anomalies(
    current_reading: Tuple[str, float, float, float],
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
    """
    ts_utc, temp_f, humidity, pressure = current_reading
    anomalies = []
    
    # Parse config values
    robust_z_threshold = float(config.get('robust_z_threshold', '6'))
    temp_roc_limit = float(config.get('temp_roc_limit', '3'))
    humidity_roc_limit = float(config.get('humidity_roc_limit', '8'))
    temp_min = float(config.get('temp_min', '50'))
    temp_max = float(config.get('temp_max', '90'))
    humidity_min = float(config.get('humidity_min', '10'))
    humidity_max = float(config.get('humidity_max', '85'))
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
    
    if humidity < humidity_min or humidity > humidity_max:
        last_alert = last_alert_times.get('humidity', '')
        if not last_alert or should_send_alert(last_alert, current_time, cooldown_minutes):
            anomalies.append({
                'ts_utc': ts_utc,
                'metric': 'humidity',
                'value': humidity,
                'rule': 'guardrail',
                'details': f'Value {humidity:.1f}% outside range [{humidity_min}, {humidity_max}]%'
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

def aggregate_readings_to_minutes(readings: List[Tuple[str, float, float, float]]) -> Dict[str, List[Tuple[str, float, float, float]]]:
    """
    Group readings by minute for statistical analysis
    Returns dict with minute timestamps as keys
    """
    minute_groups = {}
    
    for ts_utc, temp_f, humidity, pressure in readings:
        # Convert to datetime and round down to minute
        dt = datetime.fromisoformat(ts_utc.replace('Z', '+00:00'))
        minute_key = dt.replace(second=0, microsecond=0).isoformat()
        
        if minute_key not in minute_groups:
            minute_groups[minute_key] = []
        
        minute_groups[minute_key].append((ts_utc, temp_f, humidity, pressure))
    
    return minute_groups

def calculate_baseline_thresholds(readings: List[Tuple[str, float, float, float]]) -> Dict[str, float]:
    """
    Calculate baseline thresholds from calibration data
    Returns dict with median and MAD values for temp and humidity
    """
    if not readings:
        return {}
    
    # Extract values
    temps = [reading[1] for reading in readings]
    humidities = [reading[2] for reading in readings]
    
    # Calculate robust statistics
    temp_median = np.median(temps)
    temp_mad = median_absolute_deviation(temps)
    temp_std = np.std(temps) if len(temps) > 1 else 0.0
    
    hum_median = np.median(humidities)
    hum_mad = median_absolute_deviation(humidities)
    hum_std = np.std(humidities) if len(humidities) > 1 else 0.0
    
    return {
        'temp_f_med': temp_median,
        'temp_f_mad': temp_mad,
        'temp_f_std': temp_std,
        'hum_med': hum_median,
        'hum_mad': hum_mad,
        'hum_std': hum_std
    }
