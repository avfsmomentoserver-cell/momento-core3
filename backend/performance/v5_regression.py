"""V5 Performance Regression Testing Framework.

Tracks performance over time and detects regressions against established baselines.
Provides automated regression detection and alerting.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from .v5_baseline import V5BaselineRunner, V5BenchmarkResult, V5BaselineReport


@dataclass
class RegressionThreshold:
    """Regression detection threshold."""
    metric_name: str
    max_degradation_percent: float
    min_improvement_percent: float = 0.0
    severity: str = "warning"  # warning, critical


@dataclass
class RegressionAlert:
    """Performance regression alert."""
    metric_name: str
    current_value: float
    baseline_value: float
    degradation_percent: float
    threshold_percent: float
    severity: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class RegressionReport:
    """Complete regression test report."""
    baseline_timestamp: str
    current_timestamp: str
    duration_hours: float
    total_metrics: int
    regressed_metrics: int
    improved_metrics: int
    stable_metrics: int
    alerts: List[RegressionAlert]
    summary: str
    trend_analysis: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class V5RegressionTester:
    """Test for performance regressions against V5 baseline."""

    # Default regression thresholds
    DEFAULT_THRESHOLDS = [
        RegressionThreshold("db_insert_latency_p50", max_degradation_percent=20.0, severity="critical"),
        RegressionThreshold("db_insert_latency_p99", max_degradation_percent=20.0, severity="critical"),
        RegressionThreshold("db_select_latency_p50", max_degradation_percent=20.0, severity="critical"),
        RegressionThreshold("db_throughput", max_degradation_percent=15.0, severity="critical"),
        RegressionThreshold("analysis_latency_500_rounds", max_degradation_percent=30.0, severity="warning"),
        RegressionThreshold("analysis_throughput", max_degradation_percent=15.0, severity="warning"),
        RegressionThreshold("api_latency_p50", max_degradation_percent=30.0, severity="warning"),
        RegressionThreshold("api_latency_p99", max_degradation_percent=30.0, severity="warning"),
        RegressionThreshold("api_throughput", max_degradation_percent=15.0, severity="warning"),
    ]

    def __init__(self, baseline_path: Optional[Path] = None, history_path: Optional[Path] = None):
        self.baseline_path = baseline_path or Path(__file__).parent.parent / "data" / "v5_baseline.json"
        self.history_path = history_path or Path(__file__).parent.parent / "data" / "v5_regression_history.json"
        self.thresholds = self.DEFAULT_THRESHOLDS

    def load_baseline(self) -> Optional[V5BaselineReport]:
        """Load the baseline report."""
        runner = V5BaselineRunner(storage_path=self.baseline_path)
        return runner.load_report()

    def run_current_benchmark(self) -> V5BaselineReport:
        """Run current benchmark."""
        runner = V5BaselineRunner()
        return runner.generate_report()

    def detect_regressions(
        self,
        baseline: V5BaselineReport,
        current: V5BaselineReport
    ) -> List[RegressionAlert]:
        """Detect performance regressions."""
        alerts = []

        # Create lookup for baseline benchmarks
        baseline_map = {b.metric_name: b for b in baseline.benchmarks}

        for current_benchmark in current.benchmarks:
            metric_name = current_benchmark.metric_name
            baseline_benchmark = baseline_map.get(metric_name)

            if not baseline_benchmark:
                continue

            # Get threshold for this metric
            threshold = next(
                (t for t in self.thresholds if t.metric_name == metric_name),
                None
            )

            if not threshold:
                continue

            # Calculate degradation (positive = worse, negative = better)
            # For latency metrics: higher is worse
            # For throughput metrics: lower is worse
            if "latency" in metric_name or "memory" in metric_name:
                degradation = ((current_benchmark.measured_value - baseline_benchmark.measured_value)
                              / baseline_benchmark.measured_value * 100)
            else:  # throughput, ops/sec
                degradation = ((baseline_benchmark.measured_value - current_benchmark.measured_value)
                              / baseline_benchmark.measured_value * 100)

            # Check if regression exceeds threshold
            if degradation > threshold.max_degradation_percent:
                alerts.append(RegressionAlert(
                    metric_name=metric_name,
                    current_value=current_benchmark.measured_value,
                    baseline_value=baseline_benchmark.measured_value,
                    degradation_percent=degradation,
                    threshold_percent=threshold.max_degradation_percent,
                    severity=threshold.severity,
                ))

        return alerts

    def detect_improvements(
        self,
        baseline: V5BaselineReport,
        current: V5BaselineReport
    ) -> List[Dict[str, Any]]:
        """Detect performance improvements."""
        improvements = []

        baseline_map = {b.metric_name: b for b in baseline.benchmarks}

        for current_benchmark in current.benchmarks:
            metric_name = current_benchmark.metric_name
            baseline_benchmark = baseline_map.get(metric_name)

            if not baseline_benchmark:
                continue

            # Calculate improvement (positive = better)
            if "latency" in metric_name or "memory" in metric_name:
                improvement = ((baseline_benchmark.measured_value - current_benchmark.measured_value)
                              / baseline_benchmark.measured_value * 100)
            else:  # throughput, ops/sec
                improvement = ((current_benchmark.measured_value - baseline_benchmark.measured_value)
                              / baseline_benchmark.measured_value * 100)

            if improvement > 5.0:  # More than 5% improvement
                improvements.append({
                    "metric_name": metric_name,
                    "current_value": current_benchmark.measured_value,
                    "baseline_value": baseline_benchmark.measured_value,
                    "improvement_percent": improvement,
                })

        return improvements

    def calculate_trend_analysis(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        if len(history) < 2:
            return {"status": "insufficient_data"}

        trends = {}

        # Analyze each metric
        metric_names = set()
        for entry in history:
            for benchmark in entry.get("benchmarks", []):
                metric_names.add(benchmark["metric_name"])

        for metric_name in metric_names:
            values = []
            timestamps = []

            for entry in history:
                for benchmark in entry.get("benchmarks", []):
                    if benchmark["metric_name"] == metric_name:
                        values.append(benchmark["measured_value"])
                        timestamps.append(entry["timestamp"])

            if len(values) >= 2:
                # Calculate trend (positive = increasing/worse for latency)
                first_val = values[0]
                last_val = values[-1]
                change_percent = ((last_val - first_val) / first_val * 100) if first_val > 0 else 0

                # Calculate slope (linear regression)
                n = len(values)
                if n >= 3:
                    x = list(range(n))
                    mean_x = sum(x) / n
                    mean_y = sum(values) / n

                    numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
                    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
                    slope = numerator / denominator if denominator > 0 else 0
                else:
                    slope = 0

                trends[metric_name] = {
                    "change_percent": change_percent,
                    "trend": "increasing" if change_percent > 5 else "decreasing" if change_percent < -5 else "stable",
                    "slope": slope,
                    "data_points": n,
                }

        return trends

    def generate_regression_report(self) -> RegressionReport:
        """Generate complete regression test report."""
        # Load baseline
        baseline = self.load_baseline()
        if not baseline:
            raise ValueError("No baseline found. Run baseline generation first.")

        # Run current benchmark
        current = self.run_current_benchmark()

        # Calculate duration
        baseline_time = datetime.fromisoformat(baseline.timestamp)
        current_time = datetime.fromisoformat(current.timestamp)
        duration_hours = (current_time - baseline_time).total_seconds() / 3600

        # Detect regressions
        alerts = self.detect_regressions(baseline, current)

        # Detect improvements
        improvements = self.detect_improvements(baseline, current)

        # Count metrics
        total_metrics = len(current.benchmarks)
        regressed_metrics = len(alerts)
        improved_metrics = len(improvements)
        stable_metrics = total_metrics - regressed_metrics - improved_metrics

        # Load history for trend analysis
        history = self.load_history()
        history.append(asdict(current))
        self.save_history(history)

        trend_analysis = self.calculate_trend_analysis(history)

        # Generate summary
        if regressed_metrics == 0:
            summary = "No regressions detected. System performance is stable or improving."
        elif regressed_metrics <= 2:
            summary = f"Minor regressions detected in {regressed_metrics} metrics. Review recommended."
        else:
            summary = f"Significant regressions detected in {regressed_metrics} metrics. Immediate action required."

        return RegressionReport(
            baseline_timestamp=baseline.timestamp,
            current_timestamp=current.timestamp,
            duration_hours=duration_hours,
            total_metrics=total_metrics,
            regressed_metrics=regressed_metrics,
            improved_metrics=improved_metrics,
            stable_metrics=stable_metrics,
            alerts=alerts,
            summary=summary,
            trend_analysis=trend_analysis,
        )

    def load_history(self) -> List[Dict[str, Any]]:
        """Load regression history."""
        if not self.history_path.exists():
            return []

        with open(self.history_path, 'r') as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        """Save regression history."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        # Keep only last 30 entries
        if len(history) > 30:
            history = history[-30:]

        with open(self.history_path, 'w') as f:
            json.dump(history, f, indent=2)

    def save_report(self, report: RegressionReport, path: Optional[Path] = None) -> None:
        """Save regression report to file."""
        if path is None:
            path = self.history_path.parent / f"regression_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(report)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def check_regression_threshold(self, report: RegressionReport) -> bool:
        """Check if regression report exceeds action threshold."""
        # Fail if any critical regressions
        critical_alerts = [a for a in report.alerts if a.severity == "critical"]
        if critical_alerts:
            return True

        # Fail if more than 3 warnings
        warning_alerts = [a for a in report.alerts if a.severity == "warning"]
        if len(warning_alerts) > 3:
            return True

        return False


