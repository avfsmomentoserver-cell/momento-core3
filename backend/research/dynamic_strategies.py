"""Dynamic adaptive strategies for orchestrator integration.

This module implements advanced, fully dynamic strategies that adapt to market
conditions, volatility, and opportunity patterns for optimal safe betting with
high bet sizes on low take-profit opportunities.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .labels import DEFAULT_HORIZON, DEFAULT_THRESHOLD, horizon_labels, low_streaks
from .strategies import ResearchStrategy


@dataclass
class MarketState:
    """Current market state classification."""
    volatility: str = "normal"  # low, normal, high, extreme
    trend: str = "neutral"  # up, down, neutral
    momentum: str = "weak"  # weak, moderate, strong
    regime: str = "stable"  # stable, transitioning, volatile
    confidence_level: float = 0.5


class VolatilityAdaptiveStrategy(ResearchStrategy):
    """Dynamically adapts betting strategy based on market volatility.
    
    High volatility → smaller bets, higher targets (risk management)
    Low volatility → larger bets, lower targets (capital efficiency)
    
    This strategy optimizes for high bet size on low take-profit opportunities
    when market conditions are favorable.
    """

    name = "volatility_adaptive"
    description = (
        "Adapts betting size and targets based on real-time volatility. "
        "High bet sizes on low take-profit in stable conditions, "
        "conservative sizing in volatile conditions."
    )

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
        window_size: int = 20,
    ) -> None:
        super().__init__(horizon=horizon, threshold=threshold)
        self.window_size = window_size
        self._volatility_history: deque = deque(maxlen=window_size)
        self._state_probabilities: Dict[str, float] = {}
        self._min_support = 25

    def _calculate_volatility(self, values: Sequence[float], index: int) -> float:
        """Calculate rolling volatility at given index."""
        if index < self.window_size:
            return 0.0
        
        window = values[index - self.window_size : index]
        if not window:
            return 0.0
        
        mean_val = sum(window) / len(window)
        variance = sum((x - mean_val) ** 2 for x in window) / len(window)
        return math.sqrt(variance)

    def _classify_volatility(self, volatility: float) -> str:
        """Classify volatility level."""
        if volatility < 0.5:
            return "low"
        elif volatility < 1.5:
            return "normal"
        elif volatility < 3.0:
            return "high"
        else:
            return "extreme"

    def _calculate_momentum(self, values: Sequence[float], index: int) -> float:
        """Calculate momentum indicator."""
        if index < 5:
            return 0.0
        
        recent = values[max(0, index - 5) : index]
        if len(recent) < 2:
            return 0.0
        
        # Simple momentum: rate of change
        return (recent[-1] - recent[0]) / len(recent) if recent[0] > 0 else 0.0

    def _get_market_state(self, values: Sequence[float], index: int) -> MarketState:
        """Determine current market state."""
        volatility = self._calculate_volatility(values, index)
        vol_class = self._classify_volatility(volatility)
        
        momentum = self._calculate_momentum(values, index)
        if momentum > 0.1:
            trend = "up"
        elif momentum < -0.1:
            trend = "down"
        else:
            trend = "neutral"
        
        momentum_strength = abs(momentum)
        if momentum_strength > 0.3:
            mom_strength = "strong"
        elif momentum_strength > 0.1:
            mom_strength = "moderate"
        else:
            mom_strength = "weak"
        
        # Determine regime based on recent volatility changes
        if len(self._volatility_history) >= 5:
            recent_vols = list(self._volatility_history)[-5:]
            vol_change = max(recent_vols) - min(recent_vols)
            if vol_change > 1.0:
                regime = "volatile"
            elif vol_change > 0.5:
                regime = "transitioning"
            else:
                regime = "stable"
        else:
            regime = "stable"
        
        return MarketState(
            volatility=vol_class,
            trend=trend,
            momentum=mom_strength,
            regime=regime,
        )

    def features(self, values: Sequence[float]) -> List[Any]:
        """Extract market state features."""
        states = []
        for i in range(len(values)):
            state = self._get_market_state(values, i)
            self._volatility_history.append(self._calculate_volatility(values, i))
            states.append(state)
        return states

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        """Learn state-specific moonshot probabilities."""
        state_counts: Dict[str, int] = {}
        state_positives: Dict[str, int] = {}
        scorable = hits = 0

        for feat, label in zip(feats, labels):
            if label is None:
                continue
            
            state = feat if isinstance(feat, MarketState) else self._get_market_state([1.0], 0)
            state_key = f"{state.volatility}_{state.trend}_{state.regime}"
            
            state_counts[state_key] = state_counts.get(state_key, 0) + 1
            if label == 1:
                state_positives[state_key] = state_positives.get(state_key, 0) + 1
            
            scorable += 1
            hits += label

        self._base_rate = hits / scorable if scorable else 0.0
        self._state_probabilities = {
            state: state_positives.get(state, 0) / count
            for state, count in state_counts.items()
            if count >= self._min_support
        }

    def predict_from_feature(self, feat: Any) -> float:
        """Predict moonshot probability based on market state."""
        if not isinstance(feat, MarketState):
            return self._base_rate
        
        state_key = f"{feat.volatility}_{feat.trend}_{feat.regime}"
        base_prob = self._state_probabilities.get(state_key, self._base_rate)
        
        # Dynamic confidence adjustment based on volatility
        vol_multiplier = {
            "low": 1.3,      # Boost confidence in low volatility
            "normal": 1.0,
            "high": 0.7,     # Reduce confidence in high volatility
            "extreme": 0.4,  # Strong reduction in extreme volatility
        }.get(feat.volatility, 1.0)
        
        # Regime adjustment
        regime_multiplier = {
            "stable": 1.2,       # Boost in stable regimes
            "transitioning": 1.0,
            "volatile": 0.6,     # Reduce in volatile regimes
        }.get(feat.regime, 1.0)
        
        adjusted_prob = base_prob * vol_multiplier * regime_multiplier
        return max(0.0, min(1.0, adjusted_prob))

    def get_betting_recommendation(self, state: MarketState, probability: float) -> Dict[str, Any]:
        """Get dynamic betting recommendation based on state."""
        # High bet size for low take-profit in stable/low volatility
        if state.volatility == "low" and state.regime == "stable":
            return {
                "bet_size_multiplier": 1.5,  # High bet size
                "target_multiplier": 1.3,    # Low take-profit
                "confidence_threshold": 0.3,  # Lower threshold for entries
                "strategy": "aggressive_low_target",
            }
        elif state.volatility == "normal" and state.regime == "stable":
            return {
                "bet_size_multiplier": 1.0,
                "target_multiplier": 1.8,
                "confidence_threshold": 0.4,
                "strategy": "balanced",
            }
        elif state.volatility in ["high", "extreme"]:
            return {
                "bet_size_multiplier": 0.5,  # Reduce bet size
                "target_multiplier": 2.5,    # Higher target for safety
                "confidence_threshold": 0.6,  # Higher threshold
                "strategy": "conservative_high_target",
            }
        else:
            return {
                "bet_size_multiplier": 0.8,
                "target_multiplier": 2.0,
                "confidence_threshold": 0.5,
                "strategy": "moderate",
            }


class MomentumReversalStrategy(ResearchStrategy):
    """Hybrid momentum-reversal strategy for dynamic opportunity detection.
    
    Combines momentum following with reversal detection to identify:
    - Momentum continuation opportunities (trend following)
    - Reversal opportunities (mean reversion)
    - Optimal entry/exit points for high bet sizing
    """

    name = "momentum_reversal"
    description = (
        "Hybrid strategy combining momentum following and reversal detection. "
        "Identifies optimal entry points for high bet sizing on low take-profit "
        "opportunities using dynamic market analysis."
    )

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
        momentum_window: int = 10,
        reversal_window: int = 20,
    ) -> None:
        super().__init__(horizon=horizon, threshold=threshold)
        self.momentum_window = momentum_window
        self.reversal_window = reversal_window
        self._momentum_threshold = 0.15
        self._reversal_threshold = 2.0
        self._pattern_probabilities: Dict[str, float] = {}
        self._min_support = 20

    def _calculate_rsi(self, values: Sequence[float], index: int, period: int = 14) -> float:
        """Calculate Relative Strength Index for reversal detection."""
        if index < period + 1:
            return 50.0  # Neutral
        
        window = values[index - period : index]
        if len(window) < period:
            return 50.0
        
        gains = []
        losses = []
        for i in range(1, len(window)):
            change = window[i] - window[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _detect_pattern(self, values: Sequence[float], index: int) -> str:
        """Detect momentum or reversal pattern."""
        if index < self.reversal_window:
            return "insufficient_data"
        
        # Calculate momentum
        recent_window = values[index - self.momentum_window : index]
        momentum = (recent_window[-1] - recent_window[0]) / len(recent_window) if recent_window[0] > 0 else 0
        
        # Calculate RSI for reversal detection
        rsi = self._calculate_rsi(values, index)
        
        # Pattern classification
        if abs(momentum) > self._momentum_threshold:
            if momentum > 0:
                if rsi > 70:
                    return "momentum_up_overbought"  # Potential reversal
                else:
                    return "momentum_up_strong"  # Continue momentum
            else:
                if rsi < 30:
                    return "momentum_down_oversold"  # Potential reversal
                else:
                    return "momentum_down_strong"  # Continue momentum
        else:
            if rsi > 70:
                return "reversal_overbought"  # Reversal opportunity
            elif rsi < 30:
                return "reversal_oversold"  # Reversal opportunity
            else:
                return "neutral"

    def features(self, values: Sequence[float]) -> List[Any]:
        """Extract momentum-reversal pattern features."""
        return [self._detect_pattern(values, i) for i in range(len(values))]

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        """Learn pattern-specific probabilities."""
        pattern_counts: Dict[str, int] = {}
        pattern_positives: Dict[str, int] = {}
        scorable = hits = 0

        for feat, label in zip(feats, labels):
            if label is None or feat == "insufficient_data":
                continue
            
            pattern = str(feat)
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            if label == 1:
                pattern_positives[pattern] = pattern_positives.get(pattern, 0) + 1
            
            scorable += 1
            hits += label

        self._base_rate = hits / scorable if scorable else 0.0
        self._pattern_probabilities = {
            pattern: pattern_positives.get(pattern, 0) / count
            for pattern, count in pattern_counts.items()
            if count >= self._min_support
        }

    def predict_from_feature(self, feat: Any) -> float:
        """Predict moonshot probability based on pattern."""
        if feat == "insufficient_data":
            return self._base_rate
        
        base_prob = self._pattern_probabilities.get(str(feat), self._base_rate)
        
        # Pattern-specific adjustments
        pattern_adjustments = {
            "momentum_up_strong": 1.2,
            "momentum_down_strong": 0.8,
            "momentum_up_overbought": 0.6,  # Reversal risk
            "momentum_down_oversold": 1.4,  # Reversal opportunity
            "reversal_overbought": 1.3,     # Good reversal opportunity
            "reversal_oversold": 1.3,       # Good reversal opportunity
            "neutral": 1.0,
        }
        
        adjustment = pattern_adjustments.get(str(feat), 1.0)
        return max(0.0, min(1.0, base_prob * adjustment))

    def get_betting_recommendation(self, pattern: str, probability: float) -> Dict[str, Any]:
        """Get betting recommendation based on pattern."""
        # High bet size for reversal opportunities (low take-profit)
        if pattern in ["reversal_overbought", "reversal_oversold"]:
            return {
                "bet_size_multiplier": 1.4,  # High bet size
                "target_multiplier": 1.4,    # Low take-profit
                "confidence_threshold": 0.35,
                "strategy": "reversal_aggressive",
            }
        elif pattern in ["momentum_down_oversold"]:
            return {
                "bet_size_multiplier": 1.3,
                "target_multiplier": 1.5,
                "confidence_threshold": 0.4,
                "strategy": "momentum_reversal",
            }
        elif pattern in ["momentum_up_strong"]:
            return {
                "bet_size_multiplier": 1.1,
                "target_multiplier": 1.8,
                "confidence_threshold": 0.45,
                "strategy": "momentum_follow",
            }
        else:
            return {
                "bet_size_multiplier": 0.8,
                "target_multiplier": 2.0,
                "confidence_threshold": 0.5,
                "strategy": "conservative",
            }


class DynamicConfidenceStrategy(ResearchStrategy):
    """Dynamically calibrates confidence based on multiple market factors.
    
    Uses ensemble of indicators to provide adaptive confidence scores:
    - Volatility-adjusted confidence
    - Momentum-adjusted confidence
    - Streak-adjusted confidence
    - Regime-adjusted confidence
    
    Optimizes for high bet sizing when multiple factors align.
    """

    name = "dynamic_confidence"
    description = (
        "Ensemble strategy that dynamically calibrates confidence based on "
        "volatility, momentum, streaks, and regime. Optimizes bet sizing "
        "when multiple factors align for low take-profit opportunities."
    )

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
        ensemble_window: int = 15,
    ) -> None:
        super().__init__(horizon=horizon, threshold=threshold)
        self.ensemble_window = ensemble_window
        self._factor_weights: Dict[str, float] = {
            "volatility": 0.25,
            "momentum": 0.25,
            "streak": 0.25,
            "regime": 0.25,
        }
        self._min_support = 30

    def _calculate_volatility_score(self, values: Sequence[float], index: int) -> float:
        """Calculate volatility-based confidence score (0-1)."""
        if index < self.ensemble_window:
            return 0.5
        
        window = values[index - self.ensemble_window : index]
        mean_val = sum(window) / len(window)
        variance = sum((x - mean_val) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        
        # Lower volatility = higher confidence
        if std < 0.3:
            return 0.9
        elif std < 0.8:
            return 0.7
        elif std < 1.5:
            return 0.5
        else:
            return 0.3

    def _calculate_momentum_score(self, values: Sequence[float], index: int) -> float:
        """Calculate momentum-based confidence score."""
        if index < 5:
            return 0.5
        
        recent = values[max(0, index - 5) : index]
        if len(recent) < 2:
            return 0.5
        
        momentum = (recent[-1] - recent[0]) / len(recent)
        # Moderate positive momentum = higher confidence
        if 0 < momentum < 0.3:
            return 0.8
        elif momentum > 0.3:
            return 0.6  # Too extended
        elif -0.3 < momentum < 0:
            return 0.5
        else:
            return 0.4  # Negative momentum

    def _calculate_streak_score(self, values: Sequence[float], index: int) -> float:
        """Calculate streak-based confidence score."""
        streaks = low_streaks(values, low_threshold=2.0)
        if index >= len(streaks):
            return 0.5
        
        current_streak = streaks[index]
        # Moderate streak = higher confidence (not too short, not too long)
        if 3 <= current_streak <= 7:
            return 0.8
        elif current_streak < 3:
            return 0.5
        else:
            return 0.4  # Extended streak

    def _calculate_regime_score(self, values: Sequence[float], index: int) -> float:
        """Calculate regime-based confidence score."""
        if index < self.ensemble_window * 2:
            return 0.5
        
        recent = values[index - self.ensemble_window : index]
        older = values[index - self.ensemble_window * 2 : index - self.ensemble_window]
        
        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older)
        
        # Stable regime = higher confidence
        change_ratio = abs(recent_mean - older_mean) / older_mean if older_mean > 0 else 0
        
        if change_ratio < 0.1:
            return 0.9
        elif change_ratio < 0.3:
            return 0.7
        else:
            return 0.5

    def features(self, values: Sequence[float]) -> List[Any]:
        """Extract ensemble confidence features."""
        features = []
        for i in range(len(values)):
            vol_score = self._calculate_volatility_score(values, i)
            mom_score = self._calculate_momentum_score(values, i)
            streak_score = self._calculate_streak_score(values, i)
            regime_score = self._calculate_regime_score(values, i)
            
            # Weighted ensemble
            ensemble_score = (
                vol_score * self._factor_weights["volatility"] +
                mom_score * self._factor_weights["momentum"] +
                streak_score * self._factor_weights["streak"] +
                regime_score * self._factor_weights["regime"]
            )
            
            features.append({
                "volatility": vol_score,
                "momentum": mom_score,
                "streak": streak_score,
                "regime": regime_score,
                "ensemble": ensemble_score,
            })
        return features

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        """Learn ensemble-based probabilities."""
        # Bucket ensemble scores for probability learning
        bucket_counts: Dict[int, int] = {}
        bucket_positives: Dict[int, int] = {}
        scorable = hits = 0

        for feat, label in zip(feats, labels):
            if label is None or not isinstance(feat, dict):
                continue
            
            ensemble = feat.get("ensemble", 0.5)
            bucket = int(ensemble * 10)  # 0-10 buckets
            
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            if label == 1:
                bucket_positives[bucket] = bucket_positives.get(bucket, 0) + 1
            
            scorable += 1
            hits += label

        self._base_rate = hits / scorable if scorable else 0.0
        self._ensemble_probabilities = {
            bucket: bucket_positives.get(bucket, 0) / count
            for bucket, count in bucket_counts.items()
            if count >= self._min_support
        }

    def predict_from_feature(self, feat: Any) -> float:
        """Predict using ensemble confidence."""
        if not isinstance(feat, dict):
            return self._base_rate
        
        ensemble = feat.get("ensemble", 0.5)
        bucket = int(ensemble * 10)
        base_prob = self._ensemble_probabilities.get(bucket, self._base_rate)
        
        # Boost probability when multiple factors align
        vol = feat.get("volatility", 0.5)
        mom = feat.get("momentum", 0.5)
        streak = feat.get("streak", 0.5)
        regime = feat.get("regime", 0.5)
        
        # High alignment bonus
        high_scores = sum(1 for s in [vol, mom, streak, regime] if s > 0.7)
        if high_scores >= 3:
            alignment_bonus = 1.3
        elif high_scores >= 2:
            alignment_bonus = 1.15
        else:
            alignment_bonus = 1.0
        
        return max(0.0, min(1.0, base_prob * alignment_bonus))

    def get_betting_recommendation(self, ensemble_feat: Dict[str, Any], probability: float) -> Dict[str, Any]:
        """Get betting recommendation based on ensemble."""
        ensemble = ensemble_feat.get("ensemble", 0.5)
        high_scores = sum(1 for s in [
            ensemble_feat.get("volatility", 0.5),
            ensemble_feat.get("momentum", 0.5),
            ensemble_feat.get("streak", 0.5),
            ensemble_feat.get("regime", 0.5)
        ] if s > 0.7)
        
        # High bet size when multiple factors align (low take-profit)
        if high_scores >= 3 and ensemble > 0.7:
            return {
                "bet_size_multiplier": 1.6,  # Maximum bet size
                "target_multiplier": 1.3,    # Minimum take-profit
                "confidence_threshold": 0.25,
                "strategy": "ensemble_aggressive",
            }
        elif high_scores >= 2 and ensemble > 0.6:
            return {
                "bet_size_multiplier": 1.3,
                "target_multiplier": 1.5,
                "confidence_threshold": 0.35,
                "strategy": "ensemble_moderate",
            }
        else:
            return {
                "bet_size_multiplier": 0.7,
                "target_multiplier": 2.2,
                "confidence_threshold": 0.55,
                "strategy": "ensemble_conservative",
            }


# Register new strategies
from .strategies import STRATEGY_REGISTRY

STRATEGY_REGISTRY.update({
    VolatilityAdaptiveStrategy.name: VolatilityAdaptiveStrategy,
    MomentumReversalStrategy.name: MomentumReversalStrategy,
    DynamicConfidenceStrategy.name: DynamicConfidenceStrategy,
})
