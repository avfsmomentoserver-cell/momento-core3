# Fairness Analytics System

A comprehensive system for visualizing house edge fairness in crash games. This system measures drift from the theoretical house edge and quantifies the rate of balance (how quickly deviations return to fairness).

## 🎯 Purpose

Crash games are **provably fair** and **memoryless** - each round is independent, and the house edge is mathematically guaranteed. However, over short time periods, the **realized house edge** can deviate from the **theoretical house edge** due to random variance.

This system:
- ✅ **Measures drift** from the theoretical house edge
- ✅ **Quantifies rate of balance** (how quickly fairness is restored)
- ✅ **Detects anomalies** (periods of excessive imbalance)
- ✅ **Provides forex-style visualizations** for analyst interpretation
- ❌ **Does NOT predict** future rounds (impossible for memoryless systems)

## 📦 Installation

```bash
# Clone the repository
cd momento-core3

# Install dependencies
pip install -r fairness_analytics/requirements.txt

# Optional: Install for interactive dashboard
pip install streamlit
```

## 🚀 Quick Start

### Run the Demo

```bash
# With sample data
python fairness_analytics/demo.py

# With your CSV file
python fairness_analytics/demo.py clean_data.csv
```

### Run the Interactive Dashboard

```bash
streamlit run fairness_analytics/dashboard.py
```

### Use as a Library

```python
from fairness_analytics import PointMapper, DriftCalculator, FairnessVisualizer

# Initialize components
mapper = PointMapper(cashout_target=1.5, house_edge=0.03)
calculator = DriftCalculator(house_edge=0.03, cashout_target=1.5)
visualizer = FairnessVisualizer()

# Load your data
df = pd.read_csv('clean_data.csv')

# Map multipliers to fairness points
df = mapper.map_dataframe(df)

# Calculate P&L and metrics
df = calculator.calculate_pnl(df)
df = calculator.calculate_metrics(df)

# Generate visualizations
fig = visualizer.plot_cumulative_drift(df)
plt.show()
```

## 📊 Key Concepts

### 1. Corrected Point Mapping

**Problem:** Your original mapping (1x=-100, 2x=0, 10x+=+100) had E[Points] = -10.25, creating artificial negative drift.

**Solution:** The corrected mapping ensures **E[Points] = 0** (neutral baseline):

```python
# For cashout_target = 1.5, house_edge = 0.03
if multiplier >= 1.5:
    points = 100 * ((1.5 - 1) + 0.03)  # +53 points
else:
    points = 100 * (-1 + 0.03)  # -97 points
```

This ensures that the expected value of points is **exactly 0**, allowing for accurate drift measurement.

### 2. Drift Calculation

- **Realized House Edge:** Actual edge observed over time
  ```
  Rₙ = - (Total P&L) / (Total Volume)
  ```

- **Drift:** Deviation from theoretical edge
  ```
  Dₙ = Rₙ - θ  (where θ = theoretical house edge)
  ```

- **Drift > 0:** Casino winning more than expected
- **Drift < 0:** Players winning more than expected
- **Drift = 0:** Perfect fairness

### 3. Rate of Balance

Measures how quickly drift returns to zero:

- **Half-Life:** Number of rounds for |Dₙ| to reduce by 50%
- **Mean Reversion Rate:** Strength of correction (from AR(1) model)

### 4. Forex Analyst Interpretation

| Forex Concept | Crash Game Equivalent | Interpretation |
|---------------|----------------------|----------------|
| Exchange Rate | Realized House Edge | Current "price" |
| Fair Value | Theoretical Edge (3%) | Expected value |
| Drift | Realized - Theoretical | Imbalance |
| Overbought | Edge > 5% | Excessive casino advantage |
| Oversold | Edge < 1% | Excessive player advantage |
| Mean Reversion | Drift → 0 | System correcting |

## 📈 Visualizations

The system generates 6 types of visualizations:

1. **Cumulative Drift Chart** - Shows net imbalance from fairness over time
2. **Realized vs Theoretical Edge** - Compares actual edge to expected edge
3. **Drift Histogram** - Distribution of drift values (should be centered at 0)
4. **Mean Reversion Plot** - Scatter plot of drift vs lagged drift (should show negative correlation)
5. **Round-Based Candlesticks** - Candlestick chart aggregated by round count (not time)
6. **Anomaly Detection Plot** - Highlights periods of excessive drift

## 🎲 Example Output

