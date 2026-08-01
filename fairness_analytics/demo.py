"""
Fairness Analytics System - Demo Script

This script demonstrates the fairness analytics system using sample data
or a provided CSV file.

Usage:
    python demo.py                    # Use sample data
    python demo.py your_data.csv      # Use your CSV file
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fairness_analytics.point_mapper import PointMapper
from fairness_analytics.drift_calculator import DriftCalculator
from fairness_analytics.visualization import FairnessVisualizer, plot_all_metrics


def generate_sample_data(n_rounds: int = 100) -> pd.DataFrame:
    """Generate sample crash game data for demonstration."""
    np.random.seed(42)
    
    data = {
        'round_id': list(range(1, n_rounds + 1)),
        'source': 'aviator',
        'timestamp': [datetime.now() - timedelta(seconds=i*30) for i in range(n_rounds)],
        'multiplier': [],
        'color': 'rgb(52, 180, 255)',
        'band': 'low',
        'session_id': 1
    }
    
    # Generate realistic crash game multipliers
    for i in range(n_rounds):
        u = np.random.random()
        
        # Simulate crash game distribution
        # P(X >= m) = (1 - house_edge) / m
        house_edge = 0.03
        
        if u < house_edge:
            # Instant crash at 1.00x
            multiplier = 1.00
        else:
            # Generate multiplier from inverse transform sampling
            # P(X <= x) = 1 - (1 - house_edge) / x
            # So X = (1 - house_edge) / (1 - U)
            multiplier = max(1.00, (1 - house_edge) / (1 - u))
            
            # Cap at reasonable value for demo
            multiplier = min(multiplier, 100.0)
        
        data['multiplier'].append(round(multiplier, 2))
    
    return pd.DataFrame(data)


def load_csv_data(file_path: str) -> pd.DataFrame:
    """Load data from CSV file."""
    df = pd.read_csv(file_path)
    
    # Ensure required columns exist
    if 'multiplier' not in df.columns:
        raise ValueError("CSV must contain a 'multiplier' column")
    
    if 'round_id' not in df.columns:
        df['round_id'] = df.index + 1
    
    return df


def run_demo(csv_path: str = None, n_rounds: int = 100) -> None:
    """Run the fairness analytics demo."""
    print("=" * 80)
    print("CRASH GAME FAIRNESS ANALYTICS DEMO")
    print("=" * 80)
    
    # Load or generate data
    if csv_path and os.path.exists(csv_path):
        print(f"\n✅ Loading data from: {csv_path}")
        df = load_csv_data(csv_path)
    else:
        print(f"\n✅ Generating {n_rounds} rounds of sample data")
        df = generate_sample_data(n_rounds)
    
    print(f"   Total rounds: {len(df)}")
    print(f"   Multiplier range: {df['multiplier'].min():.2f}x - {df['multiplier'].max():.2f}x")
    
    # Initialize components
    cashout_target = 1.5
    house_edge = 0.03
    
    print(f"\n📊 Configuration:")
    print(f"   Cashout Target: {cashout_target}x")
    print(f"   House Edge: {house_edge*100:.1f}%")
    
    mapper = PointMapper(cashout_target, house_edge)
    calculator = DriftCalculator(house_edge, cashout_target)
    visualizer = FairnessVisualizer()
    
    # Map points
    print("\n🔄 Mapping multipliers to fairness points...")
    df = mapper.map_dataframe(df)
    
    # Verify neutral baseline
    print("\n✅ Verifying neutral baseline...")
    verification = mapper.verify_neutral_baseline(df['multiplier'])
    print(f"   Mean Points: {verification['mean_points']:.4f}")
    print(f"   Std Points: {verification['std_points']:.4f}")
    print(f"   Is Neutral: {'✅ Yes' if verification['is_neutral'] else '❌ No'}")
    print(f"   Deviation from Neutral: {verification['deviation_from_neutral']:.4f}")
    
    # Calculate P&L
    print("\n💰 Calculating P&L...")
    df = calculator.calculate_pnl(df)
    
    # Calculate metrics
    print("\n📈 Calculating drift metrics...")
    df = calculator.calculate_metrics(df)
    
    # Detect anomalies
    print("\n🔍 Detecting anomalies...")
    df = calculator.detect_anomalies(df, threshold_std=3.0)
    
    # Calculate rate of balance
    print("\n⚖️ Calculating rate of balance...")
    rate_metrics = calculator.calculate_rate_of_balance(df['drift'])
    stats = calculator.calculate_statistics(df)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  total_rounds               : {stats['n_rounds']}")
    print(f"  theoretical_house_edge    : {house_edge*100:.4f}%")
    print(f"  final_realized_edge       : {stats['final_drift']*100 + house_edge*100:.4f}%")
    print(f"  final_drift               : {stats['final_drift']*100:.4f}%")
    print(f"  mean_drift                : {stats['mean_drift']*100:.4f}%")
    print(f"  std_drift                 : {stats['std_drift']*100:.4f}%")
    print(f"  half_life                 : {rate_metrics['half_life']:.2f} rounds")
    print(f"  mean_reversion_rate       : {rate_metrics['mean_reversion_rate']*100:.2f}%")
    
    print("\n" + "=" * 80)
    print("FOREX ANALYST INTERPRETATION")
    print("=" * 80)
    
    print("\nFairness Assessment:")
    if abs(stats['final_drift']) < 0.01:
        print("  ✅ Current drift is within normal range")
    elif abs(stats['final_drift']) < 0.05:
        print("  ⚠️  Current drift is slightly elevated")
    else:
        print("  ❌ Current drift is significantly elevated")
    
    print("\nRate of Balance:")
    if rate_metrics['half_life'] < 10:
        print("  ✅ Fast balance restoration")
    elif rate_metrics['half_life'] < 30:
        print("  ℹ️  Moderate balance restoration")
    else:
        print("  ⚠️  Slow balance restoration")
    
    print("\nMean Reversion:")
    if rate_metrics['mean_reversion_rate'] > 0.15:
        print("  ✅ Strong mean reversion")
    elif rate_metrics['mean_reversion_rate'] > 0.05:
        print("  ℹ️  Moderate mean reversion")
    else:
        print("  ⚠️  Weak mean reversion")
    
    # Generate visualizations
    print("\n📊 Generating visualizations...")
    output_dir = 'demo_visualizations'
    os.makedirs(output_dir, exist_ok=True)
    
    figures = plot_all_metrics(df, output_dir)
    
    print(f"\n✅ Visualizations saved to: {output_dir}/")
    for name, path in figures.items():
        print(f"   - {name}: {path}")
    
    # Show sample data
    print("\n" + "=" * 80)
    print("SAMPLE DATA (First 10 rounds)")
    print("=" * 80)
    sample_df = df[['round_id', 'multiplier', 'points', 'pnl', 'realized_edge', 'drift']].head(10)
    print(sample_df.to_string(index=False))
    
    # Show anomaly detection
    anomalies = df[df['is_anomaly']]
    if len(anomalies) > 0:
        print("\n" + "=" * 80)
        print("ANOMALY DETECTION")
        print("=" * 80)
        print(f"Detected {len(anomalies)} anomalous rounds:")
        anomaly_sample = anomalies[['round_id', 'multiplier', 'drift', 'anomaly_duration']].head(10)
        print(anomaly_sample.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_demo(csv_path)
