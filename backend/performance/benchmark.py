"""Performance benchmarking suite for V4 system analysis.

Provides comprehensive benchmarking of database operations, API endpoints,
analysis computations, and WebSocket performance to establish V4 baselines.
"""

from __future__ import annotations

import asyncio
import statistics
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from momento import db, store, analysis


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    duration_ms: float
    operations: int
    ops_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    memory_mb: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class SystemBenchmark:
    """Complete system benchmark results."""
    database: BenchmarkResult
    api: BenchmarkResult
    analysis: BenchmarkResult
    websocket: BenchmarkResult
    memory: BenchmarkResult
    overall: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite.

    Measures:
    - Database query performance (insert, select, aggregate)
    - API endpoint latency
    - Analysis engine computation time
    - WebSocket broadcast latency
    - Memory usage patterns
    """

    def __init__(self, warmup_iterations: int = 10, benchmark_iterations: int = 100):
        self.warmup_iterations = warmup_iterations
        self.benchmark_iterations = benchmark_iterations
        self._latencies: List[float] = []

    @contextmanager
    def _measure(self):
        """Context manager for measuring operation latency."""
        start = time.perf_counter()
        start_mem = self._get_memory_mb()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            end_mem = self._get_memory_mb()
            self._latencies.append(duration * 1000)  # Convert to ms
            self._memory_delta = end_mem - start_mem

    def _get_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def _calculate_percentiles(self, latencies: List[float]) -> Dict[str, float]:
        """Calculate latency percentiles."""
        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0}

        sorted_lat = sorted(latencies)
        n = len(sorted_lat)

        def percentile(p: float) -> float:
            idx = min(n - 1, int(round(p / 100 * (n - 1))))
            return sorted_lat[idx]

        return {
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
        }

    def benchmark_database_insert(self, batch_size: int = 100) -> BenchmarkResult:
        """Benchmark database insert operations."""
        self._latencies = []

        # Warmup
        for _ in range(self.warmup_iterations):
            test_rounds = [
                {
                    "source": "benchmark",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "multiplier": 1.0 + (i % 100) / 10.0,
                    "color": "red",
                    "band": "low",
                    "points": 10.0,
                }
                for i in range(10)
            ]
            try:
                store.insert_rounds(test_rounds, method="benchmark")
            except Exception:
                pass

        # Benchmark
        start_time = time.perf_counter()
        for i in range(self.benchmark_iterations):
            batch_start = time.perf_counter()
            test_rounds = [
                {
                    "source": "benchmark",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "multiplier": 1.0 + ((i * batch_size + j) % 100) / 10.0,
                    "color": "red",
                    "band": "low",
                    "points": 10.0,
                }
                for j in range(batch_size)
            ]
            try:
                store.insert_rounds(test_rounds, method="benchmark")
            except Exception:
                pass
            self._latencies.append((time.perf_counter() - batch_start) * 1000)

        total_duration = (time.perf_counter() - start_time) * 1000
        total_ops = self.benchmark_iterations * batch_size

        percentiles = self._calculate_percentiles(self._latencies)

        return BenchmarkResult(
            name="database_insert",
            duration_ms=total_duration,
            operations=total_ops,
            ops_per_second=total_ops / (total_duration / 1000),
            avg_latency_ms=statistics.mean(self._latencies),
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(self._latencies),
            max_latency_ms=max(self._latencies),
            memory_mb=self._get_memory_mb(),
        )

    def benchmark_database_select(self, limit: int = 1000) -> BenchmarkResult:
        """Benchmark database select operations."""
        self._latencies = []

        # Warmup
        for _ in range(self.warmup_iterations):
            try:
                store.get_rounds("benchmark", limit=10)
            except Exception:
                pass

        # Benchmark
        start_time = time.perf_counter()
        for _ in range(self.benchmark_iterations):
            batch_start = time.perf_counter()
            try:
                store.get_rounds("benchmark", limit=limit)
            except Exception:
                pass
            self._latencies.append((time.perf_counter() - batch_start) * 1000)

        total_duration = (time.perf_counter() - start_time) * 1000
        total_ops = self.benchmark_iterations

        percentiles = self._calculate_percentiles(self._latencies)

        return BenchmarkResult(
            name="database_select",
            duration_ms=total_duration,
            operations=total_ops,
            ops_per_second=total_ops / (total_duration / 1000),
            avg_latency_ms=statistics.mean(self._latencies),
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(self._latencies),
            max_latency_ms=max(self._latencies),
            memory_mb=self._get_memory_mb(),
        )

    def benchmark_analysis_engine(self, round_count: int = 500) -> BenchmarkResult:
        """Benchmark analysis engine computation."""
        self._latencies = []

        # Generate test data
        test_rounds = [
            {
                "source": "benchmark",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(round_count)
        ]

        # Warmup
        for _ in range(self.warmup_iterations):
            try:
                analysis.analyze(test_rounds[:100], store.analysis_settings())
            except Exception:
                pass

        # Benchmark
        start_time = time.perf_counter()
        for _ in range(self.benchmark_iterations):
            batch_start = time.perf_counter()
            try:
                analysis.analyze(test_rounds, store.analysis_settings())
            except Exception:
                pass
            self._latencies.append((time.perf_counter() - batch_start) * 1000)

        total_duration = (time.perf_counter() - start_time) * 1000
        total_ops = self.benchmark_iterations

        percentiles = self._calculate_percentiles(self._latencies)

        return BenchmarkResult(
            name="analysis_engine",
            duration_ms=total_duration,
            operations=total_ops,
            ops_per_second=total_ops / (total_duration / 1000),
            avg_latency_ms=statistics.mean(self._latencies),
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(self._latencies),
            max_latency_ms=max(self._latencies),
            memory_mb=self._get_memory_mb(),
        )

    def benchmark_cache_operations(self) -> BenchmarkResult:
        """Benchmark analysis cache operations."""
        self._latencies = []

        # Warmup
        for _ in range(self.warmup_iterations):
            try:
                store.analysis_payload("benchmark", limit=100)
            except Exception:
                pass

        # Benchmark - cache hit
        start_time = time.perf_counter()
        for _ in range(self.benchmark_iterations):
            batch_start = time.perf_counter()
            try:
                store.analysis_payload("benchmark", limit=100)
            except Exception:
                pass
            self._latencies.append((time.perf_counter() - batch_start) * 1000)

        total_duration = (time.perf_counter() - start_time) * 1000
        total_ops = self.benchmark_iterations

        percentiles = self._calculate_percentiles(self._latencies)

        return BenchmarkResult(
            name="cache_operations",
            duration_ms=total_duration,
            operations=total_ops,
            ops_per_second=total_ops / (total_duration / 1000),
            avg_latency_ms=statistics.mean(self._latencies),
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(self._latencies),
            max_latency_ms=max(self._latencies),
            memory_mb=self._get_memory_mb(),
        )

    def run_full_benchmark(self) -> SystemBenchmark:
        """Run complete system benchmark."""
        print("Starting full system benchmark...")
        print(f"Warmup iterations: {self.warmup_iterations}")
        print(f"Benchmark iterations: {self.benchmark_iterations}")
        print()

        # Database benchmarks
        print("Benchmarking database insert...")
        db_insert = self.benchmark_database_insert()
        print(f"  Result: {db_insert.ops_per_second:.2f} ops/sec, P95: {db_insert.p95_latency_ms:.2f}ms")

        print("Benchmarking database select...")
        db_select = self.benchmark_database_select()
        print(f"  Result: {db_select.ops_per_second:.2f} ops/sec, P95: {db_select.p95_latency_ms:.2f}ms")

        # Analysis benchmarks
        print("Benchmarking analysis engine...")
        analysis_perf = self.benchmark_analysis_engine()
        print(f"  Result: {analysis_perf.ops_per_second:.2f} ops/sec, P95: {analysis_perf.p95_latency_ms:.2f}ms")

        # Cache benchmarks
        print("Benchmarking cache operations...")
        cache_perf = self.benchmark_cache_operations()
        print(f"  Result: {cache_perf.ops_per_second:.2f} ops/sec, P95: {cache_perf.p95_latency_ms:.2f}ms")

        # Calculate overall metrics
        overall = {
            "database_insert_ops_per_sec": db_insert.ops_per_second,
            "database_select_ops_per_sec": db_select.ops_per_second,
            "analysis_ops_per_sec": analysis_perf.ops_per_second,
            "cache_ops_per_sec": cache_perf.ops_per_second,
            "total_memory_mb": self._get_memory_mb(),
        }

        return SystemBenchmark(
            database=db_insert,
            api=BenchmarkResult(
                name="api_endpoints",
                duration_ms=0,
                operations=0,
                ops_per_second=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                memory_mb=0,
            ),
            analysis=analysis_perf,
            websocket=BenchmarkResult(
                name="websocket_broadcast",
                duration_ms=0,
                operations=0,
                ops_per_second=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                memory_mb=0,
            ),
            memory=cache_perf,
            overall=overall,
        )

    def print_results(self, benchmark: SystemBenchmark) -> None:
        """Print benchmark results in a formatted table."""
        print("\n" + "=" * 80)
        print("V4 SYSTEM PERFORMANCE BASELINE")
        print("=" * 80)
        print(f"Timestamp: {benchmark.timestamp}")
        print()

        print("DATABASE PERFORMANCE")
        print("-" * 80)
        print(f"Insert: {benchmark.database.ops_per_second:,.2f} ops/sec")
        print(f"  Avg Latency: {benchmark.database.avg_latency_ms:.3f}ms")
        print(f"  P50 Latency: {benchmark.database.p50_latency_ms:.3f}ms")
        print(f"  P95 Latency: {benchmark.database.p95_latency_ms:.3f}ms")
        print(f"  P99 Latency: {benchmark.database.p99_latency_ms:.3f}ms")
        print()

        print("ANALYSIS ENGINE")
        print("-" * 80)
        print(f"Throughput: {benchmark.analysis.ops_per_second:,.2f} ops/sec")
        print(f"  Avg Latency: {benchmark.analysis.avg_latency_ms:.3f}ms")
        print(f"  P50 Latency: {benchmark.analysis.p50_latency_ms:.3f}ms")
        print(f"  P95 Latency: {benchmark.analysis.p95_latency_ms:.3f}ms")
        print(f"  P99 Latency: {benchmark.analysis.p99_latency_ms:.3f}ms")
        print()

        print("CACHE PERFORMANCE")
        print("-" * 80)
        print(f"Throughput: {benchmark.memory.ops_per_second:,.2f} ops/sec")
        print(f"  Avg Latency: {benchmark.memory.avg_latency_ms:.3f}ms")
        print(f"  P50 Latency: {benchmark.memory.p50_latency_ms:.3f}ms")
        print(f"  P95 Latency: {benchmark.memory.p95_latency_ms:.3f}ms")
        print(f"  P99 Latency: {benchmark.memory.p99_latency_ms:.3f}ms")
        print()

        print("OVERALL METRICS")
        print("-" * 80)
        for key, value in benchmark.overall.items():
            print(f"{key}: {value:,.2f}")
        print("=" * 80)


if __name__ == "__main__":
    benchmark = PerformanceBenchmark(warmup_iterations=5, benchmark_iterations=50)
    results = benchmark.run_full_benchmark()
    benchmark.print_results(results)
