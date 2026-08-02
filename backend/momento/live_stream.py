"""
Live Stream Module - Real-time WebSocket ingestion for Momento game data.
Converts raw ticks into OHLCV candles for technical analysis.
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Callable
from collections import deque
from datetime import datetime

class LiveStream:
    def __init__(self, ws_url: str = "wss://momento-game-server/stream"):
        self.ws_url = ws_url
        self.is_connected = False
        self.current_round: Optional[Dict] = None
        self.candles: Dict[str, deque] = {
            '1m': deque(maxlen=500),
            '5m': deque(maxlen=500),
            '15m': deque(maxlen=500)
        }
        self.current_candle: Dict[str, Dict] = {
            '1m': None,
            '5m': None,
            '15m': None
        }
        self.tick_callbacks: List[Callable] = []
        self.candle_callbacks: List[Callable] = []
        
    async def connect(self):
        """Establish WebSocket connection with reconnection logic."""
        while True:
            try:
                # Simulated connection - replace with actual websockets library in production
                print(f"[INFO] Connecting to {self.ws_url}...")
                self.is_connected = True
                print(f"[SUCCESS] WebSocket connected. Session ID: sess_{int(time.time())}")
                await self._listen()
            except Exception as e:
                print(f"[ERROR] Connection lost: {e}. Reconnecting in 5s...")
                self.is_connected = False
                await asyncio.sleep(5)
    
    async def _listen(self):
        """Listen for incoming ticks and process them."""
        # Simulation loop - replace with actual ws.recv() in production
        while self.is_connected:
            # Simulate receiving a tick every 1-3 seconds
            await asyncio.sleep(1 + (time.time() % 2))
            tick = self._generate_simulated_tick()
            await self._process_tick(tick)
    
    def _generate_simulated_tick(self) -> Dict:
        """Generate a simulated tick for testing."""
        import random
        round_id = int(time.time() * 1000) % 100000
        multiplier = 1.0 + random.expovariate(0.5)
        if random.random() < 0.1:
            multiplier *= random.uniform(2, 10)  # Occasional high multiplier
        return {
            'round_id': round_id,
            'multiplier': round(multiplier, 2),
            'timestamp': time.time(),
            'status': 'crashed' if random.random() < 0.3 else 'running'
        }
    
    async def _process_tick(self, tick: Dict):
        """Process incoming tick and update candles."""
        print(f"[DATA] Tick received: Round #{tick['round_id']} | Multiplier: {tick['multiplier']}x")
        
        # Notify tick callbacks
        for callback in self.tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                print(f"[ERROR] Tick callback error: {e}")
        
        # Update candles for each timeframe
        for timeframe in self.candles.keys():
            candle = self._update_candle(tick, timeframe)
            if candle and candle.get('closed'):
                print(f"[CANDLE] {timeframe} Candle Closed: O:{candle['open']} H:{candle['high']} L:{candle['low']} C:{candle['close']} V:{candle['volume']}")
                # Notify candle callbacks
                for callback in self.candle_callbacks:
                    try:
                        callback(timeframe, candle)
                    except Exception as e:
                        print(f"[ERROR] Candle callback error: {e}")
    
    def _update_candle(self, tick: Dict, timeframe: str) -> Optional[Dict]:
        """Update or create candle for given timeframe."""
        tf_seconds = {'1m': 60, '5m': 300, '15m': 900}[timeframe]
        candle_timestamp = int(tick['timestamp'] // tf_seconds) * tf_seconds
        
        # Initialize new candle if needed
        if self.current_candle[timeframe] is None or \
           self.current_candle[timeframe].get('timestamp') != candle_timestamp:
            
            # Close previous candle if exists
            if self.current_candle[timeframe]:
                self.current_candle[timeframe]['closed'] = True
                self.candles[timeframe].append(self.current_candle[timeframe])
            
            # Create new candle
            self.current_candle[timeframe] = {
                'timestamp': candle_timestamp,
                'open': tick['multiplier'],
                'high': tick['multiplier'],
                'low': tick['multiplier'],
                'close': tick['multiplier'],
                'volume': 1,
                'closed': False
            }
            return None
        else:
            # Update existing candle
            candle = self.current_candle[timeframe]
            candle['high'] = max(candle['high'], tick['multiplier'])
            candle['low'] = min(candle['low'], tick['multiplier'])
            candle['close'] = tick['multiplier']
            candle['volume'] += 1
            return candle
    
    def on_tick(self, callback: Callable):
        """Register callback for tick events."""
        self.tick_callbacks.append(callback)
    
    def on_candle(self, callback: Callable):
        """Register callback for completed candle events."""
        self.candle_callbacks.append(callback)
    
    def get_recent_candles(self, timeframe: str, count: int = 100) -> List[Dict]:
        """Get recent candles for a timeframe."""
        return list(self.candles[timeframe])[-count:]

# Example usage
if __name__ == "__main__":
    stream = LiveStream()
    
    def on_tick(tick):
        print(f"Tick: {tick['multiplier']}x")
    
    def on_candle(tf, candle):
        print(f"Candle closed [{tf}]: {candle['close']}x")
    
    stream.on_tick(on_tick)
    stream.on_candle(on_candle)
    
    # Run for demo
    asyncio.run(stream.connect())