def main():
    """Run regression testing."""
    print("Running V5 Performance Regression Test...")
    print("=" * 60)

    tester = V5RegressionTester()

    try:
        report = tester.generate_regression_report()

        print(f"\nBaseline: {report.baseline_timestamp}")
        print(f"Current: {report.current_timestamp}")
        print(f"Duration: {report.duration_hours:.2f} hours")

        print(f"\nSummary: {report.summary}")

        print(f"\nMetrics:")
        print(f"  Total: {report.total_metrics}")
        print(f"  Regressed: {report.regressed_metrics}")
        print(f"  Improved: {report.improved_metrics}")
        print(f"  Stable: {report.stable_metrics}")

        if report.alerts:
            print(f"\nRegression Alerts:")
            for alert in report.alerts:
                print(f"  [{alert.severity.upper()}] {alert.metric_name}")
                print(f"    Baseline: {alert.baseline_value:.2f}")
                print(f"    Current: {alert.current_value:.2f}")
                print(f"    Degradation: {alert.degradation_percent:.1f}% (threshold: {alert.threshold_percent}%)")
        else:
            print(f"\nNo regression alerts!")

        if report.trend_analysis.get("status") != "insufficient_data":
            print(f"\nTrend Analysis:")
            for metric, trend in report.trend_analysis.items():
                if metric != "status":
                    print(f"  {metric}: {trend['trend']} ({trend['change_percent']:.1f}%)")

        # Save report
        tester.save_report(report)
        print(f"\nReport saved")

        # Check threshold
        if tester.check_regression_threshold(report):
            print("\n⚠️  REGRESSION THRESHOLD EXCEEDED - ACTION REQUIRED")
            return 1
        else:
            print("\n✓ Regression test passed")
            return 0

    except ValueError as e:
        print(f"\nError: {e}")
        print("Run baseline generation first: python -m performance.v5_baseline")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
