# Strategy Performance Deep Dive

## Individual Strategy Analysis

### Random Baseline Strategy

**Description**: 50/50 random predictions
**Performance**: Consistent ~50% accuracy across all scenarios
**Verdict**: The benchmark to beat - most strategies fail to do so

**Key Insight**: Random baseline is surprisingly competitive, especially for higher targets (20x, 50x). This suggests that complex strategies don't capture real patterns.

### Band Activity Strategy

**Description**: Predicts based on recent high-band (ignition/moonshot/mega) occurrence
**Best Performance**: 5x/10 rounds (88.54% accuracy, 0.939 F1)
**Target Scenario**: 10x/5 rounds (43.01% accuracy, 0.601 F1)

**Key Insight**: Shows promise for lower targets with longer horizons, but fails for the target scenario. The high recall (100%) suggests it's too permissive.

### Momentum Strategy

**Description**: Predicts based on positive price momentum
**Performance**: Consistent ~50% accuracy across scenarios
**Verdict**: As good as random, no better

**Key Insight**: Momentum doesn't predict crashes, which aligns with the independent draw hypothesis.

### Volatility Strategy

**Description**: Predicts based on volatility levels relative to mean
**Best Performance**: 5x/10 rounds (88.37% accuracy, 0.938 F1)
**Target Scenario**: 10x/5 rounds (42.85% accuracy, 0.600 F1)

**Key Insight**: Similar to band activity - works for easy targets but fails for hard ones.

### Recent Highs Strategy

**Description**: Predicts based on recent multipliers >= 50% of target
**Best Performance**: 5x/10 rounds (88.37% accuracy, 0.938 F1)
**Target Scenario**: 10x/5 rounds (42.85% accuracy, 0.600 F1)

**Key Insight**: Another strategy that works for easy targets but not the target scenario.

### Ascending Shape Strategy

**Description**: Predicts based on ascending pattern detection
**Best Performance**: 50x/3 rounds (55.15% accuracy, 0.116 F1)
**Target Scenario**: 10x/5 rounds (50.63% accuracy, 0.431 F1)

**Key Insight**: The only strategy that beats random for the target scenario (50.63% vs 48.45%), but still poor F1 score.

### Mean Reversion Strategy

**Description**: Predicts based on mean reversion theory
**Best Performance**: 5x/10 rounds (71.46% accuracy, 0.828 F1)
**Target Scenario**: 10x/5 rounds (47.36% accuracy, 0.562 F1)

**Key Insight**: Best F1 score for target scenario (0.562), but accuracy underperforms random.

### Streak Strategy

**Description**: Predicts based on consecutive low-round streaks
**Best Performance**: 50x/3 rounds (90.38% accuracy, 0.080 F1)
**Target Scenario**: 10x/5 rounds (57.74% accuracy, 0.090 F1)

**Key Insight**: Highest accuracy but worst F1 scores - the strategy that never bets. Useless for practical betting.

### Ensemble Strategy

**Description**: Majority vote of momentum, volatility, recent_highs
**Best Performance**: 5x/10 rounds (88.37% accuracy, 0.938 F1)
**Target Scenario**: 10x/5 rounds (42.85% accuracy, 0.600 F1)

**Key Insight**: Combination doesn't guarantee improvement - ensemble underperforms individual components for target scenario.

## Performance Matrix

### Accuracy Matrix (%)

| Strategy | 5x/3 | 5x/5 | 5x/10 | 10x/3 | 10x/5 | 10x/10 | 20x/3 | 20x/5 | 20x/10 | 50x/3 | 50x/5 | 50x/10 |
|----------|-------|-------|--------|-------|--------|---------|-------|-------|---------|-------|-------|---------|
| Random | 49.5 | 48.9 | 50.9 | 49.5 | 48.5 | 49.5 | 47.0 | 48.5 | 50.8 | 50.3 | 51.1 | 49.5 |
| Band | 47.7 | 67.5 | 88.5 | 28.5 | 43.0 | 65.4 | 15.0 | 23.9 | 40.5 | 7.0 | 11.1 | 18.9 |
| Momentum | 52.2 | 50.5 | 51.2 | 49.0 | 48.7 | 51.8 | 48.8 | 47.9 | 49.5 | 49.7 | 49.5 | 49.5 |
| Volatility | 47.5 | 67.3 | 88.4 | 28.3 | 42.9 | 65.2 | 14.8 | 23.8 | 40.3 | 6.9 | 11.0 | 18.7 |
| Recent Highs | 47.5 | 67.3 | 88.4 | 28.3 | 42.9 | 65.2 | 15.0 | 23.9 | 40.5 | 15.1 | 18.5 | 24.9 |
| Ascending | 50.0 | 48.3 | 44.6 | 51.5 | 50.6 | 47.4 | 54.7 | 54.3 | 50.6 | 55.2 | 54.6 | 52.8 |
| Mean Rev | 49.7 | 60.3 | 71.5 | 39.7 | 47.4 | 57.2 | 31.6 | 37.5 | 45.0 | 25.8 | 28.2 | 32.3 |
| Streak | 52.9 | 34.8 | 14.7 | 70.5 | 57.7 | 36.1 | 83.1 | 75.2 | 59.1 | 90.4 | 86.4 | 78.8 |
| Ensemble | 47.5 | 67.3 | 88.4 | 28.3 | 42.9 | 65.2 | 14.8 | 23.8 | 40.3 | 9.8 | 13.9 | 21.0 |

