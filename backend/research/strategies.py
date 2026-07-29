"""Hypotheses under test.

Each strategy subclasses ``features.base.BaseFeature``, so a hypothesis that
survives the significance test moves into ``backend/features/`` and the plugin
inventory with no rewrite.

The split between ``features`` and ``predict_from_feature`` exists for two
reasons. It makes causality auditable: ``features`` is the single place a future
index could leak in, so it is the single place to review. And it keeps the
permutation test affordable, since features are computed once per shuffled tape
in O(n) rather than rebuilt per decision point.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from features.base import BaseFeature

from .labels import (
    DEFAULT_HORIZON,
    DEFAULT_THRESHOLD,
    LOW_THRESHOLD,
    horizon_labels,
    low_streaks,
)


class ResearchStrategy(BaseFeature):
    """A fitted probabilistic forecaster for the moonshot-within-horizon target."""

    name = "research_strategy"
    description = "abstract research strategy"

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.horizon = horizon
        self.threshold = threshold
        self.fitted = False
        self._base_rate: float = 0.0

    # -- research interface -------------------------------------------------

    def features(self, values: Sequence[float]) -> List[Any]:
        """Per-index causal feature. ``features(v)[i]`` may read ``v[:i+1]`` only."""
        raise NotImplementedError

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        raise NotImplementedError

    def predict_from_feature(self, feat: Any) -> float:
        raise NotImplementedError

    def fit_on(self, values: Sequence[float]) -> "ResearchStrategy":
        """Fit on a raw multiplier series, deriving labels internally."""
        self.fit(
            self.features(values),
            horizon_labels(values, self.horizon, self.threshold),
        )
        self.fitted = True
        return self

    def predict_series(self, values: Sequence[float]) -> List[float]:
        """Forecast for every index of a series, in O(n)."""
        return [self.predict_from_feature(f) for f in self.features(values)]

    def predict_proba(self, context: Sequence[Dict[str, Any]]) -> float:
        """Forecast for the round *after* the last round in ``context``."""
        if not context:
            return self._base_rate
        values = [float(r["multiplier"]) for r in context]
        return self.predict_from_feature(self.features(values)[-1])

    # -- BaseFeature contract ----------------------------------------------

    def compute(
        self,
        rounds: Sequence[Dict[str, Any]],
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "strategy": self.get_name(),
            "horizon": self.horizon,
            "threshold": self.threshold,
            "probability": self.predict_proba(rounds),
            "fitted": self.fitted,
            "rounds_seen": len(rounds),
        }

    def backtest(
        self,
        rounds: Sequence[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        from .runner import run_strategy  # local import avoids a cycle

        return run_strategy(
            type(self),
            [float(r["multiplier"]) for r in rounds],
            horizon=int(config.get("horizon", self.horizon)),
            threshold=float(config.get("threshold", self.threshold)),
            n_folds=int(config.get("n_folds", 5)),
            min_train=int(config.get("min_train", 500)),
            decision_threshold=float(config.get("decision_threshold", 0.5)),
            n_boot=int(config.get("n_boot", 500)),
            permutations=int(config.get("permutations", 0)),
        )

    def get_metrics(self) -> List[str]:
        return [
            "probability",
            "brier",
            "reference_brier",
            "skill_score",
            "skill_ci",
            "log_loss",
            "precision",
            "recall",
            "ev_per_unit_staked",
            "max_drawdown",
        ]

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description


class BaseRateStrategy(ResearchStrategy):
    """Constant forecast at the training base rate.

    Not a competitor: the reference every other strategy must beat. If nothing
    beats it, that is the finding, and it is a legitimate one.
    """

    name = "base_rate"
    description = (
        "Predicts the training-set frequency of a moonshot within the horizon, "
        "ignoring all history. The reference baseline."
    )

    def features(self, values: Sequence[float]) -> List[Any]:
        return [None] * len(values)

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        scorable = [int(y) for y in labels if y is not None]
        self._base_rate = (sum(scorable) / len(scorable)) if scorable else 0.0

    def predict_from_feature(self, feat: Any) -> float:
        return self._base_rate


class DryStreakStrategy(ResearchStrategy):
    """The "dry phase" hypothesis from the linguistics vocabulary.

    Claim under test: a run of consecutive sub-2x rounds raises the probability of
    a moonshot in the next ``horizon`` rounds. The strategy learns
    ``P(target | streak bucket)`` from training data only and applies it forward.

    This is the gambler's fallacy stated precisely enough to be falsified. For a
    provably fair game the learned table should be flat across buckets and the
    skill score should sit at zero. Buckets with thin support fall back to the
    base rate rather than reporting a number computed from a handful of rounds.
    """

    name = "dry_streak"
    description = (
        "Conditions the moonshot-within-horizon probability on the current run "
        "of consecutive sub-2x rounds (the 'dry phase')."
    )

    OPEN_ENDED = 10**9
    BUCKETS: List[Tuple[int, int]] = [(0, 0), (1, 2), (3, 4), (5, 9), (10, OPEN_ENDED)]
    MIN_SUPPORT = 30

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
        low_threshold: float = LOW_THRESHOLD,
    ) -> None:
        super().__init__(horizon=horizon, threshold=threshold)
        self.low_threshold = low_threshold
        self._table: Dict[int, float] = {}
        self._support: Dict[int, int] = {}

    def _bucket(self, streak: int) -> int:
        for idx, (lo, hi) in enumerate(self.BUCKETS):
            if lo <= streak <= hi:
                return idx
        return len(self.BUCKETS) - 1

    def features(self, values: Sequence[float]) -> List[Any]:
        return [self._bucket(s) for s in low_streaks(values, self.low_threshold)]

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        totals: Dict[int, int] = {}
        positives: Dict[int, int] = {}
        scorable = hits = 0

        for feat, label in zip(feats, labels):
            if label is None:
                continue
            bucket = int(feat)
            totals[bucket] = totals.get(bucket, 0) + 1
            positives[bucket] = positives.get(bucket, 0) + int(label)
            scorable += 1
            hits += int(label)

        self._base_rate = (hits / scorable) if scorable else 0.0
        self._support = totals
        self._table = {
            bucket: positives[bucket] / count
            for bucket, count in totals.items()
            if count >= self.MIN_SUPPORT
        }

    def predict_from_feature(self, feat: Any) -> float:
        return self._table.get(int(feat), self._base_rate)

    def learned_table(self) -> Dict[str, Any]:
        """Expose the fitted table, which is the actual object of interest.

        A flat table across buckets is the expected result and is worth recording
        verbatim, not just collapsing into a single skill score.
        """
        return {
            "base_rate": self._base_rate,
            "low_threshold": self.low_threshold,
            "buckets": [
                {
                    "bucket": idx,
                    "streak_range": [lo, None if hi >= self.OPEN_ENDED else hi],
                    "support": self._support.get(idx, 0),
                    "p_target": self._table.get(idx),
                    "fell_back_to_base_rate": idx not in self._table,
                }
                for idx, (lo, hi) in enumerate(self.BUCKETS)
            ],
        }


class TimeBasedPatternStrategy(ResearchStrategy):
    """Time-based pattern detection strategy.

    Claim under test: specific temporal patterns in the sequence of rounds
    (e.g., alternating high/low volatility, periodic behavior) predict moonshots
    within the horizon. The strategy learns conditional probabilities from
    training data based on detected temporal patterns.

    This tests whether there are any exploitable temporal structures in the
    round sequence that deviate from independence.
    """

    name = "time_based_pattern"
    description = (
        "Conditions the moonshot-within-horizon probability on detected "
        "temporal patterns in the round sequence (volatility cycles, "
        "alternation patterns, periodic behavior)."
    )

    MIN_SUPPORT = 20

    def __init__(
        self,
        *,
        horizon: int = DEFAULT_HORIZON,
        threshold: float = DEFAULT_THRESHOLD,
        window_size: int = 10,
    ) -> None:
        super().__init__(horizon=horizon, threshold=threshold)
        self.window_size = window_size
        self._table: Dict[str, float] = {}
        self._support: Dict[str, int] = {}

    def _detect_pattern(self, values: Sequence[float], index: int) -> str:
        """Detect temporal pattern at the given index.

        Returns a pattern key based on the recent window's characteristics:
        - 'high_volatility': high variance in recent window
        - 'low_volatility': low variance in recent window
        - 'alternating': high/low alternation pattern
        - 'trending_up': increasing trend
        - 'trending_down': decreasing trend
        - 'stable': stable pattern
        """
        if index < self.window_size:
            return "insufficient_data"

        window = values[index - self.window_size : index]
        if not window:
            return "insufficient_data"

        # Calculate statistics
        mean_val = sum(window) / len(window)
        variance = sum((x - mean_val) ** 2 for x in window) / len(window)
        
        # Detect high/low volatility
        if variance > mean_val * 2:  # high variance relative to mean
            volatility = "high"
        elif variance < mean_val * 0.5:  # low variance relative to mean
            volatility = "low"
        else:
            volatility = "medium"

        # Detect trend
        first_half = window[:len(window)//2]
        second_half = window[len(window)//2:]
        if len(first_half) > 0 and len(second_half) > 0:
            first_mean = sum(first_half) / len(first_half)
            second_mean = sum(second_half) / len(second_half)
            if second_mean > first_mean * 1.2:
                trend = "up"
            elif second_mean < first_mean * 0.8:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Detect alternation pattern
        alternations = 0
        for i in range(1, len(window)):
            if (window[i] > mean_val and window[i-1] <= mean_val) or \
               (window[i] <= mean_val and window[i-1] > mean_val):
                alternations += 1
        
        if alternations > len(window) * 0.6:
            pattern = "alternating"
        else:
            pattern = f"{volatility}_{trend}"

        return pattern

    def features(self, values: Sequence[float]) -> List[Any]:
        """Extract temporal pattern features for each index."""
        return [self._detect_pattern(values, i) for i in range(len(values))]

    def fit(self, feats: Sequence[Any], labels: Sequence[Optional[int]]) -> None:
        """Learn conditional probabilities for each temporal pattern."""
        totals: Dict[str, int] = {}
        positives: Dict[str, int] = {}
        scorable = hits = 0

        for feat, label in zip(feats, labels):
            if label is None or feat == "insufficient_data":
                continue
            pattern = str(feat)
            totals[pattern] = totals.get(pattern, 0) + 1
            positives[pattern] = positives.get(pattern, 0) + int(label)
            scorable += 1
            hits += int(label)

        self._base_rate = (hits / scorable) if scorable else 0.0
        self._support = totals
        self._table = {
            pattern: positives[pattern] / count
            for pattern, count in totals.items()
            if count >= (self.MIN_SUPPORT if hasattr(self, 'MIN_SUPPORT') else 20)
        }

    def predict_from_feature(self, feat: Any) -> float:
        """Predict moonshot probability given a temporal pattern."""
        if feat == "insufficient_data":
            return self._base_rate
        return self._table.get(str(feat), self._base_rate)

    def learned_table(self) -> Dict[str, Any]:
        """Expose the fitted temporal pattern table."""
        patterns = list(self._table.keys()) + list(self._support.keys())
        unique_patterns = list(set(patterns))
        
        return {
            "base_rate": self._base_rate,
            "window_size": self.window_size,
            "patterns": [
                {
                    "pattern": pattern,
                    "support": self._support.get(pattern, 0),
                    "p_target": self._table.get(pattern),
                    "fell_back_to_base_rate": pattern not in self._table,
                }
                for pattern in unique_patterns
            ],
        }


STRATEGY_REGISTRY: Dict[str, type] = {
    BaseRateStrategy.name: BaseRateStrategy,
    DryStreakStrategy.name: DryStreakStrategy,
    TimeBasedPatternStrategy.name: TimeBasedPatternStrategy,
}
