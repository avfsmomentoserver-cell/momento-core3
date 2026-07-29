"""Causality, scoring and significance tests.

The leakage tests are the important ones. If a fold's training window overlaps
its test range, or a label reads the round it is scored on, every number the
suite emits is meaningless, so those properties are asserted directly rather
than assumed.
"""

from __future__ import annotations

import random

import pytest

from research.labels import horizon_labels, low_streaks
from research.metrics import (
    brier_score,
    calibration_bins,
    hit_rate,
    max_drawdown,
    paper_pnl,
    score_forecasts,
    skill_score,
)
from research.runner import run_strategy
from research.significance import permutation_test
from research.splitter import assert_causal, walk_forward_folds
from research.strategies import BaseRateStrategy, DryStreakStrategy, TimeBasedPatternStrategy


# --------------------------------------------------------------------- labels


def test_label_reads_forward_only():
    """A moonshot at index i must not label index i as positive."""
    values = [1.0, 1.0, 50.0, 1.0, 1.0]
    labels = horizon_labels(values, horizon=1, threshold=20.0)

    assert labels[1] == 1  # the 50x is at index 2, one ahead
    assert labels[2] == 0  # the round itself does not count
    assert labels[3] == 0


def test_incomplete_horizon_is_excluded_not_assumed_negative():
    labels = horizon_labels([1.0] * 10, horizon=3, threshold=20.0)

    assert labels[-3:] == [None, None, None]
    assert all(v == 0 for v in labels[:-3])


def test_horizon_window_boundaries():
    values = [1.0] * 5 + [30.0]
    # From index 0 the 30x sits 5 rounds ahead, so horizon 4 misses it.
    assert horizon_labels(values, horizon=4, threshold=20.0)[0] == 0
    assert horizon_labels(values, horizon=5, threshold=20.0)[0] == 1


def test_low_streaks_are_causal_and_reset():
    streaks = low_streaks([1.1, 1.5, 1.9, 3.0, 1.2], low_threshold=2.0)

    assert streaks == [1, 2, 3, 0, 1]
    # Truncating the series must not change earlier values.
    assert low_streaks([1.1, 1.5], low_threshold=2.0) == streaks[:2]


def test_invalid_horizon_is_rejected():
    with pytest.raises(ValueError):
        horizon_labels([1.0, 2.0], horizon=0)


# -------------------------------------------------------------------- folds


def test_folds_never_overlap_train_and_test():
    folds = walk_forward_folds(3000, horizon=10, n_folds=5, min_train=500)

    assert len(folds) == 5
    assert_causal(folds)
    for fold in folds:
        assert fold.train_end == fold.test_start
        assert fold.test_end <= 3000 - 10


def test_folds_expand_and_tile_the_evaluation_range():
    folds = walk_forward_folds(3000, horizon=10, n_folds=5, min_train=500)

    sizes = [f.train_size for f in folds]
    assert sizes == sorted(sizes)  # expanding window
    for earlier, later in zip(folds, folds[1:]):
        assert earlier.test_end == later.test_start  # contiguous, no gaps
    assert folds[-1].test_end == 2990  # the tail horizon is excluded


def test_too_little_data_yields_no_folds():
    assert walk_forward_folds(300, horizon=10, min_train=500) == []


def test_assert_causal_catches_a_leaking_fold():
    from research.splitter import Fold

    leaking = Fold(index=0, train_start=0, train_end=600, test_start=500, test_end=700)

    with pytest.raises(ValueError, match="leaks"):
        assert_causal([leaking])


# ------------------------------------------------------------------ metrics


def test_brier_and_skill_arithmetic():
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert brier_score([0.0, 1.0], [1, 0]) == 1.0
    assert brier_score([0.5, 0.5], [1, 0]) == 0.25

    assert skill_score(0.1, 0.2) == pytest.approx(0.5)
    assert skill_score(0.2, 0.2) == 0.0  # no better than reference
    assert skill_score(0.4, 0.2) == pytest.approx(-1.0)  # worse


