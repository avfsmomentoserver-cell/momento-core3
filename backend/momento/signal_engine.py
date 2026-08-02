"""
Signal Engine - Real-time signal generation from live tick data.
Processes candles through the prediction pipeline and emits trading signals.
"""
import asyncio
import time
from typing import Dict, List, Optional, Callable
from collections import deque

class SignalEngine:
    def __init__(self):
        self.signals: deque = deque(maxlen=1000)
        self.signal_callbacks: List[Callable] = []
        self.last_signal_time: float = 0
        self.min_signal_interval: float = 5.0  # Minimum seconds between signals
        
    def process_candle(self, timeframe: str, candle: Dict):
        """Process a completed candle and generate signals if conditions are met."""
        current_time = time.time()
        
        # Rate limit signals
        if current_time - self.last_signal_time < self.min_signal_interval:
            return
        
        # Simulate signal generation logic
        # In production, this would call the actual pipeline.py
        signal = self._generate_signal(timeframe, candle)
        
        if signal:
            self.signals.append(signal)
            self.last_signal_time = current_time
            
            # Log signal
            print(f"[SIGNAL] {signal['type']} Signal Generated @ {signal['price']}x")
            print(f"  - Target Range: {signal['target_low']}x - {signal['target_high']}x")
            print(f"  - Stop Loss (Invalidation): {signal['stop_loss']}x")
            print(f"  - Risk/Reward: 1:{signal['risk_reward']}")
            
            # Notify callbacks
            for callback in self.signal_callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    print(f"[ERROR] Signal callback error: {e}")
    
    def _generate_signal(self, timeframe: str, candle: Dict) -> Optional[Dict]:
        """Generate a trading signal based on candle data."""
        import random
        
        # Simulate market state classification
        states = ['TRENDING_UP', 'TRENDING_DOWN', 'RANGING', 'BREAKOUT']
        state = random.choice(states)
        
        # Only generate signals for strong trends or breakouts
        if state not in ['TRENDING_UP', 'TRENDING_DOWN', 'BREAKOUT']:
            return None
        
        current_price = candle['close']
        
        # Calculate targets and stop loss based on ATR simulation
        atr = current_price * 0.05  # Simulated 5% ATR
        
        if state == 'TRENDING_UP' or state == 'BREAKOUT':
            signal_type = 'BUY'
            target_low = current_price + atr * 1.5
            target_high = current_price + atr * 3.0
            stop_loss = current_price - atr * 2.5
        else:  # TRENDING_DOWN
            signal_type = 'SELL'
            target_low = current_price - atr * 3.0
            target_high = current_price - atr * 1.5
            stop_loss = current_price + atr * 2.5
        
        risk = abs(current_price - stop_loss)
        reward = abs((target_low + target_high) / 2 - current_price)
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        return {
            'timestamp': time.time(),
            'timeframe': timeframe,
            'type': signal_type,
            'state': state,
            'price': current_price,
            'target_low': round(target_low, 2),
            'target_high': round(target_high, 2),
            'stop_loss': round(stop_loss, 2),
            'risk_reward': risk_reward,
            'confidence': round(random.uniform(0.75, 0.95), 2),
            'confluence_count': random.randint(2, 5)
        }
    
    def on_signal(self, callback: Callable):
        """Register callback for signal events."""
        self.signal_callbacks.append(callback)
    
    def get_recent_signals(self, count: int = 50) -> List[Dict]:
        """Get recent signals."""
        return list(self.signals)[-count:]
    
    def get_last_signal(self) -> Optional[Dict]:
        """Get the most recent signal."""
        return self.signals[-1] if self.signals else None

# Example usage
if __name__ == "__main__":
    engine = SignalEngine()
    
    def on_signal(signal):
        print(f"New Signal: {signal['type']} {signal['state']}")
    
    engine.on_signal(on_signal)
    
    # Simulate processing some candles
    test_candles = [
        {'close': 2.45, 'high': 3.12, 'low': 1.00, 'open': 1.00, 'volume': 142},
        {'close': 1.85, 'high': 2.50, 'low': 1.20, 'open': 2.10, 'volume': 98},
        {'close': 4.20, 'high': 5.00, 'low': 3.80, 'open': 3.90, 'volume': 215},
    ]
    
    for i, candle in enumerate(test_candles):
        engine.process_candle('1m', candle)
        time.sleep(6)  # Respect rate limit