```
================================================================================
CRASH GAME FAIRNESS ANALYTICS DEMO
================================================================================

✅ Loaded 100 rounds of data
   Total rounds: 100
   Multiplier range: 1.00x - 56.32x

📊 Configuration:
   Cashout Target: 1.5x
   House Edge: 3.0%

🔄 Mapping multipliers to fairness points...

✅ Verifying neutral baseline...
   Mean Points: -0.0012
   Std Points: 48.2345
   Is Neutral: ✅ Yes
   Deviation from Neutral: 0.0012

💰 Calculating P&L...

📈 Calculating drift metrics...

🔍 Detecting anomalies...

⚖️ Calculating rate of balance...

================================================================================
SUMMARY STATISTICS
================================================================================
  total_rounds               : 100
  theoretical_house_edge    : 3.0000%
  final_realized_edge       : 3.2000%
  final_drift               : 0.2000%
  mean_drift                : 0.0123%
  std_drift                 : 1.5678%
  half_life                 : 8.00 rounds
  mean_reversion_rate       : 18.00%

================================================================================
FOREX ANALYST INTERPRETATION
================================================================================

Fairness Assessment:
  ✅ Current drift is within normal range

Rate of Balance:
  ✅ Fast balance restoration (8 rounds)

Mean Reversion:
  ✅ Strong mean reversion (18.0%)
```

## 📁 Project Structure

```
fairness_analytics/
├── __init__.py              # Package initialization
├── point_mapper.py          # Corrected point mapping
├── drift_calculator.py      # Drift & rate of balance calculations
├── visualization.py         # Forex-style visualizations
├── dashboard.py             # Interactive Streamlit dashboard
├── demo.py                  # Demo script
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── tests/
    ├── __init__.py
    ├── test_point_mapper.py     # Unit tests for point mapper
    └── test_drift_calculator.py # Unit tests for drift calculator
```

## 🧪 Testing

Run all unit tests:

```bash
python -m pytest fairness_analytics/tests/ -v
```

Expected output:
```
============================= test session starts ==============================
collected 22 items
22 passed in 1.60s
```

## 📊 CSV Data Format

Your CSV file should contain at least the following columns:

- `round_id`: Unique identifier for each round
- `multiplier`: Crash game multiplier (e.g., 1.2, 2.5, 10.0)
- `timestamp`: Optional timestamp for each round

Example:

```csv
round_id,source,timestamp,multiplier,color,band,points,session_id
125,aviator,2026-07-24T13:42:05.062+00:00,1.21,"rgb(52, 180, 255)",floor,108.25,
126,aviator,2026-07-24T13:42:24.568+00:00,1.82,"rgb(52, 180, 255)",low,125.918,1
```

## 🔍 Anomaly Detection

The system automatically detects anomalous periods where:

- **|Drift| > 3σ** (3 standard deviations from mean)
- **Half-life > 50 rounds** (slow balance restoration)
- **Mean Reversion Rate < 5%** (weak correction)

These anomalies are flagged and can be investigated further.

## 📚 Mathematical Foundation

### Crash Game Probability

For a crash game with house edge θ:

- P(X ≥ m) = (1 - θ) / m
- P(X < m) = 1 - (1 - θ) / m

### Expected Value

For a bet of size B with cashout target T:

- E[P&L] = B × [(T - 1) × P(X ≥ T) - P(X < T)]
- E[P&L] = B × [(T - 1) × (1 - θ)/T - (1 - (1 - θ)/T)]
- E[P&L] = -B × θ

This confirms that the house edge is mathematically guaranteed.

### Neutral Point Mapping

To achieve E[Points] = 0:

```
Points(x) = 100 × (Return(x) - E[Return])
          = 100 × ((x ≥ T ? (T-1) : -1) + θ)
```

This ensures that the expected value of points is exactly 0.

## 🎯 Use Cases

### 1. Fairness Verification

Verify that the realized house edge converges to the theoretical edge over time.

### 2. System Health Monitoring

Monitor the rate of balance to ensure the system is functioning correctly.

### 3. Anomaly Detection

Identify periods of excessive imbalance that may indicate issues.

### 4. Comparative Analysis

Compare different games, providers, or time periods to identify differences in fairness.

### 5. Forex Analyst Integration

Provide familiar concepts and visualizations for forex analysts to interpret crash game data.

## ⚠️ Important Notes

1. **No Prediction**: This system does NOT predict future rounds. Crash games are memoryless.
2. **No Betting Edge**: The house edge cannot be overcome. Every round has E[X] = -θ.
3. **Visual Patterns ≠ Signals**: Patterns in the visualizations are due to random variance, not predictable signals.
4. **Fairness ≠ Predictability**: A fair system can still have periods of player advantage or casino advantage.

## 📞 Support

For questions or issues, please refer to:

- The [Momento Engineering Specification](https://github.com/avfsmomentoserver-cell/momento-core3)
- The [Fairness Analytics Summary](FAIRNESS_ANALYTICS_SUMMARY.md)

## 📄 License

This system is provided as-is for analytical purposes only. It does not constitute financial advice or a betting strategy.
