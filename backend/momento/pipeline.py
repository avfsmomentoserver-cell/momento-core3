"""
Core Prediction Pipeline
Orchestrates the complete forex prediction flow from data ingestion to signal generation.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
import time

# Try relative import first, fall back to direct import for standalone testing
try:
    from .linguistics import (
        calculate_rsi,
        calculate_atr,
        identify_support_resistance,
        classify_forex_state,
        calculate_momentum_confirmation,
        get_state_probability_distribution
    )
    from .forecast_forex import (
        forex_candidates,
        forex_forecast,
        store_forex_prediction
    )
except ImportError:
    from linguistics import (
        calculate_rsi,
        calculate_atr,
        identify_support_resistance,
        classify_forex_state,
        calculate_momentum_confirmation,
        get_state_probability_distribution
    )
    from forecast_forex import (
        forex_candidates,
        forex_forecast,
        store_forex_prediction
    )


class PredictionPipeline:
    """
    Core pipeline for forex-style predictions on Momento rounds.
    Handles streaming data with rolling windows and dynamic thresholds.
    """
    
    def __init__(self, max_window: int = 200):
        self.max_window = max_window
        self.opens = deque(maxlen=max_window)
        self.highs = deque(maxlen=max_window)
        self.lows = deque(maxlen=max_window)
        self.closes = deque(maxlen=max_window)
        self.volumes = deque(maxlen=max_window)
        self.timestamps = deque(maxlen=max_window)
        
        # Performance tracking
        self.processing_times = deque(maxlen=100)
        self.prediction_count = 0
    
    def add_tick(self, multiplier: float, timestamp: float, volume: float = 1.0):
        """Add a single tick (round) to the pipeline"""
        # For tick-by-tick, we treat each round as both open/high/low/close initially
        # Candle builder will aggregate these later
        self.closes.append(multiplier)
        self.opens.append(multiplier)  # Will be updated by candle builder
        self.highs.append(multiplier)  # Will be updated by candle builder
        self.lows.append(multiplier)   # Will be updated by candle builder
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
    
    def add_candle(self, open_price: float, high: float, low: float, close: float, volume: float, timestamp: float):
        """Add a completed candle to the pipeline"""
        self.opens.append(open_price)
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
    
    def get_lists(self) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
        """Convert deques to lists for processing"""
        return (
            list(self.opens),
            list(self.highs),
            list(self.lows),
            list(self.closes),
            list(self.volumes)
        )
    
    def run_full_analysis(self) -> Dict:
        """Execute complete prediction pipeline"""
        start_time = time.time()
        
        opens, highs, lows, closes, volumes = self.get_lists()
        
        if len(closes) < 20:
            return {
                'status': 'insufficient_data',
                'message': f'Need 20 candles, have {len(closes)}',
                'candles_available': len(closes)
            }
        
        # Step 1: Calculate core indicators
        current_price = closes[-1]
        rsi = calculate_rsi(closes)
        atr = calculate_atr(highs, lows, closes)
        sr_levels = identify_support_resistance(highs, lows, closes)
        
        # Step 2: Classify market regime
        market_state = classify_forex_state(opens, highs, lows, closes, volumes, current_price)
        
        # Step 3: Confirm momentum
        momentum_confirmed = calculate_momentum_confirmation(closes, volumes)
        
        # Step 4: Generate candidates with confluence scoring
        candidates = forex_candidates(opens, highs, lows, closes, volumes, top_n=3)
        
        # Step 5: Get full forecast
        forecast = forex_forecast(opens, highs, lows, closes, volumes)
        
        # Step 6: Add pipeline metadata
        processing_time = (time.time() - start_time) * 1000  # ms
        self.processing_times.append(processing_time)
        self.prediction_count += 1
        
        result = {
            'status': 'success',
            'timestamp': time.time(),
            'processing_time_ms': round(processing_time, 2),
            'candles_analyzed': len(closes),
            'current_price': current_price,
            'market_state': market_state,
            'momentum_confirmed': momentum_confirmed,
            'indicators': {
                'rsi': rsi,
                'atr': atr,
                'volatility_factor': round(atr / current_price * 100, 2) if current_price > 0 else 0
            },
            'support_resistance': sr_levels,
            'candidates': candidates,
            'forecast': forecast,
            'performance': {
                'avg_processing_time_ms': round(np.mean(self.processing_times), 2) if self.processing_times else 0,
                'total_predictions': self.prediction_count
            }
        }
        
        # Store for accuracy tracking
        store_forex_prediction(forecast, result['timestamp'], self.prediction_count)
        
        return result
    
    def get_quick_signal(self) -> Optional[Dict]:
        """Generate quick signal without full analysis (for real-time use)"""
        if len(self.closes) < 20:
            return None
        
        opens, highs, lows, closes, volumes = self.get_lists()
        current_price = closes[-1]
        
        # Quick state classification
        state = classify_forex_state(opens, highs, lows, closes, volumes, current_price)
        
        # Quick RSI check
        rsi = calculate_rsi(closes)
        
        # Determine action
        if state == 'Breakout' and rsi > 50:
            action = 'BUY'
            confidence = 'HIGH' if calculate_momentum_confirmation(closes, volumes) else 'MEDIUM'
        elif state == 'Breakout' and rsi < 50:
            action = 'SELL'
            confidence = 'HIGH' if calculate_momentum_confirmation(closes, volumes) else 'MEDIUM'
        elif state == 'Reversal' and rsi < 30:
            action = 'BUY'
            confidence = 'MEDIUM'
        elif state == 'Reversal' and rsi > 70:
            action = 'SELL'
            confidence = 'MEDIUM'
        elif state in ['TrendingUp'] and rsi > 50:
            action = 'HOLD_LONG'
            confidence = 'LOW'
        elif state in ['TrendingDown'] and rsi < 50:
            action = 'HOLD_SHORT'
            confidence = 'LOW'
        else:
            action = 'WAIT'
            confidence = 'LOW'
        
        return {
            'action': action,
            'confidence': confidence,
            'state': state,
            'rsi': rsi,
            'price': current_price,
            'timestamp': time.time()
        }
    
    def reset(self):
        """Clear all data"""
        self.opens.clear()
        self.highs.clear()
        self.lows.clear()
        self.closes.clear()
        self.volumes.clear()
        self.timestamps.clear()
        self.processing_times.clear()
        self.prediction_count = 0


# Convenience function for one-off analysis
def analyze_rounds(rounds: List[Dict]) -> Dict:
    """
    Analyze a list of round dictionaries.
    Expected format: [{'multiplier': 2.45, 'timestamp': 1234567890}, ...]
    """
    pipeline = PredictionPipeline()
    
    for rnd in rounds:
        multiplier = rnd.get('multiplier', rnd.get('crash_point', 1.0))
        timestamp = rnd.get('timestamp', time.time())
        pipeline.add_tick(multiplier, timestamp)
    
    return pipeline.run_full_analysis()