def test_constant_base_rate_forecast_scores_zero_skill():
    """Perfectly calibrated and completely useless: the point of the metric."""
    labels = [1, 0, 0, 1, 0, 0, 0, 0, 1, 0]
    rate = sum(labels) / len(labels)

    score = score_forecasts([rate] * len(labels), labels, n_boot=0)

    assert score.skill == pytest.approx(0.0, abs=1e-12)
    assert score.base_rate == pytest.approx(rate)


def test_skill_ci_is_reported_and_brackets_zero_for_a_useless_forecast():
    labels = [1, 0] * 60
    rate = 0.5

    score = score_forecasts([rate] * len(labels), labels, n_boot=200)
    lo, hi = score.skill_ci["ci"]

    assert score.skill_ci["n_boot"] > 0
    assert lo <= 0.0 <= hi


def test_calibration_bins_partition_the_sample():
    probs = [0.05, 0.15, 0.35, 0.95]
    labels = [0, 0, 1, 1]

    bins = calibration_bins(probs, labels, n_bins=10)

    assert len(bins) == 10
    assert sum(b["count"] for b in bins) == 4
    assert bins[9]["observed_rate"] == 1.0


def test_hit_rate_confusion_counts():
    result = hit_rate([0.9, 0.9, 0.1, 0.1], [1, 0, 1, 0], decision_threshold=0.5)

    assert (result["true_positive"], result["false_positive"]) == (1, 1)
    assert (result["false_negative"], result["true_negative"]) == (1, 1)
    assert result["precision"] == pytest.approx(0.5)
    assert result["recall"] == pytest.approx(0.5)


def test_max_drawdown_measures_peak_to_trough():
    assert max_drawdown([0.0, 5.0, 2.0, 8.0, 1.0]) == pytest.approx(7.0)
    assert max_drawdown([0.0, 1.0, 2.0]) == 0.0


def test_paper_pnl_only_bets_when_the_signal_fires():
    # Signal fires on indices 0 and 2; index 0 wins at 2x, index 2 loses.
    result = paper_pnl([0.9, 0.1, 0.9], [3.0, 99.0, 1.5], cashout=2.0)

    assert result["bets"] == 2
    assert result["wins"] == 1
    assert result["net"] == pytest.approx(0.0)  # +1 then -1
    assert result["ev_per_unit_staked"] == pytest.approx(0.0)


# ------------------------------------------------------- strategies + null


def _fair_tape(n: int, seed: int = 7) -> list:
    """Independent draws with survival P(M >= x) = 0.97/x, the fair-game model."""
    rng = random.Random(seed)
    tape = []
    for _ in range(n):
        u = rng.random()
        tape.append(1.0 if u >= 0.97 else min(10_000.0, 0.97 / (1.0 - u) * (1.0 / 1.0)))
    return tape


def test_base_rate_strategy_predicts_a_constant():
    strategy = BaseRateStrategy(horizon=5, threshold=20.0).fit_on(_fair_tape(600))
    preds = strategy.predict_series(_fair_tape(100, seed=8))

    assert len(set(preds)) == 1
    assert 0.0 <= preds[0] <= 1.0


def test_dry_streak_falls_back_to_base_rate_on_thin_buckets():
    strategy = DryStreakStrategy(horizon=5, threshold=20.0)
    strategy.fit_on([1.1] * 40 + [30.0] * 5)
    table = strategy.learned_table()

    thin = [b for b in table["buckets"] if b["support"] < strategy.MIN_SUPPORT]
    assert all(b["fell_back_to_base_rate"] for b in thin)
    assert all(b["p_target"] is None for b in thin)


def test_dry_streak_implements_the_base_feature_contract():
    strategy = DryStreakStrategy()

    assert strategy.get_name() == "dry_streak"
    assert strategy.get_description()
    assert "skill_score" in strategy.get_metrics()

    payload = strategy.compute([{"multiplier": 1.5}, {"multiplier": 1.2}], {})
    assert 0.0 <= payload["probability"] <= 1.0


