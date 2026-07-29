# Megaplan Orchestrator Documentation

## Overview

The Megaplan Orchestrator is an advanced decision-making system that provides dynamic precision, comprehensive bankroll tracking, recovery strategies, chase systems, and vigorous backtesting capabilities. It extends the existing orchestrator with military-grade intelligence features for automated trading decisions.

## Key Features

### 1. Dynamic Decision-Making Engine
- **Multi-factor Analysis**: Considers confidence, market state, volatility, trend strength, volume profile, time-of-day factors, and historical accuracy
- **Opportunity Scoring**: Calculates a 0-1 opportunity score based on market conditions, state bonuses, streak adjustments, and exhaustion factors
- **Risk Appetite Calculation**: Dynamically adjusts risk tolerance based on bankroll health, consecutive losses/wins, and confidence levels
- **Precision Levels**: Automatically selects between CONSERVATIVE, MODERATE, AGGRESSIVE, or DYNAMIC precision based on context

### 2. Comprehensive Bankroll Tracking
- **Real-time State Tracking**: Monitors current bankroll, daily P&L, drawdown, consecutive losses/wins, win rate, and average win/loss
- **Risk Level Assessment**: Automatically classifies risk level as NORMAL, ELEVATED, or CRITICAL
- **Historical Tracking**: Maintains bankroll history for analysis and pattern recognition
- **Safety Limits**: Enforces daily loss limits, maximum drawdown limits, and per-round risk limits

### 3. Recovery Strategies
- **9 Recovery Strategies**:
  - **None**: Standard trading without recovery
  - **Martingale**: Double position after each loss (risky)
  - **Anti-Martingale**: Increase after wins, decrease after losses
  - **Fibonacci**: Use Fibonacci sequence for position sizing
  - **D'Alembert**: Increase by one unit after loss, decrease after win
  - **Labouchere**: Cross out numbers from sequence after wins
  - **Fixed Percentage**: Risk fixed percentage of bankroll
  - **Kelly Criterion**: Optimal sizing based on edge and odds
  - **Dynamic Sizing**: Adaptive sizing based on market conditions

- **Automatic Activation**: Triggers when drawdown exceeds threshold or consecutive losses hit limit
- **Progress Tracking**: Monitors recovery progress and estimates rounds to recovery
- **Safety Limits**: Enforces maximum steps, drawdown limits, and emergency stops

### 4. Chase Strategies
- **6 Chase Strategies**:
  - **None**: Do not chase high multipliers
  - **Linear**: Linear increase in chase attempts
  - **Exponential**: Exponential increase in position size
  - **Fibonacci Chase**: Use Fibonacci sequence for chase attempts
  - **Hybrid**: Combine multiple chase strategies
  - **Conditional**: Chase based on specific market conditions

- **Smart Activation**: Only activates when conditions are favorable (confidence, volatility, market state)
- **Expected Value Calculation**: Calculates EV for each chase strategy
- **Risk-Reward Analysis**: Provides detailed risk-reward ratios
- **Safety Conditions**: Enforces maximum loss per chase, step limits, and minimum confidence

### 5. Vigorous Backtesting
- **Historical Simulation**: Tests strategies on historical data
- **Phased Testing**: Supports warmup, normal, and stress testing phases
- **Performance Metrics**: Tracks success rates, P&L, and recovery rounds
- **Strategy Comparison**: Compares all strategies to find optimal configurations
- **Conditional Testing**: Tests strategies under specific market conditions

## Architecture

### Backend Components

#### `megaplan_orchestrator.py`
- **Core Module**: Contains all decision-making logic
- **Data Classes**: `BankrollState`, `RecoveryState`, `ChaseState`, `DecisionContext`, `MegaplanInstruction`
- **Enums**: `RecoveryStrategy`, `ChaseStrategy`, `DecisionPrecision`
- **Configuration**: `DEFAULT_MEGAPLAN_SETTINGS`, `RECOVERY_STRATEGIES`, `CHASE_STRATEGIES`

#### API Endpoints (`engines.py`)
- `GET /megaplan` - Generate comprehensive megaplan
- `GET /megaplan/settings` - Get megaplan settings
- `PUT /megaplan/settings` - Update megaplan settings
- `GET /megaplan/bankroll` - Get current bankroll state
- `POST /megaplan/backtest/recovery` - Backtest recovery strategy
- `POST /megaplan/backtest/chase` - Backtest chase strategy
- `GET /megaplan/backtest/compare` - Compare all strategies

#### Database Schema (`db.py`)
- `megaplan_decisions` - Store all megaplan decisions
- `megaplan_bankroll_history` - Track bankroll over time
- `megaplan_recovery_events` - Log recovery strategy activations
- `megaplan_chase_events` - Log chase strategy activations

### Frontend Components

#### `MegaplanOrchestrator.tsx`
- **Main Dashboard**: Four-tab interface (Overview, Recovery, Chase, Backtest)
- **Real-time Updates**: Polls for live plan updates
- **Interactive Controls**: Settings configuration with sliders and selects
- **Visual Feedback**: Color-coded risk levels, progress bars, and status badges
- **Backtest Results**: Side-by-side strategy comparison with recommendations

## Usage

### Basic Usage

```python
from momento.megaplan_orchestrator import megaplan_plan

# Generate a megaplan
payload = store.analysis_payload(source)
plan = megaplan_plan(payload)

# Access instruction
instruction = plan['instruction']
print(f"Action: {instruction['action']}")
print(f"Position Size: {instruction['position_size']}")
print(f"Target: {instruction['target_multiplier']}x")
```

### Configure Recovery Strategy

