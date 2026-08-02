"""
Forex Market Linguistics Module
Provides technical indicators, state classification, and support/resistance analysis for Momento rounds treated as forex candles.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# Forex Market States
FOREX_STATES = [
    'Ranging',
    'TrendingUp', 
    'TrendingDown',
    'Breakout',
    'Reversal',
    'Consolidation',
    'FalseBreak'
]

FOREX_STATE_META = {
    'Ranging': {'meaning': 'Price moving sideways within defined bounds', 'color': '#808080'},
    'TrendingUp': {'meaning': 'Sustained upward price movement', 'color': '#22c55e'},
    'TrendingDown': {'meaning': 'Sustained downward price movement', 'color': '#ef4444'},
    'Breakout': {'meaning': 'Price breaking through key resistance/support', 'color': '#3b82f6'},
    'Reversal': {'meaning': 'Change in trend direction', 'color': '#a855f7'},
    'Consolidation': {'meaning': 'Price coiling after a move', 'color': '#f59e0b'},
    'FalseBreak': {'meaning': 'Failed breakout attempt', 'color': '#ec4899'}
}


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices[-period-1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate Average True Range for volatility measurement"""
    if len(closes) < period + 1:
        return 0.0
    
    tr_values = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        tr = max(high_low, high_close, low_close)
        tr_values.append(tr)
    
    atr = np.mean(tr_values[-period:]) if len(tr_values) >= period else np.mean(tr_values)
    return round(atr, 4)


def identify_support_resistance(
    highs: List[float], 
    lows: List[float], 
    closes: List[float],
    lookback: int = 50
) -> Dict[str, List[float]]:
    """
    Identify support and resistance levels using multiple methods:
    - Swing highs/lows
    - Classic Pivot Points
    - Fibonacci Retracement
    Returns confluence-weighted levels
    """
    if len(closes) < 10:
        return {'support': [], 'resistance': [], 'pivots': {}, 'fib_levels': []}
    
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    recent_closes = closes[-lookback:]
    
    # Classic Pivot Points (Forex Standard)
    pivot = (recent_highs[-1] + recent_lows[-1] + recent_closes[-1]) / 3
    r1 = 2 * pivot - recent_lows[-1]
    s1 = 2 * pivot - recent_highs[-1]
    r2 = pivot + (recent_highs[-1] - recent_lows[-1])
    s2 = pivot - (recent_highs[-1] - recent_lows[-1])
    r3 = recent_highs[-1] + 2 * (pivot - recent_lows[-1])
    s3 = recent_lows[-1] - 2 * (recent_highs[-1] - pivot)
    
    pivots = {
        'pivot': round(pivot, 4),
        'r1': round(r1, 4), 'r2': round(r2, 4), 'r3': round(r3, 4),
        's1': round(s1, 4), 's2': round(s2, 4), 's3': round(s3, 4)
    }
    
    # Fibonacci Retracement Levels
    swing_high = max(recent_highs)
    swing_low = min(recent_lows)
    fib_range = swing_high - swing_low
    
    fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    fib_levels = []
    for ratio in fib_ratios:
        level = swing_high - (fib_range * ratio)
        fib_levels.append(round(level, 4))
    
    # Swing Highs/Lows with confluence weighting
    supports = []
    resistances = []
    
    # Add pivot supports/resistances with high weight
    supports.extend([s1, s2, s3])
    resistances.extend([r1, r2, r3])
    
    # Add fib levels with medium weight
    supports.extend([l for l in fib_levels if l < pivot])
    resistances.extend([l for l in fib_levels if l > pivot])
    
    # Find swing points
    for i in range(2, len(recent_lows) - 2):
        if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
            if recent_lows[i] < recent_lows[i-2] and recent_lows[i] < recent_lows[i+2]:
                supports.append(round(recent_lows[i], 4))
    
    for i in range(2, len(recent_highs) - 2):
        if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
            if recent_highs[i] > recent_highs[i-2] and recent_highs[i] > recent_highs[i+2]:
                resistances.append(round(recent_highs[i], 4))
    
    # Remove duplicates and sort
    supports = sorted(list(set(supports)), reverse=True)
    resistances = sorted(list(set(resistances)))
    
    return {
        'support': supports[:5],  # Top 5 strongest supports
        'resistance': resistances[:5],  # Top 5 strongest resistances
        'pivots': pivots,
        'fib_levels': fib_levels,
        'swing_high': round(swing_high, 4),
        'swing_low': round(swing_low, 4)
    }


