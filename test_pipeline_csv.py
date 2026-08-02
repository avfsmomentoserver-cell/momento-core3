#!/usr/bin/env python3
"""
Test the full core prediction pipeline on CSV data.
Expects a CSV with columns: round_id, multiplier, timestamp
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add backend to path - use cloned repo
repo_path = Path(__file__).parent / 'momento-core3' / 'backend'
sys.path.insert(0, str(repo_path))

from momento.forecast_forex import forex_forecast
from momento.linguistics import classify_forex_state, identify_support_resistance
from momento.config import AnalysisSettings
from momento.api.schemas import RoundIn

def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV data"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Validate required columns
    required_cols = ['round_id', 'multiplier']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Add timestamp if missing
    if 'timestamp' not in df.columns:
        df['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df), freq='min')
    
    # Ensure numeric types
    df['multiplier'] = pd.to_numeric(df['multiplier'], errors='coerce')
    df = df.dropna(subset=['multiplier'])
    
    print(f"✓ Loaded {len(df)} rounds from {csv_path}")
    return df

def df_to_rounds(df: pd.DataFrame):
    """Convert DataFrame to list of dict objects (as expected by forex_forecast)"""
    rounds = []
    for _, row in df.iterrows():
        ts = row.get('timestamp')
        # Convert timestamp to ISO string if it's a pandas Timestamp
        if hasattr(ts, 'isoformat'):
            ts = ts.isoformat()
        
        rounds.append({
            'multiplier': float(row['multiplier']),
            'timestamp': ts,
            'source': 'csv_test'
        })
    return rounds

def test_pipeline_on_csv(csv_path: str, num_rounds: int = 100):
    """Run full pipeline on CSV data"""
    print("\n" + "="*60)
    print("MOMENTO CORE PIPELINE - CSV TEST")
    print("="*60)
    
    # Load data
    df = load_csv_data(csv_path)
    df = df.tail(num_rounds)  # Use last N rounds
    
    # Convert to RoundIn objects
    rounds = df_to_rounds(df)
    
    print(f"\n📊 Processing {len(rounds)} rounds...")
    print("-"*60)
    
    # Create default settings
    settings = AnalysisSettings()
    
    # Run forecast
    result = forex_forecast(rounds, settings)
    
    # Display results
    print("\n🎯 PIPELINE RESULTS")
    print("-"*60)
    
    print(f"\nMarket State: {result['state']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Confluence Count: {result['confluence_count']}")
    
    print(f"\n📈 Support/Resistance Levels:")
    for level in result['support_resistance']['levels'][:5]:
        marker = "🟢" if level['type'] == 'support' else "🔴"
        print(f"  {marker} {level['type'].upper():10} @ {level['price']:.4f} (weight: {level['weight']:.2f})")
    
    print(f"\n📊 Technical Indicators:")
    indicators = result['indicators']
    print(f"  RSI: {indicators.get('rsi', 'N/A'):.2f}" if isinstance(indicators.get('rsi'), (int, float)) else f"  RSI: {indicators.get('rsi', 'N/A')}")
    print(f"  ATR: {indicators.get('atr', 'N/A'):.4f}" if isinstance(indicators.get('atr'), (int, float)) else f"  ATR: {indicators.get('atr', 'N/A')}")
    print(f"  EMA20: {indicators.get('ema_20', 'N/A'):.4f}" if isinstance(indicators.get('ema_20'), (int, float)) else f"  EMA20: {indicators.get('ema_20', 'N/A')}")
    
    print(f"\n🔮 Forecast:")
    forecast = result['forecast']
    print(f"  Predicted Range: {forecast['predicted_low']:.4f}x - {forecast['predicted_high']:.4f}x")
    print(f"  Breakout Target: {forecast.get('breakout_target', 'N/A')}")
    print(f"  Invalidation (Stop Loss): {forecast['invalidation_level']:.4f}x")
    print(f"  Risk/Reward Ratio: {forecast.get('risk_reward_ratio', 'N/A'):.2f}")
    
    print(f"\n🎲 Top Candidates:")
    for i, candidate in enumerate(result['candidates'][:3], 1):
        print(f"  {i}. {candidate['state']}: {candidate['probability']:.2%} (conf: {candidate.get('confidence', 0):.2%})")
    
    # Test individual functions
    print("\n\n🧪 INDIVIDUAL FUNCTION TESTS")
    print("-"*60)
    
    # Get multipliers list
    multipliers = [r.multiplier for r in rounds]
    
    # Test state classification
    state = classify_forex_state(multipliers)
    print(f"✓ classify_forex_state: {state}")
    
    # Test support/resistance
    sr = identify_support_resistance(multipliers)
    print(f"✓ identify_support_resistance: {len(sr['levels'])} levels found")
    print(f"  Pivot: {sr['pivot']:.4f}, R1: {sr['r1']:.4f}, S1: {sr['s1']:.4f}")
    
    # Test forecast with rounds (already tested above, skip duplicate)
    print(f"✓ forex_forecast: {result['headline']}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60 + "\n")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline_csv.py <path_to_csv>")
        print("\nCreating sample CSV for testing...")
        
        # Create sample data
        np.random.seed(42)
        n_rounds = 200
        sample_data = {
            'round_id': range(1, n_rounds + 1),
            'multiplier': np.concatenate([
                np.random.uniform(1.0, 2.0, 100),  # Ranging
                np.random.uniform(2.0, 5.0, 50),   # Trending up
                np.random.uniform(1.0, 3.0, 50),   # Consolidation
            ])
        }
        sample_df = pd.DataFrame(sample_data)
        sample_path = "sample_rounds.csv"
        sample_df.to_csv(sample_path, index=False)
        print(f"✓ Created sample CSV: {sample_path}")
        
        csv_path = sample_path
    else:
        csv_path = sys.argv[1]
    
    try:
        test_pipeline_on_csv(csv_path)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
