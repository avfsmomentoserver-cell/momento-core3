"""V5 Performance Baseline Framework.

Establishes comprehensive performance baselines for the V5 transformation,
aligned with V5 tool specifications including CUDA, DPDK, FPGA, and
ultra-low latency requirements.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from momento import db, store, analysis


@dataclass
class V5PerformanceTarget:
    """V5 performance target based on specifications."""
    metric_name: str
    target_value: float
    unit: str
    tolerance_percent: float = 10.0
    description: str = ""
    category: str = "general"  # general, realtime, database, gpu, network


@dataclass
class V5BenchmarkResult:
    """Result of a V5 benchmark run."""
    metric_name: str
    measured_value: float
    target_value: float
    unit: str
    achieved: bool
    gap_percent: float
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class V5BaselineReport:
    """Complete V5 baseline report."""
    system_info: Dict[str, Any]
    benchmarks: List[V5BenchmarkResult]
    overall_score: float
    v5_readiness: str  # ready, partial, not_ready
    critical_gaps: List[str]
    recommendations: List[str]
    capacity_metrics: Dict[str, Any]
    scaling_projections: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class V5PerformanceTargets:
    """V5 performance targets based on specifications."""

    # Database targets (PostgreSQL 15+)
    DATABASE_TARGETS = [
        V5PerformanceTarget(
            metric_name="db_insert_latency_p50",
            target_value=1.0,
            unit="ms",
            tolerance_percent=20.0,
            description="Database insert P50 latency",
            category="database"
        ),
        V5PerformanceTarget(
            metric_name="db_insert_latency_p99",
            target_value=5.0,
            unit="ms",
            tolerance_percent=20.0,
            description="Database insert P99 latency",
            category="database"
        ),
        V5PerformanceTarget(
            metric_name="db_select_latency_p50",
            target_value=0.5,
            unit="ms",
            tolerance_percent=20.0,
            description="Database select P50 latency",
            category="database"
        ),
        V5PerformanceTarget(
            metric_name="db_throughput",
            target_value=10000,
            unit="ops/sec",
            tolerance_percent=15.0,
            description="Database operations per second",
            category="database"
        ),
    ]

    # Realtime targets (DPDK, FPGA)
    REALTIME_TARGETS = [
        V5PerformanceTarget(
            metric_name="packet_processing_latency",
            target_value=0.002,
            unit="ms",
            tolerance_percent=50.0,
            description="DPDK packet processing latency (<2μs)",
            category="realtime"
        ),
        V5PerformanceTarget(
            metric_name="fix_protocol_parse",
            target_value=0.014,
            unit="ms",
            tolerance_percent=50.0,
            description="FPGA FIX protocol parsing (14ns)",
            category="realtime"
        ),
        V5PerformanceTarget(
            metric_name="orderbook_update",
            target_value=0.004,
            unit="ms",
            tolerance_percent=50.0,
            description="FPGA orderbook update (4ns)",
            category="realtime"
        ),
        V5PerformanceTarget(
            metric_name="feature_extraction",
            target_value=0.05,
            unit="ms",
            tolerance_percent=50.0,
            description="FPGA feature extraction (50ns)",
            category="realtime"
        ),
    ]

    # GPU targets (CUDA, TensorRT)
    GPU_TARGETS = [
        V5PerformanceTarget(
            metric_name="inference_latency",
            target_value=1.0,
            unit="ms",
            tolerance_percent=50.0,
            description="TensorRT inference latency (<1ms)",
            category="gpu"
        ),
        V5PerformanceTarget(
            metric_name="inference_throughput",
            target_value=1000,
            unit="inferences/sec",
            tolerance_percent=20.0,
            description="TensorRT inference throughput",
            category="gpu"
        ),
        V5PerformanceTarget(
            metric_name="model_memory",
            target_value=2.0,
            unit="GB",
            tolerance_percent=50.0,
            description="Model memory footprint (<2GB)",
            category="gpu"
        ),
    ]

    # API targets (FastAPI, uvloop)
    API_TARGETS = [
        V5PerformanceTarget(
            metric_name="api_latency_p50",
            target_value=10.0,
            unit="ms",
            tolerance_percent=30.0,
            description="API endpoint P50 latency",
            category="general"
        ),
        V5PerformanceTarget(
            metric_name="api_latency_p99",
            target_value=50.0,
            unit="ms",
            tolerance_percent=30.0,
            description="API endpoint P99 latency",
            category="general"
        ),
        V5PerformanceTarget(
            metric_name="api_throughput",
            target_value=5000,
            unit="req/sec",
            tolerance_percent=20.0,
            description="API requests per second",
            category="general"
        ),
    ]

    # Analysis targets
    ANALYSIS_TARGETS = [
        V5PerformanceTarget(
            metric_name="analysis_latency_500_rounds",
            target_value=100.0,
            unit="ms",
            tolerance_percent=30.0,
            description="Analysis computation for 500 rounds",
            category="general"
        ),
        V5PerformanceTarget(
            metric_name="analysis_throughput",
            target_value=100,
            unit="analyses/sec",
            tolerance_percent=30.0,
            description="Analysis computations per second",
            category="general"
        ),
    ]

    @classmethod
    def all_targets(cls) -> List[V5PerformanceTarget]:
        """Get all V5 performance targets."""
        return (
            cls.DATABASE_TARGETS +
            cls.REALTIME_TARGETS +
            cls.GPU_TARGETS +
            cls.API_TARGETS +
            cls.ANALYSIS_TARGETS
        )

    @classmethod
    def get_targets_by_category(cls, category: str) -> List[V5PerformanceTarget]:
        """Get targets by category."""
        return [t for t in cls.all_targets() if t.category == category]


class V5BaselineRunner:
    """Run V5 performance benchmarks and generate baseline reports."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(__file__).parent.parent / "data" / "v5_baseline.json"
        self.results: List[V5BenchmarkResult] = []

    def collect_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information."""
        import platform
        import os

        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "cpu_count": os.cpu_count() or 1,
        }

        # Memory info
        try:
            import psutil
            info["memory_total_gb"] = psutil.virtual_memory().total / 1024 / 1024 / 1024
            info["memory_available_gb"] = psutil.virtual_memory().available / 1024 / 1024 / 1024
        except ImportError:
            info["memory_total_gb"] = 0
            info["memory_available_gb"] = 0

        # GPU info
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            info["gpu_count"] = device_count
            info["gpu_info"] = []
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                info["gpu_info"].append({
                    "device": i,
                    "name": name.decode() if isinstance(name, bytes) else name,
                    "memory_total_gb": memory.total / 1024 / 1024 / 1024,
                })
            pynvml.nvmlShutdown()
        except Exception:
            info["gpu_count"] = 0
            info["gpu_info"] = []

        # Network info
        try:
            import psutil
            interfaces = psutil.net_if_addrs()
            info["network_interfaces"] = list(interfaces.keys())
        except Exception:
            info["network_interfaces"] = []

        return info

    def benchmark_database_performance(self) -> List[V5BenchmarkResult]:
        """Benchmark database performance against V5 targets."""
        results = []
        targets = V5PerformanceTargets.DATABASE_TARGETS

        # Test insert performance
        insert_latencies = []
        for _ in range(100):
            test_rounds = [
                {
                    "source": "v5_baseline",
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
                store.insert_rounds(test_rounds, method="v5_baseline")
                insert_latencies.append((time.perf_counter() - start) * 1000)
            except Exception:
                pass

        if insert_latencies:
            sorted_lat = sorted(insert_latencies)
            n = len(sorted_lat)

            def percentile(p: float) -> float:
                idx = min(n - 1, int(round(p / 100 * (n - 1))))
                return sorted_lat[idx]

            p50 = percentile(50)
            p99 = percentile(99)

            # P50 insert latency
            target = next(t for t in targets if t.metric_name == "db_insert_latency_p50")
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=p50,
                target_value=target.target_value,
                unit=target.unit,
                achieved=p50 <= target.target_value * (1 + target.tolerance_percent / 100),
                gap_percent=((p50 - target.target_value) / target.target_value * 100),
                category=target.category,
                metadata={"n": n, "p99": p99}
            ))

            # P99 insert latency
            target = next(t for t in targets if t.metric_name == "db_insert_latency_p99")
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=p99,
                target_value=target.target_value,
                unit=target.unit,
                achieved=p99 <= target.target_value * (1 + target.tolerance_percent / 100),
                gap_percent=((p99 - target.target_value) / target.target_value * 100),
                category=target.category,
                metadata={"n": n, "p50": p50}
            ))

        # Test select performance
        select_latencies = []
        for _ in range(100):
            start = time.perf_counter()
            try:
                store.get_rounds("v5_baseline", limit=100)
                select_latencies.append((time.perf_counter() - start) * 1000)
            except Exception:
                pass

        if select_latencies:
            sorted_lat = sorted(select_latencies)
            n = len(sorted_lat)
            p50 = sorted_lat[min(n - 1, int(round(0.5 * (n - 1))))]

            target = next(t for t in targets if t.metric_name == "db_select_latency_p50")
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=p50,
                target_value=target.target_value,
                unit=target.unit,
                achieved=p50 <= target.target_value * (1 + target.tolerance_percent / 100),
                gap_percent=((p50 - target.target_value) / target.target_value * 100),
                category=target.category,
                metadata={"n": n}
            ))

        # Test throughput
        start = time.perf_counter()
        ops = 0
        for _ in range(100):
            try:
                store.get_rounds("v5_baseline", limit=10)
                ops += 1
            except Exception:
                pass
        duration = time.perf_counter() - start
        throughput = ops / duration if duration > 0 else 0

        target = next(t for t in targets if t.metric_name == "db_throughput")
        results.append(V5BenchmarkResult(
            metric_name=target.metric_name,
            measured_value=throughput,
            target_value=target.target_value,
            unit=target.unit,
            achieved=throughput >= target.target_value * (1 - target.tolerance_percent / 100),
            gap_percent=((throughput - target.target_value) / target.target_value * 100),
            category=target.category,
            metadata={"duration_sec": duration, "ops": ops}
        ))

        return results

    def benchmark_analysis_performance(self) -> List[V5BenchmarkResult]:
        """Benchmark analysis engine performance."""
        results = []
        targets = V5PerformanceTargets.ANALYSIS_TARGETS

        # Generate test data
        test_rounds = [
            {
                "source": "v5_baseline",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(500)
        ]

        # Test analysis latency
        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            try:
                analysis.analyze(test_rounds, store.analysis_settings())
                latencies.append((time.perf_counter() - start) * 1000)
            except Exception:
                pass

        if latencies:
            avg_latency = statistics.mean(latencies)

            target = next(t for t in targets if t.metric_name == "analysis_latency_500_rounds")
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=avg_latency,
                target_value=target.target_value,
                unit=target.unit,
                achieved=avg_latency <= target.target_value * (1 + target.tolerance_percent / 100),
                gap_percent=((avg_latency - target.target_value) / target.target_value * 100),
                category=target.category,
                metadata={"n": len(latencies), "min": min(latencies), "max": max(latencies)}
            ))

        # Test throughput
        start = time.perf_counter()
        count = 0
        for _ in range(20):
            try:
                analysis.analyze(test_rounds, store.analysis_settings())
                count += 1
            except Exception:
                pass
        duration = time.perf_counter() - start
        throughput = count / duration if duration > 0 else 0

        target = next(t for t in targets if t.metric_name == "analysis_throughput")
        results.append(V5BenchmarkResult(
            metric_name=target.metric_name,
            measured_value=throughput,
            target_value=target.target_value,
            unit=target.unit,
            achieved=throughput >= target.target_value * (1 - target.tolerance_percent / 100),
            gap_percent=((throughput - target.target_value) / target.target_value * 100),
            category=target.category,
            metadata={"duration_sec": duration, "count": count}
        ))

        return results

    def benchmark_api_performance(self) -> List[V5BenchmarkResult]:
        """Benchmark API performance (simulated)."""
        results = []
        targets = V5PerformanceTargets.API_TARGETS

        # Simulate API latency (actual testing would require running server)
        # This is a placeholder for actual API benchmarking
        simulated_p50 = 15.0  # ms
        simulated_p99 = 60.0  # ms
        simulated_throughput = 3000  # req/sec

        target = next(t for t in targets if t.metric_name == "api_latency_p50")
        results.append(V5BenchmarkResult(
            metric_name=target.metric_name,
            measured_value=simulated_p50,
            target_value=target.target_value,
            unit=target.unit,
            achieved=simulated_p50 <= target.target_value * (1 + target.tolerance_percent / 100),
            gap_percent=((simulated_p50 - target.target_value) / target.target_value * 100),
            category=target.category,
            metadata={"simulated": True}
        ))

        target = next(t for t in targets if t.metric_name == "api_latency_p99")
        results.append(V5BenchmarkResult(
            metric_name=target.metric_name,
            measured_value=simulated_p99,
            target_value=target.target_value,
            unit=target.unit,
            achieved=simulated_p99 <= target.target_value * (1 + target.tolerance_percent / 100),
            gap_percent=((simulated_p99 - target.target_value) / target.target_value * 100),
            category=target.category,
            metadata={"simulated": True}
        ))

        target = next(t for t in targets if t.metric_name == "api_throughput")
        results.append(V5BenchmarkResult(
            metric_name=target.metric_name,
            measured_value=simulated_throughput,
            target_value=target.target_value,
            unit=target.unit,
            achieved=simulated_throughput >= target.target_value * (1 - target.tolerance_percent / 100),
            gap_percent=((simulated_throughput - target.target_value) / target.target_value * 100),
            category=target.category,
            metadata={"simulated": True}
        ))

        return results

    def benchmark_realtime_hardware(self) -> List[V5BenchmarkResult]:
        """Benchmark realtime hardware (DPDK, FPGA)."""
        results = []
        targets = V5PerformanceTargets.REALTIME_TARGETS

        # These require actual hardware (DPDK, FPGA)
        # Placeholder results for when hardware is available
        for target in targets:
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=0.0,
                target_value=target.target_value,
                unit=target.unit,
                achieved=False,
                gap_percent=-100.0,
                category=target.category,
                metadata={"hardware_required": True, "status": "not_implemented"}
            ))

        return results

    def benchmark_gpu_performance(self) -> List[V5BenchmarkResult]:
        """Benchmark GPU performance (CUDA, TensorRT)."""
        results = []
        targets = V5PerformanceTargets.GPU_TARGETS

        # Check for GPU availability
        gpu_available = False
        try:
            import pynvml
            pynvml.nvmlInit()
            gpu_available = pynvml.nvmlDeviceGetCount() > 0
            pynvml.nvmlShutdown()
        except Exception:
            pass

        if not gpu_available:
            for target in targets:
                results.append(V5BenchmarkResult(
                    metric_name=target.metric_name,
                    measured_value=0.0,
                    target_value=target.target_value,
                    unit=target.unit,
                    achieved=False,
                    gap_percent=-100.0,
                    category=target.category,
                    metadata={"gpu_available": False, "status": "hardware_required"}
                ))
            return results

        # Placeholder for actual GPU benchmarking
        # Would use CUDA and TensorRT for real measurements
        for target in targets:
            results.append(V5BenchmarkResult(
                metric_name=target.metric_name,
                measured_value=0.0,
                target_value=target.target_value,
                unit=target.unit,
                achieved=False,
                gap_percent=-100.0,
                category=target.category,
                metadata={"gpu_available": True, "status": "not_implemented"}
            ))

        return results

    def calculate_capacity_metrics(self) -> Dict[str, Any]:
        """Calculate capacity planning metrics."""
        system_info = self.collect_system_info()

        # Calculate current capacity based on benchmarks
        db_throughput = next((r.measured_value for r in self.results if r.metric_name == "db_throughput"), 0)
        analysis_throughput = next((r.measured_value for r in self.results if r.metric_name == "analysis_throughput"), 0)

        return {
            "current_db_throughput": db_throughput,
            "current_analysis_throughput": analysis_throughput,
            "cpu_cores": system_info["cpu_count"],
            "memory_gb": system_info.get("memory_total_gb", 0),
            "gpu_count": system_info.get("gpu_count", 0),
            "max_concurrent_users": int(db_throughput / 10),  # Assume 10 req/sec per user
            "peak_load_headroom": 0.3,  # 30% headroom
        }

    def calculate_scaling_projections(self) -> Dict[str, Any]:
        """Calculate scaling projections for V5 requirements."""
        capacity = self.calculate_capacity_metrics()

        # V5 target requirements
        v5_db_throughput = 10000  # ops/sec
        v5_analysis_throughput = 100  # analyses/sec

        current_db = capacity["current_db_throughput"]
        current_analysis = capacity["current_analysis_throughput"]

        db_scaling_factor = v5_db_throughput / current_db if current_db > 0 else 0
        analysis_scaling_factor = v5_analysis_throughput / current_analysis if current_analysis > 0 else 0

        return {
            "v5_db_throughput_target": v5_db_throughput,
            "v5_analysis_throughput_target": v5_analysis_throughput,
            "current_db_throughput": current_db,
            "current_analysis_throughput": current_analysis,
            "db_scaling_factor": db_scaling_factor,
            "analysis_scaling_factor": analysis_scaling_factor,
            "required_instances": max(db_scaling_factor, analysis_scaling_factor),
            "horizontal_scaling": db_scaling_factor > 1.0,
            "vertical_scaling_needed": db_scaling_factor < 1.0,
        }

    def generate_report(self) -> V5BaselineReport:
        """Generate complete V5 baseline report."""
        # Run all benchmarks
        self.results = []
        self.results.extend(self.benchmark_database_performance())
        self.results.extend(self.benchmark_analysis_performance())
        self.results.extend(self.benchmark_api_performance())
        self.results.extend(self.benchmark_realtime_hardware())
        self.results.extend(self.benchmark_gpu_performance())

        # Calculate overall score
        achieved_count = sum(1 for r in self.results if r.achieved)
        total_count = len(self.results)
        overall_score = (achieved_count / total_count * 100) if total_count > 0 else 0

        # Determine V5 readiness
        if overall_score >= 80:
            readiness = "ready"
        elif overall_score >= 50:
            readiness = "partial"
        else:
            readiness = "not_ready"

        # Identify critical gaps
        critical_gaps = [
            f"{r.metric_name}: {r.gap_percent:.1f}% gap"
            for r in self.results
            if not r.achieved and r.category in ["database", "realtime", "gpu"]
        ]

        # Generate recommendations
        recommendations = []
        if not any(r.achieved for r in self.results if r.category == "database"):
            recommendations.append("Optimize database queries and consider PostgreSQL 15+ with TimescaleDB")
        if not any(r.achieved for r in self.results if r.category == "realtime"):
            recommendations.append("Implement DPDK for kernel-bypass networking and FPGA for critical path processing")
        if not any(r.achieved for r in self.results if r.category == "gpu"):
            recommendations.append("Deploy GPU infrastructure with CUDA 12.2+ and TensorRT 8.6+ for ML inference")
        if not any(r.achieved for r in self.results if r.category == "general"):
            recommendations.append("Migrate to Python 3.11+ with uvloop and async database drivers")

        return V5BaselineReport(
            system_info=self.collect_system_info(),
            benchmarks=self.results,
            overall_score=overall_score,
            v5_readiness=readiness,
            critical_gaps=critical_gaps,
            recommendations=recommendations,
            capacity_metrics=self.calculate_capacity_metrics(),
            scaling_projections=self.calculate_scaling_projections(),
        )

    def save_report(self, report: V5BaselineReport, path: Optional[Path] = None) -> None:
        """Save baseline report to file."""
        path = path or self.storage_path
        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(report)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_report(self, path: Optional[Path] = None) -> Optional[V5BaselineReport]:
        """Load baseline report from file."""
        path = path or self.storage_path
        if not path.exists():
            return None

        with open(path, 'r') as f:
            data = json.load(f)

        return V5BaselineReport(**data)


def main():
    """Run V5 baseline generation."""
    print("Generating V5 Performance Baseline...")
    print("=" * 60)

    runner = V5BaselineRunner()
    report = runner.generate_report()

    print(f"\nSystem Info:")
    print(f"  Platform: {report.system_info['platform']}")
    print(f"  Python: {report.system_info['python_version']}")
    print(f"  CPU Cores: {report.system_info['cpu_count']}")
    print(f"  Memory: {report.system_info.get('memory_total_gb', 0):.2f} GB")
    print(f"  GPUs: {report.system_info.get('gpu_count', 0)}")

    print(f"\nV5 Readiness: {report.v5_readiness.upper()}")
    print(f"Overall Score: {report.overall_score:.1f}%")

    print(f"\nBenchmark Results:")
    for result in report.benchmarks:
        status = "✓" if result.achieved else "✗"
        print(f"  {status} {result.metric_name}: {result.measured_value:.2f} {result.unit} "
              f"(target: {result.target_value:.2f} {result.unit}, gap: {result.gap_percent:.1f}%)")

    print(f"\nCritical Gaps:")
    for gap in report.critical_gaps:
        print(f"  - {gap}")

    print(f"\nRecommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")

    print(f"\nCapacity Metrics:")
    for key, value in report.capacity_metrics.items():
        print(f"  {key}: {value}")

    print(f"\nScaling Projections:")
    for key, value in report.scaling_projections.items():
        print(f"  {key}: {value}")

    # Save report
    runner.save_report(report)
    print(f"\nReport saved to: {runner.storage_path}")

    return report


if __name__ == "__main__":
    main()
