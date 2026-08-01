"""
Fairness Analytics System

A comprehensive system for visualizing house edge fairness in crash games.

Key Features:
- Corrected point mapping with neutral baseline (E[Points] = 0)
- Drift calculation from theoretical house edge
- Rate of balance metrics (half-life, mean reversion)
- Forex-style visualizations
- Interactive dashboard
- Anomaly detection

Usage:
    from fairness_analytics import PointMapper, DriftCalculator, FairnessVisualizer
    
    # Initialize components
    mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
    calculator = DriftCalculator(house_edge=0.03, cashout_target=1.5)
    visualizer = FairnessVisualizer()
    
    # Process data
    df = mapper.map_dataframe(df)
    df = calculator.calculate_pnl(df)
    df = calculator.calculate_metrics(df)
    
    # Generate visualizations
    fig = visualizer.plot_cumulative_drift(df)
"""

from .point_mapper import PointMapper, fairness_points
from .drift_calculator import DriftCalculator, calculate_drift_metrics
from .visualization import FairnessVisualizer, plot_all_metrics

__version__ = "1.0.0"
__all__ = [
    'PointMapper',
    'fairness_points',
    'DriftCalculator',
    'calculate_drift_metrics',
    'FairnessVisualizer',
    'plot_all_metrics',
    '__version__'
]
