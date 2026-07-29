"""Load testing suite for stress testing and capacity planning.

Simulates high-load scenarios to validate system capacity and identify
performance degradation under stress.
"""

from __future__ import annotations

import asyncio
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from momento import db, store, analysis


@dataclass
class LoadTestResult:
    """Result of a load test."""
    test_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    error_rate: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class CapacityPlan:
    """Capacity planning recommendations."""
    current_capacity: Dict[str, Any]
    v5_requirements: Dict[str, Any]
    gap_analysis: Dict[str, Any]
    recommendations: List[str]
    infrastructure_needs: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class LoadTestRunner:
    """Load testing for stress testing and capacity planning."""

    def __init__(self):
        self._results: List[LoadTestResult] = []

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

    def test_database_concurrent_inserts(
        self,
        concurrent_users: int = 10,
        requests_per_user: int = 100,
        batch_size: int = 10,
    ) -> LoadTestResult:
        """Test concurrent database insert operations."""
        latencies = []
        successful = 0
        failed = 0

        def insert_batch(user_id: int) -> tuple[int, int, List[float]]:
            user_latencies = []
            user_successful = 0
            user_failed = 0

            for i in range(requests_per_user):
                start = time.perf_counter()
                try:
                    test_rounds = [
                        {
                            "source": f"loadtest_user{user_id}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "multiplier": 1.0 + ((user_id * requests_per_user + i) % 100) / 10.0,
                            "color": "red",
                            "band": "low",
                            "points": 10.0,
                        }
                        for j in range(batch_size)
                    ]
                    store.insert_rounds(test_rounds, method="loadtest")
                    user_successful += 1
                except Exception as e:
                    user_failed += 1
                finally:
                    user_latencies.append((time.perf_counter() - start) * 1000)

            return user_successful, user_failed, user_latencies

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(insert_batch, user_id) for user_id in range(concurrent_users)]
            for future in as_completed(futures):
                user_successful, user_failed, user_latencies = future.result()
                successful += user_successful
                failed += user_failed
                latencies.extend(user_latencies)

        duration = time.perf_counter() - start_time
        total_requests = concurrent_users * requests_per_user

        percentiles = self._calculate_percentiles(latencies)

        result = LoadTestResult(
            test_name="database_concurrent_inserts",
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            duration_seconds=duration,
            requests_per_second=total_requests / duration,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            error_rate=failed / total_requests if total_requests > 0 else 0,
        )

        self._results.append(result)
        return result

    def test_database_concurrent_reads(
        self,
        concurrent_users: int = 10,
        requests_per_user: int = 100,
        limit: int = 100,
    ) -> LoadTestResult:
        """Test concurrent database read operations."""
        latencies = []
        successful = 0
        failed = 0

        def read_batch(user_id: int) -> tuple[int, int, List[float]]:
            user_latencies = []
            user_successful = 0
            user_failed = 0

            for _ in range(requests_per_user):
                start = time.perf_counter()
                try:
                    store.get_rounds(f"loadtest_user{user_id}", limit=limit)
                    user_successful += 1
                except Exception:
                    user_failed += 1
                finally:
                    user_latencies.append((time.perf_counter() - start) * 1000)

            return user_successful, user_failed, user_latencies

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(read_batch, user_id) for user_id in range(concurrent_users)]
            for future in as_completed(futures):
                user_successful, user_failed, user_latencies = future.result()
                successful += user_successful
                failed += user_failed
                latencies.extend(user_latencies)

        duration = time.perf_counter() - start_time
        total_requests = concurrent_users * requests_per_user

        percentiles = self._calculate_percentiles(latencies)

        result = LoadTestResult(
            test_name="database_concurrent_reads",
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            duration_seconds=duration,
            requests_per_second=total_requests / duration,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            error_rate=failed / total_requests if total_requests > 0 else 0,
        )

        self._results.append(result)
        return result

    def test_analysis_concurrent_computations(
        self,
        concurrent_users: int = 10,
        requests_per_user: int = 50,
        round_count: int = 500,
    ) -> LoadTestResult:
        """Test concurrent analysis computations."""
        latencies = []
        successful = 0
        failed = 0

        # Pre-generate test data
        test_rounds = [
            {
                "source": "loadtest",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(round_count)
        ]

        def compute_analysis(user_id: int) -> tuple[int, int, List[float]]:
            user_latencies = []
            user_successful = 0
            user_failed = 0

            for _ in range(requests_per_user):
                start = time.perf_counter()
                try:
                    analysis.analyze(test_rounds, store.analysis_settings())
                    user_successful += 1
                except Exception:
                    user_failed += 1
                finally:
                    user_latencies.append((time.perf_counter() - start) * 1000)

            return user_successful, user_failed, user_latencies

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(compute_analysis, user_id) for user_id in range(concurrent_users)]
            for future in as_completed(futures):
                user_successful, user_failed, user_latencies = future.result()
                successful += user_successful
                failed += user_failed
                latencies.extend(user_latencies)

        duration = time.perf_counter() - start_time
        total_requests = concurrent_users * requests_per_user

        percentiles = self._calculate_percentiles(latencies)

        result = LoadTestResult(
            test_name="analysis_concurrent_computations",
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            duration_seconds=duration,
            requests_per_second=total_requests / duration,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            error_rate=failed / total_requests if total_requests > 0 else 0,
        )

        self._results.append(result)
        return result

    def test_cache_concurrent_access(
        self,
        concurrent_users: int = 10,
        requests_per_user: int = 100,
    ) -> LoadTestResult:
        """Test concurrent cache access."""
        latencies = []
        successful = 0
        failed = 0

        def access_cache(user_id: int) -> tuple[int, int, List[float]]:
            user_latencies = []
            user_successful = 0
            user_failed = 0

            for _ in range(requests_per_user):
                start = time.perf_counter()
                try:
                    store.analysis_payload(f"loadtest_user{user_id}", limit=100)
                    user_successful += 1
                except Exception:
                    user_failed += 1
                finally:
                    user_latencies.append((time.perf_counter() - start) * 1000)

            return user_successful, user_failed, user_latencies

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(access_cache, user_id) for user_id in range(concurrent_users)]
            for future in as_completed(futures):
                user_successful, user_failed, user_latencies = future.result()
                successful += user_successful
                failed += user_failed
                latencies.extend(user_latencies)

        duration = time.perf_counter() - start_time
        total_requests = concurrent_users * requests_per_user

        percentiles = self._calculate_percentiles(latencies)

        result = LoadTestResult(
            test_name="cache_concurrent_access",
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            duration_seconds=duration,
            requests_per_second=total_requests / duration,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=percentiles["p95"],
            p99_latency_ms=percentiles["p99"],
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            error_rate=failed / total_requests if total_requests > 0 else 0,
        )

        self._results.append(result)
        return result

    def run_scalability_test(self, max_users: int = 100, step: int = 10) -> List[LoadTestResult]:
        """Run scalability test with increasing concurrent users."""
        results = []

        for users in range(step, max_users + 1, step):
            print(f"Testing with {users} concurrent users...")
            result = self.test_database_concurrent_reads(
                concurrent_users=users,
                requests_per_user=10,
                limit=100,
            )
            results.append(result)
            print(f"  RPS: {result.requests_per_second:.2f}, P95: {result.p95_latency_ms:.2f}ms")

        return results

    def generate_capacity_plan(self) -> CapacityPlan:
        """Generate capacity plan based on load test results."""
        if not self._results:
            raise ValueError("No load test results available")

        # Calculate current capacity metrics
        avg_rps = statistics.mean([r.requests_per_second for r in self._results])
        avg_p95 = statistics.mean([r.p95_latency_ms for r in self._results])
        avg_error_rate = statistics.mean([r.error_rate for r in self._results])

        current_capacity = {
            "avg_requests_per_second": avg_rps,
            "avg_p95_latency_ms": avg_p95,
            "avg_error_rate": avg_error_rate,
            "max_concurrent_users": max([r.concurrent_users for r in self._results]),
        }

        # V5 requirements from specifications
        v5_requirements = {
            "target_events_per_second": 500000,
            "target_concurrent_users": 10000,
            "target_latency_ms": 1.0,  # sub-millisecond
            "target_availability": 99.99,
            "target_error_rate": 0.0001,  # 0.01%
        }

        # Gap analysis
        rps_gap = v5_requirements["target_events_per_second"] / avg_rps if avg_rps > 0 else float('inf')
        latency_gap = avg_p95 / v5_requirements["target_latency_ms"] if v5_requirements["target_latency_ms"] > 0 else float('inf')
        users_gap = v5_requirements["target_concurrent_users"] / current_capacity["max_concurrent_users"]

        gap_analysis = {
            "rps_multiplier_needed": rps_gap,
            "latency_reduction_needed": latency_gap,
            "users_multiplier_needed": users_gap,
            "error_rate_reduction_needed": avg_error_rate / v5_requirements["target_error_rate"] if avg_error_rate > 0 else 0,
        }

        # Generate recommendations
        recommendations = []
        infrastructure_needs = []

        if rps_gap > 10:
            recommendations.append(
                f"Critical: Current throughput ({avg_rps:.0f} RPS) is {rps_gap:.1f}x below V5 target. "
                "Requires horizontal scaling and async optimization."
            )
            infrastructure_needs.append("Kubernetes cluster with HPA for auto-scaling")
            infrastructure_needs.append("Load balancer with least-connections algorithm")
            infrastructure_needs.append("Redis cluster for caching layer")

        if latency_gap > 100:
            recommendations.append(
                f"Critical: Current latency ({avg_p95:.2f}ms) is {latency_gap:.1f}x above V5 target. "
                "Requires DPDK, FPGA acceleration, and lock-free architectures."
            )
            infrastructure_needs.append("DPDK kernel-bypass networking")
            infrastructure_needs.append("FPGA acceleration cards (Xilinx Alveo)")
            infrastructure_needs.append("GPU cluster for ML inference (NVIDIA A100/H100)")

        if users_gap > 100:
            recommendations.append(
                f"Critical: Current concurrency ({current_capacity['max_concurrent_users']}) is {users_gap:.1f}x below V5 target. "
                "Requires connection pooling and WebSocket optimization."
            )
            infrastructure_needs.append("WebSocket connection pooling")
            infrastructure_needs.append("Redis pub/sub for horizontal scaling")
            infrastructure_needs.append("CDN for static assets")

        return CapacityPlan(
            current_capacity=current_capacity,
            v5_requirements=v5_requirements,
            gap_analysis=gap_analysis,
            recommendations=recommendations,
            infrastructure_needs=infrastructure_needs,
        )

    def print_results(self) -> None:
        """Print load test results."""
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)

        for result in self._results:
            print(f"\n{result.test_name.upper()}")
            print("-" * 80)
            print(f"Concurrent Users: {result.concurrent_users}")
            print(f"Total Requests: {result.total_requests}")
            print(f"Successful: {result.successful_requests}")
            print(f"Failed: {result.failed_requests}")
            print(f"Duration: {result.duration_seconds:.2f}s")
            print(f"Requests/Second: {result.requests_per_second:.2f}")
            print(f"Error Rate: {result.error_rate * 100:.2f}%")
            print(f"Latency (ms):")
            print(f"  Avg: {result.avg_latency_ms:.3f}")
            print(f"  P50: {result.p50_latency_ms:.3f}")
            print(f"  P95: {result.p95_latency_ms:.3f}")
            print(f"  P99: {result.p99_latency_ms:.3f}")
            print(f"  Min: {result.min_latency_ms:.3f}")
            print(f"  Max: {result.max_latency_ms:.3f}")

        print("=" * 80)


