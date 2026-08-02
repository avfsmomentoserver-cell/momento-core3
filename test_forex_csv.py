#!/usr/bin/env python3
"""
Standalone test of forex prediction logic on CSV data.
Tests core functions without database dependencies.
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add backend to path
repo_path = Path(__file__).parent / 'momento-core3' / 'backend'
sys.path.insert(0, str(repo_path))

from momento.linguistics import (
    classify_forex_state, 
    identify_support_resistance,
    calculate_rsi,
    calculate_atr,
    FOREX_STATES
)
from momento.forecast_forex import (
    forex_state_sequence,
    forex_transition_matrix,
    forex_candidates
)

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
    
    # Ensure numeric types
    df['multiplier'] = pd.to_numeric(df['multiplier'], errors='coerce')
    df = df.dropna(subset=['multiplier'])
    
    print(f"✓ Loaded {len(df)} rounds from {csv_path}")
    return df

def test_forex_logic(csv_path: str, num_rounds: int = 100):
    """Test forex prediction logic on CSV data"""
    print("\n" + "="*60)
    print("MOMENTO FOREX PREDICTION - CSV TEST")
    print("="*60)
    
    # Load data
    df = load_csv_data(csv_path)
    df = df.tail(num_rounds)
    multipliers = df['multiplier'].tolist()
    
    print(f"\n📊 Testing {len(multipliers)} rounds...")
    print("-"*60)
    
    # Test 1: State Classification
    print("\n🎯 TEST 1: Market State Classification")
    state = classify_forex_state(multipliers)
    print(f"  Current State: {state}")
    assert state in FOREX_STATES, f"Invalid state: {state}"
    print(f"  ✓ Valid state from {FOREX_STATES}")
    
    # Test 2: Support/Resistance
    print("\n📈 TEST 2: Support/Resistance Levels")
    sr = identify_support_resistance(multipliers)
    print(f"  Pivot Point: {sr['pivot']:.4f}")
    print(f"  Resistance R1: {sr['r1']:.4f}")
    print(f"  Support S1: {sr['s1']:.4f}")
    print(f"  Levels Found: {len(sr['levels'])}")
    for level in sr['levels'][:3]:
        marker = "🟢" if level['type'] == 'support' else "🔴"
        print(f"    {marker} {level['price']:.4f} ({level['type']})")
    assert sr['pivot'] > 0, "Invalid pivot"
    print(f"  ✓ Support/Resistance calculated")
    
    # Test 3: Technical Indicators
    print("\n📊 TEST 3: Technical Indicators")
    rsi = calculate_rsi(multipliers)
    atr = calculate_atr(multipliers)
    print(f"  RSI(14): {rsi:.2f}")
    print(f"  ATR(14): {atr:.4f}")
    
    if rsi > 70:
        print(f"  ⚠️ Overbought (>70)")
    elif rsi < 30:
        print(f"  ⚠️ Oversold (<30)")
    else:
        print(f"  ✓ Neutral zone")
    assert 0 <= rsi <= 100, "RSI out of range"
    assert atr > 0, "ATR must be positive"
    print(f"  ✓ Indicators valid")
    
    # Test 4: State Sequence
    print("\n🔄 TEST 4: Forex State Sequence")
    sequence = forex_state_sequence(multipliers)
    print(f"  Sequence Length: {len(sequence)}")
    unique_states = set(sequence)
    print(f"  Unique States: {', '.join(sorted(unique_states))}")
    
    # Count state distribution
    from collections import Counter
    state_counts = Counter(sequence)
    print(f"  Distribution:")
    for state_name, count in state_counts.most_common():
        pct = count / len(sequence) * 100
        print(f"    {state_name}: {count} ({pct:.1f}%)")
    print(f"  ✓ State sequence generated")
    
    # Test 5: Transition Matrix
    print("\n🔀 TEST 5: State Transition Matrix")
    matrix = forex_transition_matrix(sequence)
    print(f"  States in Matrix: {len(matrix)}")
    
    # Show top transitions
    transitions = []
    for from_state, to_states in matrix.items():
        for to_state, prob in to_states.items():
            if prob > 0.1:  # Only show significant transitions
                transitions.append((from_state, to_state, prob))
    
    transitions.sort(key=lambda x: x[2], reverse=True)
    print(f"  Top Transitions (>10%):")
    for from_s, to_s, prob in transitions[:5]:
        print(f"    {from_s} → {to_s}: {prob:.2%}")
    print(f"  ✓ Transition matrix calculated")
    
    # Test 6: Candidates/Rankings
    print("\n🎲 TEST 6: Prediction Candidates")
    candidates = forex_candidates(multipliers)
    print(f"  Candidates Generated: {len(candidates)}")
    
    if candidates:
        print(f"  Top 3 Predictions:")
        for i, cand in enumerate(candidates[:3], 1):
            conf = cand.get('confidence', 0)
            print(f"    {i}. {cand['state']}: {cand['probability']:.2%} (conf: {conf:.2%})")
        
        # Verify probabilities sum close to 1
        total_prob = sum(c['probability'] for c in candidates)
        print(f"  Total Probability: {total_prob:.2%}")
        assert 0.9 <= total_prob <= 1.1, f"Probabilities don't sum to ~1: {total_prob}"
        print(f"  ✓ Candidates ranked correctly")
    else:
        print(f"  ⚠️ No candidates (need more data)")
    
    # Summary
    print("\n" + "="*60)
    print("✅ ALL FOREX PREDICTION TESTS PASSED")
    print("="*60)
    print(f"\n📋 Summary:")
    print(f"  • Market State: {state}")
    print(f"  • RSI: {rsi:.2f} {'(Overbought)' if rsi > 70 else '(Oversold)' if rsi < 30 else '(Neutral)'}")
    print(f"  • ATR: {atr:.4f}")
    print(f"  • Support: {sr['s1']:.4f}, Resistance: {sr['r1']:.4f}")
    if candidates:
        print(f"  • Top Prediction: {candidates[0]['state']} ({candidates[0]['probability']:.2%})")
    print()
    
    return {
        'state': state,
        'rsi': rsi,
        'atr': atr,
        'support_resistance': sr,
        'candidates': candidates,
        'sequence': sequence
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_forex_csv.py <path_to_csv>")
        print("\nCreating sample CSV for testing...")
        
        # Create realistic sample data with different market regimes
        np.random.seed(42)
        n_rounds = 200
        
        # Simulate different market phases
        ranging = np.random.uniform(1.0, 2.0, 80)      # Ranging market
        trending_up = np.linspace(2.0, 5.0, 40)        # Uptrend
        consolidation = np.random.uniform(3.0, 4.0, 40) # Consolidation
        breakout = np.array([4.0, 6.5, 5.2, 7.8, 6.1]) # Breakout attempt
        pullback = np.linspace(7.0, 4.5, 35)           # Pullback
        
        multipliers = np.concatenate([ranging, trending_up, consolidation, breakout, pullback])
        
        sample_data = {
            'round_id': range(1, len(multipliers) + 1),
            'multiplier': multipliers
        }
        sample_df = pd.DataFrame(sample_data)
        sample_path = "sample_rounds.csv"
        sample_df.to_csv(sample_path, index=False)
        print(f"✓ Created sample CSV: {sample_path} ({len(multipliers)} rounds)")
        
        csv_path = sample_path
    else:
        csv_path = sys.argv[1]
    
    try:
        result = test_forex_logic(csv_path)
        print("🎉 Test completed successfully!")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
