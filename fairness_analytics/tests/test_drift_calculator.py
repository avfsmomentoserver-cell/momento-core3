"""
Unit tests for DriftCalculator class.
"""

import pytest
import numpy as np
import pandas as pd
from fairness_analytics.drift_calculator import DriftCalculator, calculate_drift_metrics


class TestDriftCalculator:
    """Tests for DriftCalculator class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        calculator = DriftCalculator()
        assert calculator.house_edge == 0.03
        assert calculator.cashout_target == 1.5
    
    def test_init_custom(self):
        """Test custom initialization."""
        calculator = DriftCalculator(house_edge=0.05, cashout_target=2.0)
        assert calculator.house_edge == 0.05
        assert calculator.cashout_target == 2.0
    
    def test_calculate_pnl_win(self):
        """Test P&L calculation for winning round."""
        calculator = DriftCalculator(house_edge=0.03, cashout_target=1.5)
        
        df = pd.DataFrame({
            'round_id': [1],
            'multiplier': [2.0]
        })
        
        result = calculator.calculate_pnl(df)
        
        assert 'pnl' in result.columns
        assert 'casino_profit' in result.columns
        assert result.loc[0, 'pnl'] == pytest.approx(0.5, abs=0.01)  # (1.5 - 1) * 1.0
        assert result.loc[0, 'casino_profit'] == pytest.approx(-0.5, abs=0.01)
    
    def test_calculate_pnl_loss(self):
        """Test P&L calculation for losing round."""
        calculator = DriftCalculator(house_edge=0.03, cashout_target=1.5)
        
        df = pd.DataFrame({
            'round_id': [1],
            'multiplier': [1.2]
        })
        
        result = calculator.calculate_pnl(df)
        
        assert result.loc[0, 'pnl'] == pytest.approx(-1.0, abs=0.01)
        assert result.loc[0, 'casino_profit'] == pytest.approx(1.0, abs=0.01)
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        calculator = DriftCalculator(house_edge=0.03, cashout_target=1.5)
        
        df = pd.DataFrame({
            'round_id': [1, 2, 3],
            'multiplier': [1.2, 2.0, 1.5],
            'pnl': [-1.0, 0.5, 0.5],
            'bet_size': [1.0, 1.0, 1.0]
        })
        
        result = calculator.calculate_metrics(df)
        
        assert 'cumulative_pnl' in result.columns
        assert 'cumulative_volume' in result.columns
        assert 'realized_edge' in result.columns
        assert 'drift' in result.columns
        
        # Check cumulative P&L
        assert result.loc[0, 'cumulative_pnl'] == pytest.approx(-1.0, abs=0.01)
        assert result.loc[1, 'cumulative_pnl'] == pytest.approx(-0.5, abs=0.01)
        assert result.loc[2, 'cumulative_pnl'] == pytest.approx(0.0, abs=0.01)
        
        # Check realized edge
        assert result.loc[0, 'realized_edge'] == pytest.approx(1.0, abs=0.01)  # -(-1.0)/1.0
        assert result.loc[2, 'realized_edge'] == pytest.approx(0.0, abs=0.01)  # -0.0/3.0
    
    def test_calculate_rate_of_balance(self):
        """Test rate of balance calculation."""
        calculator = DriftCalculator()
        
        # Create a longer drift series for meaningful calculation
        np.random.seed(42)
        drift_series = pd.Series(np.random.normal(0, 0.01, 100))
        
        result = calculator.calculate_rate_of_balance(drift_series)
        
        assert 'half_life' in result
        assert 'mean_reversion_rate' in result
        assert 'is_mean_reverting' in result
        
        # Half-life should be a positive number
        assert result['half_life'] >= 0
        
        # Mean reversion rate should be non-negative or NaN
        if not np.isnan(result['mean_reversion_rate']):
            assert result['mean_reversion_rate'] >= 0
    
    def test_calculate_statistics(self):
        """Test statistics calculation."""
        calculator = DriftCalculator()
        
        df = pd.DataFrame({
            'round_id': [1, 2, 3, 4, 5],
            'drift': [0.01, -0.02, 0.03, -0.01, 0.005]
        })
        
        result = calculator.calculate_statistics(df)
        
        assert 'mean_drift' in result
        assert 'std_drift' in result
        assert 'min_drift' in result
        assert 'max_drift' in result
        assert 'final_drift' in result
        assert 'n_rounds' in result
        
        assert result['n_rounds'] == 5
        assert result['mean_drift'] == pytest.approx(np.mean([0.01, -0.02, 0.03, -0.01, 0.005]), abs=0.001)
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        calculator = DriftCalculator()
        
        # Create a series with a clear anomaly
        # Mean ~0, std ~0.02, so 0.10 is >2 std from mean
        df = pd.DataFrame({
            'round_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'drift': [0.01, -0.02, 0.01, -0.01, 0.005, -0.015, 0.02, -0.005, 0.01, 0.10]
        })
        
        result = calculator.detect_anomalies(df, threshold_std=2.0)
        
        assert 'is_anomaly' in result.columns
        assert 'anomaly_group' in result.columns
        assert 'anomaly_duration' in result.columns
        
        # The last value should be flagged as anomaly
        assert result.loc[9, 'is_anomaly'] == True


class TestCalculateDriftMetricsFunction:
    """Tests for calculate_drift_metrics convenience function."""
    
    def test_basic(self):
        """Test basic drift metrics calculation."""
        df = pd.DataFrame({
            'round_id': [1, 2, 3],
            'multiplier': [1.2, 2.0, 1.5]
        })
        
        result = calculate_drift_metrics(df, house_edge=0.03, cashout_target=1.5)
        
        assert 'pnl' in result.columns
        assert 'casino_profit' in result.columns
        assert 'cumulative_pnl' in result.columns
        assert 'realized_edge' in result.columns
        assert 'drift' in result.columns
