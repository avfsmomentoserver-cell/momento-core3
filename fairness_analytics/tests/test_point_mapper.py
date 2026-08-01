"""
Unit tests for PointMapper class.
"""

import pytest
import numpy as np
import pandas as pd
from fairness_analytics.point_mapper import PointMapper, fairness_points


class TestPointMapper:
    """Tests for PointMapper class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        mapper = PointMapper()
        assert mapper.cashout_target == 1.5
        assert mapper.house_edge == 0.03
    
    def test_init_custom(self):
        """Test custom initialization."""
        mapper = PointMapper(cashout_target=2.0, house_edge=0.05)
        assert mapper.cashout_target == 2.0
        assert mapper.house_edge == 0.05
    
    def test_map_single_win(self):
        """Test mapping a winning multiplier."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        # Multiplier >= cashout_target should be a win
        points = mapper.map_single(2.0)
        expected = 100 * ((1.5 - 1) + 0.03)  # 100 * 0.53 = 53
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_map_single_loss(self):
        """Test mapping a losing multiplier."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        # Multiplier < cashout_target should be a loss
        points = mapper.map_single(1.2)
        expected = 100 * (-1 + 0.03)  # 100 * -0.97 = -97
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_map_single_exact_cashout(self):
        """Test mapping exact cashout multiplier."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        # Multiplier == cashout_target should be a win
        points = mapper.map_single(1.5)
        expected = 100 * ((1.5 - 1) + 0.03)  # 53
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_map_single_instant_crash(self):
        """Test mapping instant crash at 1.00x."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        points = mapper.map_single(1.0)
        expected = 100 * (-1 + 0.03)  # -97
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_map_array(self):
        """Test mapping an array of multipliers."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        multipliers = [1.2, 1.8, 2.5, 1.0]
        points = mapper.map_array(multipliers)
        
        expected = [
            100 * (-1 + 0.03),  # -97
            100 * ((1.5 - 1) + 0.03),  # 53
            100 * ((1.5 - 1) + 0.03),  # 53
            100 * (-1 + 0.03)  # -97
        ]
        
        assert len(points) == len(expected)
        for p, e in zip(points, expected):
            assert p == pytest.approx(e, abs=0.01)
    
    def test_map_dataframe(self):
        """Test mapping a DataFrame."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        df = pd.DataFrame({
            'round_id': [1, 2, 3],
            'multiplier': [1.2, 1.8, 2.5]
        })
        
        result = mapper.map_dataframe(df)
        
        assert 'points' in result.columns
        assert len(result) == 3
        
        # Check specific values
        assert result.loc[0, 'points'] == pytest.approx(-97, abs=0.01)
        assert result.loc[1, 'points'] == pytest.approx(53, abs=0.01)
        assert result.loc[2, 'points'] == pytest.approx(53, abs=0.01)
    
    def test_verify_neutral_baseline(self):
        """Test neutral baseline verification."""
        mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
        
        # Generate synthetic multipliers
        multipliers = [1.2, 1.8, 2.5, 1.0, 3.0, 1.1, 2.0, 1.5, 1.9, 10.0]
        
        result = mapper.verify_neutral_baseline(multipliers, n_simulations=10000)
        
        assert 'mean_points' in result
        assert 'std_points' in result
        assert 'is_neutral' in result
        assert 'deviation_from_neutral' in result
        
        # Mean should be close to 0 for neutral baseline (allowing for simulation variance)
        # With corrected mapping, mean should be very close to 0
        assert abs(result['mean_points']) < 5.0  # Allowing for simulation variance


class TestFairnessPointsFunction:
    """Tests for fairness_points convenience function."""
    
    def test_defaults(self):
        """Test with default parameters."""
        points = fairness_points(2.0)
        expected = 100 * ((1.5 - 1) + 0.03)  # 53
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_custom_parameters(self):
        """Test with custom parameters."""
        points = fairness_points(2.0, cashout_target=2.0, house_edge=0.05)
        expected = 100 * ((2.0 - 1) + 0.05)  # 105
        assert points == pytest.approx(expected, abs=0.01)
    
    def test_loss(self):
        """Test loss calculation."""
        points = fairness_points(1.2, cashout_target=1.5, house_edge=0.03)
        expected = 100 * (-1 + 0.03)  # -97
        assert points == pytest.approx(expected, abs=0.01)
