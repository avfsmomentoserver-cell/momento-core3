"""Performance metrics collection and analysis.

Provides tools for collecting, storing, and analyzing performance metrics
to establish baselines and track improvements over time.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class PerformanceMetric:
    """Single performance metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of performance metrics."""
    name: str
    unit: str
    metrics: List[PerformanceMetric]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a metric to the series."""
        self.metrics.append(PerformanceMetric(
            name=self.name,
            value=value,
            unit=self.unit,
            metadata=metadata or {},
        ))

    def get_statistics(self) -> Dict[str, float]:
        """Calculate statistics for the metric series."""
        if not self.metrics:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "stddev": 0,
                "p25": 0,
                "p75": 0,
                "p95": 0,
                "p99": 0,
            }

        values = [m.value for m in self.metrics]
        sorted_values = sorted(values)
        n = len(sorted_values)

        def percentile(p: float) -> float:
            idx = min(n - 1, int(round(p / 100 * (n - 1))))
            return sorted_values[idx]

        return {
            "count": n,
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if n > 1 else 0,
            "p25": percentile(25),
            "p75": percentile(75),
            "p95": percentile(95),
            "p99": percentile(99),
        }


@dataclass
class BaselineReport:
    """Complete performance baseline report."""
    system_info: Dict[str, Any]
    database_metrics: Dict[str, Any]
    api_metrics: Dict[str, Any]
    analysis_metrics: Dict[str, Any]
    websocket_metrics: Dict[str, Any]
    memory_metrics: Dict[str, Any]
    network_metrics: Dict[str, Any]
    overall_assessment: Dict[str, Any]
    v5_target_comparison: Dict[str, Any]
    recommendations: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class PerformanceMetrics:
    """Performance metrics collection and analysis."""

    def __init__(self, storage_path: Optional[Path] = None):
        self._series: Dict[str, MetricSeries] = {}
        self.storage_path = storage_path or Path(__file__).parent.parent / "data" / "performance_metrics.json"

    def create_series(self, name: str, unit: str, metadata: Optional[Dict[str, Any]] = None) -> MetricSeries:
        """Create a new metric series."""
        series = MetricSeries(name=name, unit=unit, metadata=metadata or {})
        self._series[name] = series
        return series

    def get_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series by name."""
        return self._series.get(name)

    def record_metric(self, name: str, value: float, unit: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a single metric."""
        if name not in self._series:
            self.create_series(name, unit, metadata)
        self._series[name].add(value, metadata)

    def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metric series."""
        return {name: series.get_statistics() for name, series in self._series.items()}

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """Save metrics to file."""
        path = path or self.storage_path
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            name: {
                "name": series.name,
                "unit": series.unit,
                "metadata": series.metadata,
                "metrics": [asdict(m) for m in series.metrics],
            }
            for name, series in self._series.items()
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, path: Optional[Path] = None) -> None:
        """Load metrics from file."""
        path = path or self.storage_path
        if not path.exists():
            return

        with open(path, 'r') as f:
            data = json.load(f)

        for name, series_data in data.items():
            series = MetricSeries(
                name=series_data["name"],
                unit=series_data["unit"],
                metadata=series_data["metadata"],
                metrics=[PerformanceMetric(**m) for m in series_data["metrics"]],
            )
            self._series[name] = series

    def compare_with_baseline(self, baseline_path: Path) -> Dict[str, Any]:
        """Compare current metrics with a baseline."""
        baseline = PerformanceMetrics(storage_path=baseline_path)
        baseline.load_from_file()

        comparison = {}
        for name, current_series in self._series.items():
            baseline_series = baseline.get_series(name)
            if baseline_series:
                current_stats = current_series.get_statistics()
                baseline_stats = baseline_series.get_statistics()

                comparison[name] = {
                    "current_mean": current_stats["mean"],
                    "baseline_mean": baseline_stats["mean"],
                    "change_percent": ((current_stats["mean"] - baseline_stats["mean"]) / baseline_stats["mean"] * 100)
                    if baseline_stats["mean"] > 0 else 0,
                    "improvement": current_stats["mean"] < baseline_stats["mean"],
                }

        return comparison


class BaselineGenerator:
    """Generate comprehensive performance baseline reports."""

    def __init__(self):
        self.metrics = PerformanceMetrics()

    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information."""
        import platform
        import os

        try:
            import psutil
            cpu_count = psutil.cpu_count()
            memory_total = psutil.virtual_memory().total / 1024 / 1024 / 1024  # GB
        except ImportError:
            cpu_count = os.cpu_count() or 1
            memory_total = 0

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": cpu_count,
            "memory_gb": memory_total,
            "hostname": platform.node(),
        }

    def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database performance metrics."""
        from momento import db, store

        metrics = {}

        # Test insert performance
        import time
        test_rounds = [
            {
                "source": "baseline",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(10)
        ]

        start = time.perf_counter()
        try:
            store.insert_rounds(test_rounds, method="baseline")
            insert_duration = (time.perf_counter() - start) * 1000
        except Exception:
            insert_duration = 0

        # Test select performance
        start = time.perf_counter()
        try:
            store.get_rounds("baseline", limit=100)
            select_duration = (time.perf_counter() - start) * 1000
        except Exception:
            select_duration = 0

        metrics["insert_latency_ms"] = insert_duration
        metrics["select_latency_ms"] = select_duration
        metrics["insert_throughput"] = len(test_rounds) / (insert_duration / 1000) if insert_duration > 0 else 0

        return metrics

    def collect_analysis_metrics(self) -> Dict[str, Any]:
        """Collect analysis engine performance metrics."""
        from momento import analysis, store

        metrics = {}

        test_rounds = [
            {
                "source": "baseline",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(500)
        ]

        import time
        start = time.perf_counter()
        try:
            analysis.analyze(test_rounds, store.analysis_settings())
            analysis_duration = (time.perf_counter() - start) * 1000
        except Exception:
            analysis_duration = 0

        metrics["analysis_latency_ms"] = analysis_duration
        metrics["analysis_throughput"] = 1 / (analysis_duration / 1000) if analysis_duration > 0 else 0

        return metrics

    def collect_memory_metrics(self) -> Dict[str, Any]:
        """Collect memory usage metrics."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }
        except ImportError:
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0}

    def generate_baseline_report(self) -> BaselineReport:
        """Generate comprehensive baseline report."""
        print("Collecting system information...")
        system_info = self.collect_system_info()

        print("Collecting database metrics...")
        database_metrics = self.collect_database_metrics()

        print("Collecting analysis metrics...")
        analysis_metrics = self.collect_analysis_metrics()

        print("Collecting memory metrics...")
        memory_metrics = self.collect_memory_metrics()

        # V5 target comparison
        v5_targets = {
            "latency_ms": 1.0,  # sub-millisecond
            "throughput_events_per_sec": 500000,
            "availability_percent": 99.99,
            "concurrent_users": 10000,
        }

        current_metrics = {
            "latency_ms": database_metrics.get("select_latency_ms", 0),
            "throughput_events_per_sec": database_metrics.get("insert_throughput", 0),
            "availability_percent": 99.9,  # Assumed baseline
            "concurrent_users": 100,  # Assumed baseline
        }

        target_comparison = {
            "latency_gap": current_metrics["latency_ms"] / v5_targets["latency_ms"] if v5_targets["latency_ms"] > 0 else 0,
            "throughput_gap": v5_targets["throughput_events_per_sec"] / current_metrics["throughput_events_per_sec"]
            if current_metrics["throughput_events_per_sec"] > 0 else 0,
            "users_gap": v5_targets["concurrent_users"] / current_metrics["concurrent_users"],
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(database_metrics, analysis_metrics, target_comparison)

        # Overall assessment
        overall_assessment = {
            "performance_tier": self._calculate_performance_tier(target_comparison),
            "critical_gaps": [k for k, v in target_comparison.items() if v > 100],
            "readiness_score": self._calculate_readiness_score(target_comparison),
        }

        return BaselineReport(
            system_info=system_info,
            database_metrics=database_metrics,
            api_metrics={},  # Will be populated by API benchmarks
            analysis_metrics=analysis_metrics,
            websocket_metrics={},  # Will be populated by WebSocket benchmarks
            memory_metrics=memory_metrics,
            network_metrics={},  # Will be populated by network analysis
            overall_assessment=overall_assessment,
            v5_target_comparison=target_comparison,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        database_metrics: Dict[str, Any],
        analysis_metrics: Dict[str, Any],
        target_comparison: Dict[str, Any],
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if database_metrics.get("insert_latency_ms", 0) > 10:
            recommendations.append(
                f"Database insert latency ({database_metrics['insert_latency_ms']:.2f}ms) exceeds 10ms. "
                "Consider batch inserts, connection pooling, and query optimization."
            )

        if database_metrics.get("select_latency_ms", 0) > 5:
            recommendations.append(
                f"Database select latency ({database_metrics['select_latency_ms']:.2f}ms) exceeds 5ms. "
                "Consider indexing, query optimization, and read replicas."
            )

        if analysis_metrics.get("analysis_latency_ms", 0) > 100:
            recommendations.append(
                f"Analysis latency ({analysis_metrics['analysis_latency_ms']:.2f}ms) exceeds 100ms. "
                "Consider memoization, caching, and algorithm optimization."
            )

        if target_comparison.get("latency_gap", 0) > 100:
            recommendations.append(
                f"Latency gap ({target_comparison['latency_gap']:.1f}x) requires DPDK, FPGA acceleration, "
                "and lock-free architectures for V5 targets."
            )

        if target_comparison.get("throughput_gap", 0) > 10:
            recommendations.append(
                f"Throughput gap ({target_comparison['throughput_gap']:.1f}x) requires horizontal scaling, "
                "GPU acceleration, and async optimization for V5 targets."
            )

        return recommendations

    def _calculate_performance_tier(self, target_comparison: Dict[str, Any]) -> str:
        """Calculate overall performance tier."""
        if any(v > 1000 for v in target_comparison.values()):
            return "tier_4_basic"
        elif any(v > 100 for v in target_comparison.values()):
            return "tier_3_standard"
        elif any(v > 10 for v in target_comparison.values()):
            return "tier_2_optimized"
        else:
            return "tier_1_high_performance"

    def _calculate_readiness_score(self, target_comparison: Dict[str, Any]) -> float:
        """Calculate V5 readiness score (0-100)."""
        scores = []
        for gap in target_comparison.values():
            if gap <= 1:
                scores.append(100)
            elif gap <= 10:
                scores.append(50)
            elif gap <= 100:
                scores.append(25)
            else:
                scores.append(0)

        return statistics.mean(scores) if scores else 0

    def save_report(self, report: BaselineReport, path: Optional[Path] = None) -> None:
        """Save baseline report to file."""
        path = path or Path(__file__).parent.parent / "data" / "performance_baseline.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)

        print(f"Baseline report saved to: {path}")

    def print_report(self, report: BaselineReport) -> None:
        """Print baseline report."""
        print("\n" + "=" * 80)
        print("V4 PERFORMANCE BASELINE REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print()

        print("SYSTEM INFORMATION")
        print("-" * 80)
        for key, value in report.system_info.items():
            print(f"{key}: {value}")
        print()

        print("DATABASE METRICS")
        print("-" * 80)
        for key, value in report.database_metrics.items():
            print(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")
        print()

        print("ANALYSIS METRICS")
        print("-" * 80)
        for key, value in report.analysis_metrics.items():
            print(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")
        print()

        print("MEMORY METRICS")
        print("-" * 80)
        for key, value in report.memory_metrics.items():
            print(f"{key}: {value:.2f}" if isinstance(value, float) else f"{key}: {value}")
        print()

        print("V5 TARGET COMPARISON")
        print("-" * 80)
        for key, value in report.v5_target_comparison.items():
            print(f"{key}: {value:.2f}x")
        print()

        print("OVERALL ASSESSMENT")
        print("-" * 80)
        print(f"Performance Tier: {report.overall_assessment['performance_tier']}")
        print(f"Readiness Score: {report.overall_assessment['readiness_score']:.1f}/100")
        print(f"Critical Gaps: {', '.join(report.overall_assessment['critical_gaps'])}")
        print()

        print("RECOMMENDATIONS")
        print("-" * 80)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        print("=" * 80)


if __name__ == "__main__":
    generator = BaselineGenerator()
    report = generator.generate_baseline_report()
    generator.print_report(report)
    generator.save_report(report)
