"""
SEWA - Sepsis Early Warning Agent
Artifact 1: Trend Recognition Engine

This module performs statistical trend analysis on patient vital signs
to detect temporal patterns indicative of early sepsis risk.

Key Features:
- Multi-window exponential moving averages (1h, 3h, 6h)
- Slope computation (directional trends)
- Volatility measurement (rolling standard deviation)
- Acceleration detection (second derivative)
- Handles missing data and irregular timestamps

Author: SEWA Development Team
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class VitalSign:
    """Container for a single vital sign measurement."""
    timestamp: datetime
    value: float
    name: str
    

class TrendRecognitionEngine:
    """
    Statistical trend analysis engine for patient vital signs.
    
    Computes trends without any machine learning - pure statistical methods.
    All outputs are deterministic and clinically interpretable.
    """
    
    # Window sizes in hours
    WINDOWS = {
        'short': 1.0,   # 1 hour - acute changes
        'medium': 3.0,  # 3 hours - persistent trends
        'long': 6.0     # 6 hours - baseline drift
    }
    
    # EMA smoothing factors (alpha = 2 / (N + 1))
    # Approximate N based on typical 15-min measurement intervals
    EMA_SPANS = {
        'short': 4,   # ~1 hour with 15-min intervals
        'medium': 12, # ~3 hours
        'long': 24    # ~6 hours
    }
    
    def __init__(self, vital_names: List[str]):
        """
        Initialize trend engine for specific vital signs.
        
        Args:
            vital_names: List of vital sign names to track (e.g., ['lactate', 'map', 'hr'])
        """
        self.vital_names = vital_names
        self.data_buffer = {name: [] for name in vital_names}
        
    def add_measurement(self, vital_name: str, timestamp: datetime, value: float):
        """
        Add a new vital sign measurement to the buffer.
        
        Args:
            vital_name: Name of vital sign (must be in vital_names)
            timestamp: Measurement timestamp
            value: Measured value
        """
        if vital_name not in self.vital_names:
            raise ValueError(f"Unknown vital sign: {vital_name}")
        
        if not np.isnan(value):  # Only add valid measurements
            self.data_buffer[vital_name].append(
                VitalSign(timestamp=timestamp, value=value, name=vital_name)
            )
    
    def _get_windowed_data(self, vital_name: str, current_time: datetime, 
                           window_hours: float) -> List[VitalSign]:
        """
        Extract measurements within a time window.
        
        Args:
            vital_name: Vital sign name
            current_time: Reference timestamp
            window_hours: Window size in hours
            
        Returns:
            List of VitalSign objects within window
        """
        cutoff_time = current_time - timedelta(hours=window_hours)
        windowed = [
            vs for vs in self.data_buffer[vital_name]
            if vs.timestamp >= cutoff_time and vs.timestamp <= current_time
        ]
        return sorted(windowed, key=lambda x: x.timestamp)
    
    def _compute_ema(self, values: np.ndarray, span: int) -> Optional[float]:
        """
        Compute exponential moving average.
        
        Args:
            values: Array of measurements
            span: EMA span (larger = more smoothing)
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(values) == 0:
            return None
        
        # Use pandas EMA for consistency with clinical applications
        series = pd.Series(values)
        ema = series.ewm(span=span, adjust=False).mean()
        return float(ema.iloc[-1])
    
    def _compute_slope(self, timestamps: List[datetime], values: np.ndarray) -> Optional[float]:
        """
        Compute linear regression slope (trend direction).
        
        Args:
            timestamps: List of measurement times
            values: Array of measured values
            
        Returns:
            Slope in units per hour, or None if insufficient data
        """
        if len(values) < 2:
            return None
        
        # Convert timestamps to hours since first measurement
        t0 = timestamps[0]
        time_hours = np.array([(t - t0).total_seconds() / 3600 for t in timestamps])
        
        # Linear regression: slope = cov(x,y) / var(x)
        if np.var(time_hours) == 0:
            return 0.0
        
        slope = np.cov(time_hours, values)[0, 1] / np.var(time_hours)
        return float(slope)
    
    def _compute_volatility(self, values: np.ndarray) -> Optional[float]:
        """
        Compute rolling standard deviation (volatility measure).
        
        Args:
            values: Array of measurements
            
        Returns:
            Standard deviation or None if insufficient data
        """
        if len(values) < 2:
            return None
        return float(np.std(values, ddof=1))
    
    def _compute_acceleration(self, short_slope: Optional[float], 
                             long_slope: Optional[float]) -> Optional[float]:
        """
        Compute trend acceleration (second derivative).
        
        Positive acceleration = trend intensifying
        Negative acceleration = trend stabilizing
        
        Args:
            short_slope: Short-term slope (1h)
            long_slope: Long-term slope (6h)
            
        Returns:
            Acceleration metric or None
        """
        if short_slope is None or long_slope is None:
            return None
        return short_slope - long_slope
    
    def extract_features(self, vital_name: str, current_time: datetime) -> Dict[str, Optional[float]]:
        """
        Extract all trend features for a single vital sign.
        
        This is the PRIMARY METHOD for feature extraction.
        
        Args:
            vital_name: Name of vital sign
            current_time: Current timestamp for trend computation
            
        Returns:
            Dictionary of trend features with keys:
            - {vital}_ema_{window}: Exponential moving average
            - {vital}_slope_{window}: Linear trend (units/hour)
            - {vital}_volatility_{window}: Rolling std dev
            - {vital}_acceleration: Trend acceleration metric
        """
        features = {}
        slopes = {}
        
        # Compute features for each window
        for window_name, window_hours in self.WINDOWS.items():
            windowed_data = self._get_windowed_data(vital_name, current_time, window_hours)
            
            if len(windowed_data) == 0:
                # No data in this window
                features[f'{vital_name}_ema_{window_name}'] = None
                features[f'{vital_name}_slope_{window_name}'] = None
                features[f'{vital_name}_volatility_{window_name}'] = None
                slopes[window_name] = None
                continue
            
            # Extract values and timestamps
            values = np.array([vs.value for vs in windowed_data])
            timestamps = [vs.timestamp for vs in windowed_data]
            
            # Compute EMA
            span = self.EMA_SPANS[window_name]
            ema = self._compute_ema(values, span)
            features[f'{vital_name}_ema_{window_name}'] = ema
            
            # Compute slope (units per hour)
            slope = self._compute_slope(timestamps, values)
            features[f'{vital_name}_slope_{window_name}'] = slope
            slopes[window_name] = slope
            
            # Compute volatility
            volatility = self._compute_volatility(values)
            features[f'{vital_name}_volatility_{window_name}'] = volatility
        
        # Compute acceleration (short-term vs long-term slope)
        acceleration = self._compute_acceleration(slopes['short'], slopes['long'])
        features[f'{vital_name}_acceleration'] = acceleration
        
        return features
    
    def extract_all_features(self, current_time: datetime) -> Dict[str, Optional[float]]:
        """
        Extract trend features for ALL vital signs.
        
        This produces the complete feature vector for downstream ML models.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Dictionary mapping feature names to values
        """
        all_features = {}
        
        for vital_name in self.vital_names:
            vital_features = self.extract_features(vital_name, current_time)
            all_features.update(vital_features)
        
        return all_features
    
    def get_data_quality_metrics(self, current_time: datetime) -> Dict[str, Dict[str, float]]:
        """
        Compute data quality metrics for each vital sign.
        
        Useful for detecting missing data, sensor failures, or stale measurements.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Dict with quality metrics per vital sign:
            - measurement_count_6h: Number of measurements in past 6 hours
            - time_since_last: Hours since last measurement
            - coverage_ratio: Fraction of 6h window with data
        """
        quality = {}
        
        for vital_name in self.vital_names:
            windowed = self._get_windowed_data(vital_name, current_time, 6.0)
            
            if len(windowed) == 0:
                quality[vital_name] = {
                    'measurement_count_6h': 0,
                    'time_since_last': float('inf'),
                    'coverage_ratio': 0.0
                }
                continue
            
            # Time since last measurement
            last_measurement = windowed[-1].timestamp
            hours_since = (current_time - last_measurement).total_seconds() / 3600
            
            # Coverage ratio (assuming 15-min intervals = 24 measurements in 6h)
            expected_measurements = 24
            coverage = len(windowed) / expected_measurements
            
            quality[vital_name] = {
                'measurement_count_6h': len(windowed),
                'time_since_last': hours_since,
                'coverage_ratio': min(coverage, 1.0)
            }
        
        return quality
    
    def clear_old_data(self, current_time: datetime, retention_hours: float = 24.0):
        """
        Remove measurements older than retention period to prevent memory bloat.
        
        Args:
            current_time: Current timestamp
            retention_hours: How many hours of history to keep
        """
        cutoff_time = current_time - timedelta(hours=retention_hours)
        
        for vital_name in self.vital_names:
            self.data_buffer[vital_name] = [
                vs for vs in self.data_buffer[vital_name]
                if vs.timestamp >= cutoff_time
            ]