def classify_forex_state(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    current_price: float
) -> str:
    """
    Classify current market state using dynamic volatility-based thresholds
    """
    if len(closes) < 20:
        return 'Ranging'
    
    # Calculate indicators
    rsi = calculate_rsi(closes)
    atr = calculate_atr(highs, lows, closes)
    sr_levels = identify_support_resistance(highs, lows, closes)
    
    # Dynamic thresholds based on ATR
    volatility_factor = atr / current_price if current_price > 0 else 0.01
    rsi_overbought = 65 + (volatility_factor * 100)
    rsi_oversold = 35 - (volatility_factor * 100)
    
    # Price position analysis
    pivot = sr_levels['pivots'].get('pivot', current_price)
    resistance_1 = sr_levels['resistance'][0] if sr_levels['resistance'] else pivot * 1.05
    support_1 = sr_levels['support'][0] if sr_levels['support'] else pivot * 0.95
    
    price_to_pivot = (current_price - pivot) / pivot if pivot > 0 else 0
    price_to_resistance = (resistance_1 - current_price) / resistance_1 if resistance_1 > 0 else 0
    price_to_support = (current_price - support_1) / support_1 if support_1 > 0 else 0
    
    # Recent trend detection
    recent_closes = closes[-10:]
    ema_short = np.mean(recent_closes[-5:])
    ema_long = np.mean(recent_closes)
    trend_strength = (ema_short - ema_long) / ema_long if ema_long > 0 else 0
    
    # State classification logic with momentum confirmation
    if current_price > resistance_1 and rsi > rsi_overbought:
        # Breakout with momentum
        if volumes[-1] > np.mean(volumes[-20:-1]) * 1.5:
            return 'Breakout'
        else:
            return 'FalseBreak'
    
    elif current_price < support_1 and rsi < rsi_oversold:
        # Breakdown with momentum
        if volumes[-1] > np.mean(volumes[-20:-1]) * 1.5:
            return 'Breakout'  # Downward breakout
        else:
            return 'FalseBreak'
    
    elif price_to_support < 0.02 and rsi < 45:
        # Near support, potential bounce
        return 'Reversal'
    
    elif price_to_resistance < 0.02 and rsi > 55:
        # Near resistance, potential rejection
        if trend_strength > 0.02:
            return 'Consolidation'
        else:
            return 'Reversal'
    
    elif abs(price_to_pivot) < 0.01 and atr < np.mean(calculate_atr(highs[:-i], lows[:-i], closes[:-i]) for i in range(1, 4)):
        # Low volatility, coiling
        return 'Consolidation'
    
    elif trend_strength > 0.03 and rsi > 50:
        return 'TrendingUp'
    
    elif trend_strength < -0.03 and rsi < 50:
        return 'TrendingDown'
    
    else:
        return 'Ranging'


def calculate_momentum_confirmation(
    closes: List[float],
    volumes: List[float],
    threshold_multiplier: float = 1.5
) -> bool:
    """Check if momentum confirms the current price move"""
    if len(closes) < 10:
        return False
    
    # Rate of Change
    roc = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
    
    # Volume confirmation
    avg_volume = np.mean(volumes[-20:-1]) if len(volumes) > 20 else np.mean(volumes[:-1])
    volume_confirmed = volumes[-1] > avg_volume * threshold_multiplier
    
    # Velocity (acceleration)
    if len(closes) >= 3:
        velocity = (closes[-1] - closes[-2]) - (closes[-2] - closes[-3])
    else:
        velocity = 0
    
    return abs(roc) > 0.02 and (volume_confirmed or abs(velocity) > 0.01)


def get_state_probability_distribution(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float]
) -> Dict[str, float]:
    """Return probability distribution across all forex states"""
    current_price = closes[-1] if closes else 1.0
    primary_state = classify_forex_state(opens, highs, lows, closes, volumes, current_price)
    
    # Base probabilities
    probs = {state: 5.0 for state in FOREX_STATES}  # Base 5% for each
    probs[primary_state] = 50.0  # Primary state gets 50%
    
    # Adjust based on technical factors
    rsi = calculate_rsi(closes)
    
    if rsi > 70:
        probs['TrendingUp'] += 15
        probs['Reversal'] += 10
        probs['Ranging'] -= 10
    elif rsi < 30:
        probs['TrendingDown'] += 15
        probs['Reversal'] += 10
        probs['Ranging'] -= 10
    
    # Normalize to 100%
    total = sum(probs.values())
    probs = {k: round(v / total * 100, 2) for k, v in probs.items()}
    
    return probs
