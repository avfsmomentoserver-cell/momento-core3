"""V5 Real-time Performance Monitoring.

Provides real-time performance monitoring and alerting for V5 components.
Tracks metrics in production and detects anomalies.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from momento import db, store, analysis


@dataclass
class RealtimeMetric:
    """Real-time performance metric."""
    name: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricThreshold:
    """Threshold for metric alerting."""
    metric_name: str
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    window_seconds: int = 60
    consecutive_violations: int = 3
    severity: str = "warning"  # warning, critical


@dataclass
class PerformanceAlert:
    """Performance alert."""
    metric_name: str
    current_value: float
    threshold_value: float
    violation_type: str  # above_max, below_min
    severity: str
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class MonitoringReport:
    """Monitoring report."""
    start_time: str
    end_time: str
    duration_seconds: float
    metrics_collected: int
    alerts_triggered: int
    metric_statistics: Dict[str, Any]
    alerts: List[PerformanceAlert]
    system_health: str  # healthy, degraded, critical
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class RealtimeMetricsCollector:
    """Collect real-time performance metrics."""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    async def record_metric(self, metric: RealtimeMetric) -> None:
        """Record a metric."""
        async with self._lock:
            if metric.name not in self.metrics:
                self.metrics[metric.name] = deque(maxlen=self.window_size)
            self.metrics[metric.name].append(metric)

    async def get_metric_values(self, metric_name: str, limit: Optional[int] = None) -> List[float]:
        """Get recent metric values."""
        async with self._lock:
            if metric_name not in self.metrics:
                return []

            values = [m.value for m in self.metrics[metric_name]]
            if limit:
                values = values[-limit:]
            return values

    async def get_metric_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        values = await self.get_metric_values(metric_name)

        if not values:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "stddev": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }

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
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
        }

    async def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        async with self._lock:
            return {name: await self.get_metric_statistics(name) for name in self.metrics.keys()}


class V5PerformanceMonitor:
    """Real-time performance monitoring for V5 components."""

    # Default monitoring thresholds
    DEFAULT_THRESHOLDS = [
        MetricThreshold("db_insert_latency", max_value=10.0, window_seconds=60, severity="critical"),
        MetricThreshold("db_select_latency", max_value=5.0, window_seconds=60, severity="critical"),
        MetricThreshold("analysis_latency", max_value=200.0, window_seconds=60, severity="warning"),
        MetricThreshold("api_latency", max_value=100.0, window_seconds=60, severity="warning"),
        MetricThreshold("memory_usage_mb", max_value=4096.0, window_seconds=300, severity="critical"),
        MetricThreshold("cpu_usage_percent", max_value=80.0, window_seconds=60, severity="warning"),
    ]

    def __init__(
        self,
        collector: Optional[RealtimeMetricsCollector] = None,
        thresholds: Optional[List[MetricThreshold]] = None
    ):
        self.collector = collector or RealtimeMetricsCollector()
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self.alerts: List[PerformanceAlert] = []
        self._violation_counts: Dict[str, int] = {}
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add callback for alert notifications."""
        self._alert_callbacks.append(callback)

    async def check_thresholds(self) -> List[PerformanceAlert]:
        """Check all metrics against thresholds."""
        new_alerts = []

        for threshold in self.thresholds:
            values = await self.collector.get_metric_values(threshold.metric_name, limit=100)

            if not values:
                continue

            recent_value = values[-1]

            # Check max threshold
            if threshold.max_value is not None and recent_value > threshold.max_value:
                self._violation_counts[threshold.metric_name] = \
                    self._violation_counts.get(threshold.metric_name, 0) + 1

                if self._violation_counts[threshold.metric_name] >= threshold.consecutive_violations:
                    alert = PerformanceAlert(
                        metric_name=threshold.metric_name,
                        current_value=recent_value,
                        threshold_value=threshold.max_value,
                        violation_type="above_max",
                        severity=threshold.severity,
                        duration_seconds=threshold.window_seconds,
                    )
                    new_alerts.append(alert)
                    self.alerts.append(alert)

                    # Trigger callbacks
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert)
                        except Exception:
                            pass
            else:
                self._violation_counts[threshold.metric_name] = 0

            # Check min threshold
            if threshold.min_value is not None and recent_value < threshold.min_value:
                self._violation_counts[f"{threshold.metric_name}_min"] = \
                    self._violation_counts.get(f"{threshold.metric_name}_min", 0) + 1

                if self._violation_counts[f"{threshold.metric_name}_min"] >= threshold.consecutive_violations:
                    alert = PerformanceAlert(
                        metric_name=threshold.metric_name,
                        current_value=recent_value,
                        threshold_value=threshold.min_value,
                        violation_type="below_min",
                        severity=threshold.severity,
                        duration_seconds=threshold.window_seconds,
                    )
                    new_alerts.append(alert)
                    self.alerts.append(alert)

                    # Trigger callbacks
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert)
                        except Exception:
                            pass
            else:
                self._violation_counts[f"{threshold.metric_name}_min"] = 0

        return new_alerts

    async def monitor_database_operations(self, interval_seconds: float = 1.0) -> None:
        """Monitor database operations."""
        while True:
            try:
                # Measure insert latency
                test_rounds = [
                    {
                        "source": "monitoring",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "multiplier": 1.0 + (i % 100) / 10.0,
                        "color": "red",
                        "band": "low",
                        "points": 10.0,
                    }
                    for i in range(5)
                ]

                start = time.perf_counter()
                try:
                    store.insert_rounds(test_rounds, method="monitoring")
                    insert_latency = (time.perf_counter() - start) * 1000
                    await self.collector.record_metric(RealtimeMetric(
                        name="db_insert_latency",
                        value=insert_latency,
                        unit="ms",
                    ))
                except Exception:
                    pass

                # Measure select latency
                start = time.perf_counter()
                try:
                    store.get_rounds("monitoring", limit=50)
                    select_latency = (time.perf_counter() - start) * 1000
                    await self.collector.record_metric(RealtimeMetric(
                        name="db_select_latency",
                        value=select_latency,
                        unit="ms",
                    ))
                except Exception:
                    pass

            except Exception:
                pass

            await asyncio.sleep(interval_seconds)

    async def monitor_analysis_operations(self, interval_seconds: float = 5.0) -> None:
        """Monitor analysis operations."""
        while True:
            try:
                # Generate test data
                test_rounds = [
                    {
                        "source": "monitoring",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "multiplier": 1.0 + (i % 100) / 10.0,
                        "color": "red",
                        "band": "low",
                        "points": 10.0,
                    }
                    for i in range(500)
                ]

                start = time.perf_counter()
                try:
                    analysis.analyze(test_rounds, store.analysis_settings())
                    analysis_latency = (time.perf_counter() - start) * 1000
                    await self.collector.record_metric(RealtimeMetric(
                        name="analysis_latency",
                        value=analysis_latency,
                        unit="ms",
                    ))
                except Exception:
                    pass

            except Exception:
                pass

            await asyncio.sleep(interval_seconds)

    async def monitor_system_resources(self, interval_seconds: float = 5.0) -> None:
        """Monitor system resources."""
        while True:
            try:
                import psutil
                import os

                # Memory usage
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                await self.collector.record_metric(RealtimeMetric(
                    name="memory_usage_mb",
                    value=memory_mb,
                    unit="MB",
                ))

                # CPU usage
                cpu_percent = process.cpu_percent(interval=0.1)
                await self.collector.record_metric(RealtimeMetric(
                    name="cpu_usage_percent",
                    value=cpu_percent,
                    unit="percent",
                ))

            except Exception:
                pass

            await asyncio.sleep(interval_seconds)

    async def start_monitoring(self) -> None:
        """Start all monitoring tasks."""
        tasks = [
            asyncio.create_task(self.monitor_database_operations()),
            asyncio.create_task(self.monitor_analysis_operations()),
            asyncio.create_task(self.monitor_system_resources()),
            asyncio.create_task(self.check_thresholds_loop()),
        ]
        await asyncio.gather(*tasks)

    async def check_thresholds_loop(self, interval_seconds: float = 10.0) -> None:
        """Check thresholds periodically."""
        while True:
            try:
                await self.check_thresholds()
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)

    async def generate_report(self, duration_seconds: float = 60.0) -> MonitoringReport:
        """Generate monitoring report."""
        start_time = datetime.now(timezone.utc)

        # Wait for duration
        await asyncio.sleep(duration_seconds)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Get statistics
        statistics = await self.collector.get_all_statistics()

        # Count metrics
        metrics_collected = sum(len(m) for m in self.collector.metrics.values())

        # Determine system health
        critical_alerts = [a for a in self.alerts if a.severity == "critical"]
        warning_alerts = [a for a in self.alerts if a.severity == "warning"]

        if critical_alerts:
            system_health = "critical"
        elif warning_alerts:
            system_health = "degraded"
        else:
            system_health = "healthy"

        return MonitoringReport(
            start_time=start_time.isoformat(timespec="milliseconds"),
            end_time=end_time.isoformat(timespec="milliseconds"),
            duration_seconds=duration,
            metrics_collected=metrics_collected,
            alerts_triggered=len(self.alerts),
            metric_statistics=statistics,
            alerts=self.alerts.copy(),
            system_health=system_health,
        )

    def save_report(self, report: MonitoringReport, path: Optional[Path] = None) -> None:
        """Save monitoring report to file."""
        if path is None:
            path = Path(__file__).parent.parent / "data" / f"monitoring_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(report)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