```python
from momento.megaplan_orchestrator import update_megaplan_settings

# Enable Fibonacci recovery
update_megaplan_settings({
    'recovery_strategy': 'fibonacci',
    'recovery_trigger_threshold': 0.08,
})
```

### Configure Chase Strategy

```python
# Enable conditional chase
update_megaplan_settings({
    'chase_strategy': 'conditional',
    'chase_target_multiplier': 50.0,
    'chase_max_steps': 12,
})
```

### Backtest Strategies

```python
from momento.megaplan_orchestrator import backtest_recovery_strategy, compare_strategies

# Backtest specific strategy
result = backtest_recovery_strategy(source, 'fibonacci')
print(f"Success Rate: {result['recovery_success_rate']}")
print(f"P&L: {result['pnl_percentage']}%")

# Compare all strategies
comparison = compare_strategies(source)
print(f"Best Recovery: {comparison['recommendations']['best_recovery_strategy']}")
print(f"Best Chase: {comparison['recommendations']['best_chase_strategy']}")
```

## Decision-Making Process

### 1. Context Building
The system first builds a comprehensive decision context by analyzing:
- Market state and prediction confidence
- Volatility and trend strength
- Streak patterns and band exhaustion
- Time-of-day factors
- Historical accuracy

### 2. Risk Assessment
Bankroll state is evaluated to determine:
- Current drawdown and risk level
- Consecutive losses/wins impact
- Win rate and average performance
- Available risk capital

### 3. Strategy Evaluation
Recovery and chase strategies are evaluated for activation:
- Check trigger conditions
- Calculate expected values
- Verify safety limits
- Estimate recovery rounds

### 4. Precision Selection
Based on context and risk, the system selects:
- CONSERVATIVE: Low confidence, high risk
- MODERATE: Balanced approach
- AGGRESSIVE: High confidence, low risk
- DYNAMIC: Adaptive based on conditions

### 5. Position Sizing
Position size is calculated using:
- Recovery/chase multipliers if active
- Selected sizing method (fixed, confidence-scaled, Kelly, dynamic)
- Risk limits and bankroll constraints
- Opportunity score adjustments

### 6. Instruction Generation
Final instruction includes:
- Action (ENTER, PREPARE, WAIT, STAND_DOWN)
- Position size and targets
- Reasoning and risk analysis
- Execution conditions and safety checks

## Safety Features

### Risk Limits
- **Daily Loss Limit**: Stops trading when daily loss exceeds threshold
- **Maximum Drawdown**: Emergency stop at critical drawdown levels
- **Per-Round Risk**: Limits position size as percentage of bankroll
- **Consecutive Loss Limits**: Automatically reduces size after losing streaks

### Recovery Safety
- **Maximum Steps**: Limits recovery strategy iterations
- **Emergency Stop**: Hard stop at critical drawdown
- **Progress Tracking**: Monitors recovery effectiveness
- **Automatic Deactivation**: Disables if recovery fails

### Chase Safety
- **Conditional Activation**: Only chases when conditions are favorable
- **Maximum Steps**: Limits chase iterations
- **Expected Value Filter**: Only chases with positive EV
- **Bankroll Allocation**: Limits capital allocated to chasing

## Performance Optimization

### Database Optimization
- Indexed queries for fast lookups
- Separate tables for different data types
- Efficient history tracking

### Caching Strategy
- Settings cached in memory
- Bankroll state calculated on-demand
- Backtest results cached for comparison

### API Performance
- Async endpoint handling
- Efficient payload processing
- Minimal database round-trips

## Best Practices

1. **Start Conservative**: Begin with CONSERVATIVE precision and no recovery/chase strategies
2. **Test Thoroughly**: Use backtesting to validate strategies before live deployment
3. **Monitor Risk**: Keep a close eye on drawdown and risk levels
4. **Adjust Settings**: Fine-tune settings based on performance data
5. **Use Safety Limits**: Always enforce daily loss limits and maximum drawdown
6. **Diversify Strategies**: Don't rely on a single recovery or chase strategy
7. **Review Regularly**: Analyze performance metrics and adjust accordingly

## Troubleshooting

### Common Issues

**Issue**: Recovery strategy not activating
- **Solution**: Check trigger threshold and current drawdown level

**Issue**: Chase strategy not activating
- **Solution**: Verify confidence, volatility, and market state conditions

**Issue**: Poor backtest results
- **Solution**: Adjust strategy parameters or try different strategies

**Issue**: High drawdown
- **Solution**: Reduce risk per round, enable recovery strategy, or stop trading

## Future Enhancements

- Machine learning integration for strategy optimization
- Real-time strategy adaptation based on performance
- Advanced pattern recognition for market conditions
- Multi-symbol portfolio management
- Cloud-based backtesting with distributed computing
- Mobile app for real-time monitoring
- Advanced analytics and reporting
- Social trading features for strategy sharing

## Integration Points

### Existing Orchestrator
The megaplan orchestrator complements the existing orchestrator by:
- Providing more sophisticated decision-making
- Adding recovery and chase capabilities
- Offering comprehensive backtesting
- Maintaining backward compatibility

### Autopilot Integration
Can be integrated with autopilot for:
- Automated decision execution
- Real-time performance tracking
- Automatic strategy adjustment
- Risk management integration

### Analysis Engines
Uses data from:
- Signal engine for confidence scores
- Forecast engine for target ranges
- Pattern recognition for state detection
- Volatility analysis for risk assessment

## Conclusion

The Megaplan Orchestrator provides a comprehensive, military-grade decision-making system that extends the existing Momento platform with advanced recovery strategies, chase systems, and vigorous backtesting capabilities. It's designed for dynamic precision decision-making with comprehensive safety features and real-time monitoring.