if __name__ == "__main__":
    runner = LoadTestRunner()

    print("Running load tests...")
    print("\n1. Database concurrent inserts...")
    runner.test_database_concurrent_inserts(concurrent_users=5, requests_per_user=20, batch_size=10)

    print("\n2. Database concurrent reads...")
    runner.test_database_concurrent_reads(concurrent_users=10, requests_per_user=50, limit=100)

    print("\n3. Analysis concurrent computations...")
    runner.test_analysis_concurrent_computations(concurrent_users=5, requests_per_user=20, round_count=200)

    print("\n4. Cache concurrent access...")
    runner.test_cache_concurrent_access(concurrent_users=10, requests_per_user=50)

    runner.print_results()

    print("\nGenerating capacity plan...")
    capacity_plan = runner.generate_capacity_plan()
    print("\n" + "=" * 80)
    print("CAPACITY PLAN")
    print("=" * 80)
    print(f"Current RPS: {capacity_plan.current_capacity['avg_requests_per_second']:.2f}")
    print(f"Current P95 Latency: {capacity_plan.current_capacity['avg_p95_latency_ms']:.2f}ms")
    print(f"RPS Gap: {capacity_plan.gap_analysis['rps_multiplier_needed']:.1f}x")
    print(f"Latency Gap: {capacity_plan.gap_analysis['latency_reduction_needed']:.1f}x")
    print("\nRecommendations:")
    for rec in capacity_plan.recommendations:
        print(f"  - {rec}")
    print("\nInfrastructure Needs:")
    for need in capacity_plan.infrastructure_needs:
        print(f"  - {need}")
    print("=" * 80)