### F1 Score Matrix

| Strategy | 5x/3 | 5x/5 | 5x/10 | 10x/3 | 10x/5 | 10x/10 | 20x/3 | 20x/5 | 20x/10 | 50x/3 | 50x/5 | 50x/10 |
|----------|-------|-------|--------|-------|--------|---------|-------|-------|---------|-------|-------|---------|
| Random | 0.473 | 0.556 | 0.650 | 0.352 | 0.447 | 0.563 | 0.177 | 0.322 | 0.456 | 0.097 | 0.177 | 0.280 |
| Band | 0.645 | 0.805 | 0.939 | 0.442 | 0.601 | 0.790 | 0.258 | 0.385 | 0.576 | 0.129 | 0.198 | 0.316 |
| Momentum | 0.514 | 0.581 | 0.649 | 0.356 | 0.452 | 0.584 | 0.219 | 0.301 | 0.446 | 0.128 | 0.182 | 0.274 |
| Volatility | 0.644 | 0.804 | 0.938 | 0.441 | 0.600 | 0.789 | 0.258 | 0.384 | 0.575 | 0.128 | 0.198 | 0.316 |
| Recent Highs | 0.644 | 0.804 | 0.938 | 0.441 | 0.600 | 0.789 | 0.258 | 0.385 | 0.576 | 0.130 | 0.199 | 0.315 |
| Ascending | 0.452 | 0.535 | 0.581 | 0.327 | 0.431 | 0.517 | 0.228 | 0.324 | 0.414 | 0.116 | 0.171 | 0.246 |
| Mean Rev | 0.597 | 0.725 | 0.828 | 0.429 | 0.562 | 0.700 | 0.258 | 0.382 | 0.533 | 0.119 | 0.188 | 0.296 |
| Streak | 0.079 | 0.080 | 0.073 | 0.073 | 0.090 | 0.071 | 0.082 | 0.092 | 0.069 | 0.080 | 0.069 | 0.052 |
| Ensemble | 0.644 | 0.804 | 0.938 | 0.441 | 0.600 | 0.789 | 0.258 | 0.384 | 0.575 | 0.128 | 0.199 | 0.315 |

## Strategy Archetypes

### The "Never Bet" Strategy

**Example**: Streak strategy
**Pattern**: High accuracy (>80%), terrible F1 (<0.1)
**Reality**: Achieves accuracy by almost never predicting positive events
**Usefulness**: None for betting

### The "Always Bet" Strategy

**Example**: Band activity, volatility, recent highs (10x scenarios)
**Pattern**: 100% recall, poor accuracy (~40%)
**Reality**: Predicts positive events constantly, but most are wrong
**Usefulness**: High loss rate, poor value

### The "Balanced" Strategy

**Example**: Random, momentum, ascending shape
**Pattern**: Accuracy ~50%, balanced precision/recall
**Reality**: Predicts at random chance levels
**Usefulness: No edge over random

### The "Specialized" Strategy

**Example**: Mean reversion
**Pattern**: Better F1 scores, poor accuracy
**Reality**: Good at catching wins but misses many opportunities
**Usefulness**: Niche applications, not general purpose

## Failure Mode Analysis

### Why Complex Strategies Fail

1. **Overfitting**: Strategies capture dataset-specific noise
2. **Lookahead Bias**: Testing methodology may introduce subtle biases
3. **Mathematical Reality**: Independent draws have no predictable patterns
4. **Pattern Dilution**: More complex strategies add noise rather than signal

### Why Simple Strategies Succeed (Sometimes)

1. **Less Overfitting**: Simpler strategies have fewer parameters to overfit
2. **Random Luck**: Sometimes simple approaches get lucky on test data
3. **Base Rate Exploitation**: Some strategies exploit known base rates
4. **Measurement Bias**: Testing methodology may favor certain approaches

---

**Date**: 2026-07-29  
**Analysis**: 9 strategies × 12 scenarios deep dive  
**Finding**: No strategy meaningfully beats random for target scenario