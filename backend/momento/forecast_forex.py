"""
Forex Market Forecast Module
Generates predictions, range forecasts, and candidate analysis using forex concepts.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# Try relative import first, fall back to direct import for standalone testing
try:
    from .linguistics import (
        FOREX_STATES,
        calculate_rsi,
        calculate_atr,
        identify_support_resistance,
        classify_forex_state,
        get_state_probability_distribution
    )
except ImportError:
    from linguistics import (
        FOREX_STATES,
        calculate_rsi,
        calculate_atr,
        identify_support_resistance,
        classify_forex_state,
        get_state_probability_distribution
    )


def forex_state_sequence(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    num_states: int = 10
) -> List[str]:
    """Generate sequence of forex states for recent candles"""
    states = []
    for i in range(max(0, len(closes) - num_states), len(closes)):
        window_end = i + 1
        state = classify_forex_state(
            opens[:window_end],
            highs[:window_end],
            lows[:window_end],
            closes[:window_end],
            volumes[:window_end],
            closes[i]
        )
        states.append(state)
    return states


def forex_transition_matrix(states: List[str]) -> Dict[str, Dict[str, float]]:
    """Calculate transition probabilities between forex states with Laplace smoothing"""
    transitions = defaultdict(lambda: defaultdict(int))
    
    for i in range(len(states) - 1):
        current_state = states[i]
        next_state = states[i + 1]
        transitions[current_state][next_state] += 1
    
    # Convert to probabilities with Laplace smoothing
    matrix = {}
    for state in FOREX_STATES:
        matrix[state] = {}
        total_count = sum(transitions[state].values()) + len(FOREX_STATES)  # Laplace smoothing
        
        for next_state in FOREX_STATES:
            count = transitions[state][next_state] + 1  # Add 1 for smoothing
            probability = count / total_count
            matrix[state][next_state] = round(probability, 4)
    
    return matrix


def _forex_band_range_for_state(
    state: str,
    current_price: float,
    atr: float,
    sr_levels: Dict
) -> Tuple[float, float]:
    """Calculate expected price range based on forex state"""
    pivot = sr_levels.get('pivots', {}).get('pivot', current_price)
    resistance_1 = sr_levels.get('resistance', [current_price * 1.05])[0] if sr_levels.get('resistance') else current_price * 1.05
    support_1 = sr_levels.get('support', [current_price * 0.95])[0] if sr_levels.get('support') else current_price * 0.95
    
    if state == 'Ranging' or state == 'Consolidation':
        # Range between nearest support and resistance
        lower = max(support_1, current_price * 0.98)
        upper = min(resistance_1, current_price * 1.02)
        return (round(lower, 4), round(upper, 4))
    
    elif state == 'TrendingUp':
        # Target next resistance level
        target = resistance_1 + (atr * 1.5)
        stop = support_1
        return (round(stop, 4), round(target, 4))
    
    elif state == 'TrendingDown':
        # Target next support level
        target = support_1 - (atr * 1.5)
        stop = resistance_1
        return (round(target, 4), round(stop, 4))
    
    elif state == 'Breakout':
        # Breakout target: 2-3x ATR beyond the broken level
        if current_price > resistance_1:
            target = current_price + (atr * 2.5)
            stop = resistance_1 - (atr * 0.5)
        else:
            target = current_price - (atr * 2.5)
            stop = support_1 + (atr * 0.5)
        return (round(min(target, stop), 4), round(max(target, stop), 4))
    
    elif state == 'Reversal':
        # Reversal target: bounce to opposite side of range
        if current_price < pivot:
            target = pivot + (atr * 1.0)
            stop = current_price - (atr * 1.5)
        else:
            target = pivot - (atr * 1.0)
            stop = current_price + (atr * 1.5)
        return (round(min(target, stop), 4), round(max(target, stop), 4))
    
    elif state == 'FalseBreak':
        # False break: quick return to range
        lower = support_1
        upper = resistance_1
        return (round(lower, 4), round(upper, 4))
    
    else:
        # Default: ±1 ATR
        return (round(current_price - atr, 4), round(current_price + atr, 4))


def forex_candidates(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float],
    top_n: int = 3
) -> List[Dict]:
    """Generate ranked list of forex state candidates with probabilities and ranges"""
    if len(closes) < 20:
        return []
    
    current_price = closes[-1]
    rsi = calculate_rsi(closes)
    atr = calculate_atr(highs, lows, closes)
    sr_levels = identify_support_resistance(highs, lows, closes)
    
    # Get probability distribution
    probs = get_state_probability_distribution(opens, highs, lows, closes, volumes)
    
    # Calculate confluence score for each state
    candidates = []
    for state, probability in probs.items():
        # Base confidence from probability
        confidence = probability
        
        # Adjust for confluence factors
        confluence_count = 0
        
        # Check if price is near key levels
        for level in sr_levels.get('resistance', []):
            if abs(current_price - level) / level < 0.02:
                if state in ['Breakout', 'Reversal', 'Consolidation']:
                    confluence_count += 1
                    confidence += 3.0
        
        for level in sr_levels.get('support', []):
            if abs(current_price - level) / level < 0.02:
                if state in ['Reversal', 'Consolidation']:
                    confluence_count += 1
                    confidence += 3.0
        
        # RSI confluence
        if state in ['TrendingUp', 'Breakout'] and 50 < rsi < 70:
            confluence_count += 1
            confidence += 2.0
        elif state in ['TrendingDown', 'Breakout'] and 30 < rsi < 50:
            confluence_count += 1
            confidence += 2.0
        elif state == 'Reversal' and (rsi > 70 or rsi < 30):
            confluence_count += 1
            confidence += 4.0
        
        # Volume confluence
        avg_volume = np.mean(volumes[-20:-1]) if len(volumes) > 20 else np.mean(volumes[:-1])
        if volumes[-1] > avg_volume * 1.5:
            if state in ['Breakout', 'TrendingUp', 'TrendingDown']:
                confluence_count += 1
                confidence += 3.0
        
        # Calculate range for this state
        predicted_range = _forex_band_range_for_state(state, current_price, atr, sr_levels)
        
        # Risk/Reward calculation
        if state in ['TrendingUp', 'Breakout'] and current_price > sr_levels.get('pivots', {}).get('pivot', current_price):
            upside = predicted_range[1] - current_price
            downside = current_price - predicted_range[0]
            risk_reward = upside / downside if downside > 0 else 0
        elif state in ['TrendingDown', 'Breakout'] and current_price < sr_levels.get('pivots', {}).get('pivot', current_price):
            downside = current_price - predicted_range[0]
            upside = predicted_range[1] - current_price
            risk_reward = downside / upside if upside > 0 else 0
        else:
            risk_reward = 1.0
        
        candidates.append({
            'state': state,
            'probability': round(probability, 2),
            'confidence_score': round(confidence, 2),
            'confluence_count': confluence_count,
            'predicted_range': predicted_range,
            'risk_reward_ratio': round(risk_reward, 2),
            'invalidation_level': predicted_range[0] if state in ['TrendingUp', 'Breakout'] and current_price > sr_levels.get('pivots', {}).get('pivot', current_price) else predicted_range[1],
            'rsi': rsi,
            'atr': atr
        })
    
    # Sort by confidence score
    candidates.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    return candidates[:top_n]


def forex_forecast(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float]
) -> Dict:
    """Generate comprehensive forex forecast with headline and details"""
    if len(closes) < 20:
        return {
            'headline': 'Insufficient Data',
            'summary': 'Need at least 20 candles for reliable forex analysis',
            'candidates': [],
            'transition_matrix': {},
            'indicators': {}
        }
    
    current_price = closes[-1]
    rsi = calculate_rsi(closes)
    atr = calculate_atr(highs, lows, closes)
    sr_levels = identify_support_resistance(highs, lows, closes)
    states = forex_state_sequence(opens, highs, lows, closes, volumes)
    candidates = forex_candidates(opens, highs, lows, closes, volumes, top_n=3)
    transition_matrix = forex_transition_matrix(states)
    
    # Determine primary state
    primary_state = classify_forex_state(opens, highs, lows, closes, volumes, current_price)
    
    # Generate headline
    if primary_state == 'Breakout':
        direction = 'Bullish' if current_price > sr_levels.get('pivots', {}).get('pivot', current_price) else 'Bearish'
        headline = f"{direction} Breakout Detected - Target {candidates[0]['predicted_range'][1] if direction == 'Bullish' else candidates[0]['predicted_range'][0]}"
    elif primary_state == 'TrendingUp':
        headline = f"Uptrend Continuation Expected - Resistance at {sr_levels.get('resistance', [current_price * 1.05])[0]}"
    elif primary_state == 'TrendingDown':
        headline = f"Downtrend Continuation Expected - Support at {sr_levels.get('support', [current_price * 0.95])[0]}"
    elif primary_state == 'Reversal':
        headline = "Potential Reversal Signal - Watch for Confirmation"
    elif primary_state == 'FalseBreak':
        headline = "False Breakout Warning - Range Bound Expected"
    else:
        headline = f"Market {primary_state} - Wait for Clear Direction"
    
    # Summary
    summary = (
        f"RSI: {rsi} | ATR: {atr} | "
        f"Key Resistance: {sr_levels.get('resistance', ['N/A'])[0]} | "
        f"Key Support: {sr_levels.get('support', ['N/A'])[0]}"
    )
    
    return {
        'headline': headline,
        'summary': summary,
        'primary_state': primary_state,
        'candidates': candidates,
        'transition_matrix': transition_matrix,
        'indicators': {
            'rsi': rsi,
            'atr': atr,
            'pivot': sr_levels.get('pivots', {}).get('pivot', current_price),
            'resistance_levels': sr_levels.get('resistance', []),
            'support_levels': sr_levels.get('support', []),
            'fib_levels': sr_levels.get('fib_levels', [])
        },
        'state_sequence': states[-10:]  # Last 10 states
    }


# Persistence functions for production use
def store_forex_prediction(prediction: Dict, timestamp: float, round_id: int):
    """Store prediction for later accuracy tracking"""
    # In production, this would write to a database
    # For now, just log it
    print(f"[STORE] Round {round_id} @ {timestamp}: {prediction['headline']}")


def load_historical_predictions(limit: int = 100) -> List[Dict]:
    """Load historical predictions for accuracy calculation"""
    # In production, this would query a database
    # For now, return empty list
    return []


def calculate_prediction_accuracy(predictions: List[Dict], actual_outcomes: List[float]) -> Dict:
    """Calculate accuracy metrics for past predictions"""
    if not predictions or not actual_outcomes:
        return {'accuracy': 0.0, 'total': 0, 'correct': 0}
    
    correct = 0
    total = min(len(predictions), len(actual_outcomes))
    
    for i in range(total):
        pred_range = predictions[i].get('candidates', [{}])[0].get('predicted_range', (0, 0))
        actual = actual_outcomes[i]
        
        if pred_range[0] <= actual <= pred_range[1]:
            correct += 1
    
    accuracy = (correct / total * 100) if total > 0 else 0
    
    return {
        'accuracy': round(accuracy, 2),
        'total': total,
        'correct': correct,
        'hit_rate': f"{correct}/{total}"
    }
