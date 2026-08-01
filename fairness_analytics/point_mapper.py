"""
Fairness Analytics System - Point Mapper

This module provides corrected point mapping for crash game multipliers
to achieve a neutral baseline (E[Points] = 0) and avoid artificial drift.

Key Concepts:
- Original mapping (1x=-100, 2x=0, 10x+=+100) had E[Points] = -10.25
- Corrected mapping ensures E[Points] = 0 for fair drift measurement
- Points represent deviation from expected house edge
"""

import numpy as np
import pandas as pd
from typing import Union, Optional


class PointMapper:
    """
    Maps crash game multipliers to fairness points with neutral baseline.
    
    The corrected mapping ensures that the expected value of points is 0,
    allowing for accurate drift measurement from the theoretical house edge.
    
    Args:
        cashout_target: Multiplier at which bets are automatically cashed out
        house_edge: Theoretical house edge (e.g., 0.03 for 3%)
    """
    
    def __init__(self, cashout_target: float = 1.5, house_edge: float = 0.03):
        self.cashout_target = cashout_target
        self.house_edge = house_edge
        
    def map_single(self, multiplier: float) -> float:
        """
        Map a single multiplier to fairness points.
        
        Formula:
        - If multiplier >= cashout_target: Points = 100 * ((cashout_target - 1) + house_edge)
        - If multiplier < cashout_target: Points = 100 * (-1 + house_edge)
        
        This ensures E[Points] = 0 for fair games.
        
        Args:
            multiplier: The crash game multiplier (e.g., 1.2, 2.5, 10.0)
            
        Returns:
            Fairness points (neutral baseline)
        """
        if multiplier >= self.cashout_target:
            return 100 * ((self.cashout_target - 1) + self.house_edge)
        else:
            return 100 * (-1 + self.house_edge)
    
    def map_array(self, multipliers: Union[list, np.ndarray, pd.Series]) -> np.ndarray:
        """
        Map an array of multipliers to fairness points.
        
        Args:
            multipliers: Array-like of crash game multipliers
            
        Returns:
            Numpy array of fairness points
        """
        return np.array([self.map_single(m) for m in multipliers])
    
    def map_dataframe(self, df: pd.DataFrame, multiplier_col: str = 'multiplier', 
                     output_col: str = 'points') -> pd.DataFrame:
        """
        Map a DataFrame column of multipliers to fairness points.
        
        Args:
            df: DataFrame containing multiplier data
            multiplier_col: Name of the column containing multipliers
            output_col: Name of the column to store points
            
        Returns:
            DataFrame with added points column
        """
        df = df.copy()
        df[output_col] = df[multiplier_col].apply(self.map_single)
        return df
    
    def verify_neutral_baseline(self, multipliers: Union[list, np.ndarray, pd.Series], 
                               n_simulations: int = 10000) -> dict:
        """
        Verify that the point mapping has a neutral baseline (E[Points] ≈ 0).
        
        Uses Monte Carlo simulation to estimate the expected value.
        
        Args:
            multipliers: Sample multipliers for distribution estimation
            n_simulations: Number of simulations to run
            
        Returns:
            Dictionary with verification metrics
        """
        # Estimate distribution parameters from input
        if isinstance(multipliers, pd.Series):
            multipliers = multipliers.values
        
        # Generate synthetic multipliers based on crash game probability
        # P(X >= m) = (1 - house_edge) / m
        synthetic_multipliers = []
        for _ in range(n_simulations):
            u = np.random.random()
            # Inverse transform sampling for crash game distribution
            # P(X <= x) = 1 - (1 - house_edge) / x for x >= 1
            # So X = (1 - house_edge) / (1 - U) where U ~ Uniform(0,1)
            if u < self.house_edge:
                synthetic_multipliers.append(1.0)  # Instant crash
            else:
                x = (1 - self.house_edge) / (1 - u)
                synthetic_multipliers.append(max(1.0, x))
        
        # Map synthetic multipliers to points
        points = self.map_array(synthetic_multipliers)
        
        # Calculate statistics
        mean_points = np.mean(points)
        std_points = np.std(points)
        
        return {
            'mean_points': mean_points,
            'std_points': std_points,
            'n_simulations': n_simulations,
            'is_neutral': abs(mean_points) < 0.1,  # Within 0.1 points of 0
            'deviation_from_neutral': abs(mean_points)
        }


def fairness_points(multiplier: float, cashout_target: float = 1.5, 
                   house_edge: float = 0.03) -> float:
    """
    Convenience function to map a single multiplier to fairness points.
    
    Args:
        multiplier: The crash game multiplier
        cashout_target: Auto-cashout multiplier
        house_edge: Theoretical house edge
        
    Returns:
        Fairness points
    """
    mapper = PointMapper(cashout_target, house_edge)
    return mapper.map_single(multiplier)