async def monitor_duration(duration_seconds: float = 60.0) -> MonitoringReport:
    """Run monitoring for a specified duration."""
    print(f"Starting V5 Performance Monitoring for {duration_seconds} seconds...")
    print("=" * 60)

    monitor = V5PerformanceMonitor()

    # Add console alert callback
    def console_alert(alert: PerformanceAlert) -> None:
        print(f"\n[ALERT] {alert.severity.upper()}: {alert.metric_name}")
        print(f"  Current: {alert.current_value:.2f}")
        print(f"  Threshold: {alert.threshold_value:.2f}")
        print(f"  Type: {alert.violation_type}")

    monitor.add_alert_callback(console_alert)

    # Start monitoring tasks
    db_task = asyncio.create_task(monitor.monitor_database_operations())
    analysis_task = asyncio.create_task(monitor.monitor_analysis_operations())
    resource_task = asyncio.create_task(monitor.monitor_system_resources())
    threshold_task = asyncio.create_task(monitor.check_thresholds_loop())

    try:
        # Wait for duration
        await asyncio.sleep(duration_seconds)
    finally:
        # Cancel tasks
        db_task.cancel()
        analysis_task.cancel()
        resource_task.cancel()
        threshold_task.cancel()

    # Generate report
    report = await monitor.generate_report(0)  # Duration already elapsed

    print(f"\nMonitoring Report:")
    print(f"  Duration: {report.duration_seconds:.2f} seconds")
    print(f"  Metrics Collected: {report.metrics_collected}")
    print(f"  Alerts Triggered: {report.alerts_triggered}")
    print(f"  System Health: {report.system_health.upper()}")

    print(f"\nMetric Statistics:")
    for metric_name, stats in report.metric_statistics.items():
        print(f"  {metric_name}:")
        print(f"    Mean: {stats['mean']:.2f}")
        print(f"    P50: {stats['p50']:.2f}")
        print(f"    P95: {stats['p95']:.2f}")
        print(f"    P99: {stats['p99']:.2f}")

    if report.alerts:
        print(f"\nAlerts:")
        for alert in report.alerts:
            print(f"  [{alert.severity.upper()}] {alert.metric_name}: {alert.current_value:.2f}")

    # Save report
    monitor.save_report(report)
    print(f"\nReport saved")

    return report


def main():
    """Run monitoring."""
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    asyncio.run(monitor_duration(duration))


if __name__ == "__main__":
    main()