def test_walk_forward_run_is_deterministic():
    tape = _fair_tape(1200)
    kwargs = dict(horizon=5, threshold=20.0, n_folds=3, min_train=400, n_boot=50)

    first = run_strategy(DryStreakStrategy, tape, **kwargs)
    second = run_strategy(DryStreakStrategy, tape, **kwargs)

    assert first["pooled"]["skill_score"] == second["pooled"]["skill_score"]
    assert first["pooled"]["skill_ci"] == second["pooled"]["skill_ci"]


def test_run_strategy_reports_insufficient_data_rather_than_guessing():
    result = run_strategy(BaseRateStrategy, _fair_tape(100), horizon=5, min_train=500)

    assert result["insufficient_data"] is True


def test_permutation_test_places_a_noise_statistic_inside_the_null():
    """A statistic independent of order must not look significant."""
    tape = _fair_tape(400)
    result = permutation_test(
        tape, lambda series: sum(series) / len(series), n_permutations=50
    )

    assert result.n_permutations == 50
    # The mean is shuffle-invariant, so observed equals every null draw.
    assert result.observed == pytest.approx(result.null_mean)
    assert not result.significant


def test_permutation_test_detects_a_genuinely_order_dependent_statistic():
    tape = list(range(1, 201))

    def monotonicity(series):
        return sum(1 for a, b in zip(series, series[1:]) if b > a) / (len(series) - 1)

    result = permutation_test(tape, monotonicity, n_permutations=50)

    assert result.observed == pytest.approx(1.0)
    assert result.significant
    assert result.p_value <= 0.05


def test_permutation_p_value_is_never_zero():
    result = permutation_test(list(range(50)), lambda s: s[0], n_permutations=20)

    assert result.p_value > 0.0


def test_time_based_pattern_implements_the_base_feature_contract():
    """Test that TimeBasedPatternStrategy implements the BaseFeature contract."""
    strategy = TimeBasedPatternStrategy()

    assert strategy.get_name() == "time_based_pattern"
    assert strategy.get_description()
    assert "skill_score" in strategy.get_metrics()

    # Test compute function
    rounds = [{"multiplier": 1.5}, {"multiplier": 1.2}, {"multiplier": 3.0}]
    result = strategy.compute(rounds, {})
    assert 0.0 <= result["probability"] <= 1.0
    assert result["strategy"] == "time_based_pattern"
    assert result["fitted"] == False  # Not fitted yet

    # Test fit and prediction
    strategy.fit_on([1.1] * 40 + [30.0] * 5)
    assert strategy.fitted == True
    
    # Test learned table
    table = strategy.learned_table()
    assert "base_rate" in table
    assert "window_size" in table
    assert "patterns" in table
    assert len(table["patterns"]) > 0


def test_time_based_pattern_detects_different_temporal_patterns():
    """Test that the strategy detects different temporal patterns."""
    strategy = TimeBasedPatternStrategy(window_size=5)
    
    # High volatility pattern
    high_vol = [1.0, 10.0, 1.0, 15.0, 1.0, 20.0, 1.0, 5.0, 1.0, 25.0]
    pattern_high = strategy._detect_pattern(high_vol, len(high_vol)-1)
    
    # Low volatility pattern
    low_vol = [1.5, 1.6, 1.4, 1.5, 1.6, 1.4, 1.5, 1.6, 1.4, 1.5]
    pattern_low = strategy._detect_pattern(low_vol, len(low_vol)-1)
    
    # Trending up pattern
    trending_up = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
    pattern_up = strategy._detect_pattern(trending_up, len(trending_up)-1)
    
    # Verify different patterns are detected
    assert pattern_high != pattern_low
    assert pattern_low != pattern_up
    
    # Test insufficient data
    pattern_insufficient = strategy._detect_pattern([1.0, 1.5], 1)
    assert pattern_insufficient == "insufficient_data"
