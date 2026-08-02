# Momento TradingView Implementation Guide

## Overview
This implementation converts Momento crash game rounds into a professional Forex-style TradingView interface, treating each round as a market candle with full technical analysis capabilities.

## Core Concepts

### 1. Rounds as Candles
- **Open**: Multiplier at start of timeframe bucket (or previous close)
- **High**: Highest multiplier in the timeframe bucket
- **Low**: Lowest multiplier (always 1.00x for crash games)
- **Close**: Last multiplier before timeframe ends or crash point
- **Volume**: Number of rounds in the timeframe bucket

### 2. Forex Market States
The system classifies market conditions into 7 states:
- **Ranging**: Price moving sideways between support/resistance
- **TrendingUp**: Consistent higher highs and higher lows
- **TrendingDown**: Consistent lower highs and lower lows
- **Breakout**: Price breaking above resistance with momentum (RSI > 60)
- **Reversal**: Price bouncing from support with momentum shift (RSI < 40)
- **Consolidation**: Tight range near pivot point with low volatility
- **FalseBreak**: Failed breakout attempt with RSI divergence

### 3. Technical Indicators
- **RSI (Relative Strength Index)**: Momentum oscillator (0-100)
  - Overbought: > 70
  - Oversold: < 30
- **ATR (Average True Range)**: Volatility measurement
- **EMA (Exponential Moving Average)**: 20, 50, 200 periods
- **Bollinger Bands**: Upper/Middle/Lower bands for volatility envelope
- **Support/Resistance**: Classic Pivot Points + Fibonacci Retracement

## File Structure

```
backend/momento/
├── linguistics.py          # Forex utilities, RSI, ATR, S/R detection
├── forecast_forex.py       # Prediction logic, state sequences, candidates
└── tradingview_adapter.py  # Data conversion, Pine Script export

web/src/pages/dashboard/
├── MomentoTradingView.tsx        # Basic dashboard view
└── MomentoTradingViewFull.tsx    # Full TradingView implementation
```

## Testing Instructions

### Backend Testing

1. **Test Forex State Classification**
```bash
cd backend
python3 -c "
from momento.linguistics import classify_forex_state, calculate_rsi
import random

# Generate sample data
data = [random.uniform(1.0, 50.0) for _ in range(50)]
state = classify_forex_state(data)
rsi = calculate_rsi(data)

print(f'Market State: {state}')
print(f'RSI: {rsi:.2f}')
"
```

2. **Test Support/Resistance Detection**
```bash
python3 -c "
from momento.linguistics import identify_support_resistance
import random

data = [random.uniform(1.0, 100.0) for _ in range(100)]
levels = identify_support_resistance(data)

print('Support Levels:', levels['support'][:3])
print('Resistance Levels:', levels['resistance'][:3])
print('Pivot Point:', levels['pivot'])
print('Fibonacci Levels:', levels['fibonacci'])
"
```

3. **Test Forecast Generation**
```bash
python3 -c "
from momento.forecast_forex import forex_forecast, forex_candidates
import random

data = [random.uniform(1.0, 50.0) for _ in range(100)]
forecast = forex_forecast(data)
candidates = forex_candidates(data)

print('Forecast:', forecast)
print('Top 3 Candidates:')
for c in candidates[:3]:
    print(f\"  {c['label']}: {c['probability']:.2%}\")
"
```

4. **Test TradingView Adapter**
```bash
python3 -c "
from momento.tradingview_adapter import convert_to_candles, generate_pine_script

data = [random.uniform(1.0, 50.0) for _ in range(100)]
candles = convert_to_candles(data, timeframe='5m')
pine = generate_pine_script(candles)

print(f'Generated {len(candles)} candles')
print('Pine Script Preview (first 200 chars):')
print(pine[:200])
"
```

### Frontend Testing

1. **Start Development Server**
```bash
cd web
npm install
npm run dev
```

2. **Navigate to Dashboard**
- Open browser to `http://localhost:3000` (or your configured port)
- Go to `/dashboard/tradingview-full` for the complete implementation
- Go to `/dashboard/tradingview` for the basic version

3. **Test Features**
- ✅ Switch timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- ✅ Use drawing tools (trendline, horizontal, fibonacci, rectangle)
- ✅ Toggle fullscreen mode
- ✅ View support/resistance lines on chart
- ✅ Check AI forecast panel for predictions
- ✅ Monitor round list sidebar for live updates
- ✅ Export chart as PNG

## Configuration

### Environment Variables
```bash
# Backend (.env)
MOMENTO_API_URL=https://api.momento.com
FOREX_RSI_PERIOD=14
FOREX_ATR_PERIOD=14
FOREX_EMA_PERIODS=20,50,200
MAX_BACKTEST_ROUNDS=10000
```

### DevAI Test Configuration
See `devai.config.json` for automated testing scenarios.

## Key Differences: 50x vs 10000x

- **50x**: Typical multiplier threshold for significant events
  - Used in RSI calculations for extreme moves
  - Breakout detection threshold
  - Visual highlighting on charts

- **10000x**: System configuration limit
  - `max_backtest_rounds`: Maximum historical rounds for analysis
  - Rate limiting window size
  - NOT used as a multiplier value in predictions

## Pine Script Integration

The generated Pine Script can be:
1. Copied from the UI export function
2. Pasted into TradingView's Pine Editor
3. Added to charts as a custom indicator
4. Used for backtesting strategies on real forex pairs

Example strategy signals:
- **Buy**: When state changes to "Breakout" with RSI > 60
- **Sell**: When state changes to "Reversal" with RSI < 40
- **Stop Loss**: Below nearest support level
- **Take Profit**: At next resistance level or 1.5x ATR

## Troubleshooting

### Common Issues

1. **Chart not rendering**
   - Check if `lightweight-charts` is installed: `npm list lightweight-charts`
   - Verify container has dimensions (min-height: 500px)

2. **No data appearing**
   - Ensure backend API is running
   - Check network tab for failed requests
   - Verify round data format matches expected schema

3. **Drawing tools not working**
   - Click tool icon first, then click on chart
   - Double-click to finish drawing
   - Press ESC to cancel current tool

4. **Incorrect state classification**
   - Increase sample size (minimum 20 rounds recommended)
   - Check for data gaps or anomalies
   - Adjust RSI/ATR periods in config

## Next Steps

1. Connect to live Momento API websocket
2. Add real-time alert system for state changes
3. Implement strategy backtesting engine
4. Add social sharing for chart analysis
5. Create mobile-responsive version

## License
Proprietary - Momento Core Project
