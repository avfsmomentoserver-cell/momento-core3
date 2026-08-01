"""
Fairness Analytics System - Drift Calculator

This module calculates drift from the theoretical house edge and measures
the rate of balance (how quickly deviations return to fairness).

Key Metrics:
- Realized House Edge: Actual edge observed over time
- Drift: Realized Edge - Theoretical Edge
- Rate of Balance: Half-life and mean reversion metrics
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from statsmodels.tsa.ar_model import AutoReg
from scipy.optimize import minimize_scalar


class DriftCalculator:
    """
    Calculates drift and rate of balance metrics for crash game data.
    
    Args:
        house_edge: Theoretical house edge (e.g., 0.03 for 3%)
        cashout_target: Multiplier at which bets are automatically cashed out
    """
    
    def __init__(self, house_edge: float = 0.03, cashout_target: float = 1.5):
        self.house_edge = house_edge
        self.cashout_target = cashout_target
        
    def calculate_pnl(self, df: pd.DataFrame, multiplier_col: str = 'multiplier',
                     bet_size: float = 1.0) -> pd.DataFrame:
        """
        Calculate profit and loss for each round.
        
        Args:
            df: DataFrame containing multiplier data
            multiplier_col: Name of the column containing multipliers
            bet_size: Size of each bet
            
        Returns:
            DataFrame with added P&L columns
        """
        df = df.copy()
        df['bet_size'] = bet_size
        
        # Calculate P&L: Win = (cashout_target - 1) * bet_size, Loss = -bet_size
        df['pnl'] = np.where(
            df[multiplier_col] >= self.cashout_target,
            (self.cashout_target - 1) * bet_size,
            -bet_size
        )
        
        # Casino profit is negative of player P&L
        df['casino_profit'] = -df['pnl']
        
        return df
    
    def calculate_metrics(self, df: pd.DataFrame, pnl_col: str = 'pnl',
                         bet_size_col: str = 'bet_size') -> pd.DataFrame:
        """
        Calculate cumulative drift and realized house edge.
        
        Args:
            df: DataFrame containing P&L data
            pnl_col: Name of the column containing P&L
            bet_size_col: Name of the column containing bet sizes
            
        Returns:
            DataFrame with added metrics columns
        """
        df = df.copy()
        
        # Cumulative P&L
        df['cumulative_pnl'] = df[pnl_col].cumsum()
        
        # Cumulative volume (total bets)
        df['cumulative_volume'] = df[bet_size_col].cumsum()
        
        # Realized house edge: - (Total P&L) / (Total Volume)
        df['realized_edge'] = -df['cumulative_pnl'] / df['cumulative_volume']
        
        # Drift: Realized Edge - Theoretical Edge
        df['drift'] = df['realized_edge'] - self.house_edge
        
        # Drift percentage
        df['drift_pct'] = df['drift'] * 100
        
        return df
    
    def calculate_rate_of_balance(self, drift_series: pd.Series) -> dict:
        """
        Calculate rate of balance metrics from drift series.
        
        Args:
            drift_series: Series of drift values
            
        Returns:
            Dictionary with rate of balance metrics
        """
        drift_values = drift_series.dropna().values
        
        if len(drift_values) < 2:
            return {
                'half_life': np.nan,
                'mean_reversion_rate': np.nan,
                'is_mean_reverting': False,
                'error': 'Insufficient data'
            }
        
        # Calculate half-life: smallest h where |E[D_{n+h}]| < 0.5 * |D_n|
        half_life = self._calculate_half_life(drift_values)
        
        # Calculate mean reversion rate from AR(1) model
        mean_reversion_rate = self._calculate_mean_reversion(drift_values)
        
        # Check if mean-reverting (phi < 1)
        is_mean_reverting = mean_reversion_rate > 0
        
        return {
            'half_life': half_life,
            'mean_reversion_rate': mean_reversion_rate,
            'is_mean_reverting': is_mean_reverting
        }
    
    def _calculate_half_life(self, drift_values: np.ndarray) -> float:
        """Calculate the half-life of drift deviations."""
        n = len(drift_values)
        
        for h in range(1, min(100, n)):
            if h >= n:
                break
            future_drift = drift_values[h:]
            current_drift = drift_values[:n-h]
            
            if len(future_drift) == 0 or len(current_drift) == 0:
                continue
            
            # Check if expected future drift is less than 50% of current
            if abs(np.mean(future_drift)) < 0.5 * abs(np.mean(current_drift)):
                return h
        
        return 100.0  # Default if not found
    
    def _calculate_mean_reversion(self, drift_values: np.ndarray) -> float:
        """Calculate mean reversion rate from AR(1) model."""
        try:
            # Create AR(1) model
            model = AutoReg(drift_values, lags=1).fit()
            phi = model.params[1] if len(model.params) > 1 else 0.9
            
            # Mean reversion rate: -ln(phi) if phi < 1
            if phi < 1:
                return -np.log(phi)
            else:
                return 0.0
        except:
            return 0.0
    
    def calculate_statistics(self, df: pd.DataFrame, drift_col: str = 'drift') -> dict:
        """
        Calculate comprehensive statistics for drift analysis.
        
        Args:
            df: DataFrame containing drift data
            drift_col: Name of the column containing drift values
            
        Returns:
            Dictionary with statistical metrics
        """
        drift_values = df[drift_col].dropna().values
        
        return {
            'mean_drift': np.mean(drift_values),
            'std_drift': np.std(drift_values),
            'min_drift': np.min(drift_values),
            'max_drift': np.max(drift_values),
            'final_drift': drift_values[-1] if len(drift_values) > 0 else np.nan,
            'n_rounds': len(drift_values)
        }
    
    def detect_anomalies(self, df: pd.DataFrame, drift_col: str = 'drift',
                        threshold_std: float = 3.0) -> pd.DataFrame:
        """
        Detect anomalous periods where drift exceeds threshold.
        
        Args:
            df: DataFrame containing drift data
            drift_col: Name of the column containing drift values
            threshold_std: Number of standard deviations to use as threshold
            
        Returns:
            DataFrame with anomaly flags
        """
        df = df.copy()
        drift_values = df[drift_col].dropna().values
        
        mean_drift = np.mean(drift_values)
        std_drift = np.std(drift_values)
        
        # Flag anomalies
        df['is_anomaly'] = abs(df[drift_col] - mean_drift) > (threshold_std * std_drift)
        
        # Calculate anomaly duration
        df['anomaly_group'] = (df['is_anomaly'] != df['is_anomaly'].shift(1)).cumsum()
        anomaly_durations = df[df['is_anomaly']].groupby('anomaly_group').size()
        
        # Add anomaly metrics
        df['anomaly_duration'] = df['anomaly_group'].map(anomaly_durations)
        
        return df


def calculate_drift_metrics(df: pd.DataFrame, house_edge: float = 0.03,
                           cashout_target: float = 1.5) -> pd.DataFrame:
    """
    Convenience function to calculate all drift metrics for a DataFrame.
    
    Args:
        df: DataFrame containing multiplier data
        house_edge: Theoretical house edge
        cashout_target: Auto-cashout multiplier
        
    Returns:
        DataFrame with all drift metrics
    """
    calculator = DriftCalculator(house_edge, cashout_target)
    df = calculator.calculate_pnl(df)
    df = calculator.calculate_metrics(df)
    return df
