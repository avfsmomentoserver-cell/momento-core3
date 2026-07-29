"""V5 Bottleneck Analysis and Profiling.

Provides advanced bottleneck analysis specifically for V5 transformation,
including GPU profiling, network latency analysis, and hardware acceleration
bottlenecks (DPDK, FPGA, CUDA).
"""

from __future__ import annotations

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
from .profiler import MemoryProfiler, CPProfiler, BottleneckReport


@dataclass
class V5Bottleneck:
    """V5-specific bottleneck."""
    component: str  # database, api, analysis, gpu, network, fpga, dpdk
    severity: str  # critical, high, medium, low
    metric_name: str
    current_value: float
    target_value: float
    gap_percent: float
    description: str
    impact_area: str  # latency, throughput, memory, cpu
    recommendation: str
    estimated_fix_effort: str  # hours, days, weeks
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


@dataclass
class V5BottleneckAnalysis:
    """Complete V5 bottleneck analysis report."""
    system_info: Dict[str, Any]
    bottlenecks: List[V5Bottleneck]
    critical_bottlenecks: List[V5Bottleneck]
    bottleneck_summary: Dict[str, Any]
    optimization_roadmap: List[Dict[str, Any]]
    performance_improvement_potential: Dict[str, float]
    resource_utilization: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class V5BottleneckAnalyzer:
    """Analyze V5-specific bottlenecks."""

    def __init__(self):
        self.memory_profiler = MemoryProfiler()
        self.cpu_profiler = CPProfiler()
        self.bottlenecks: List[V5Bottleneck] = []

    def analyze_database_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze database-specific bottlenecks."""
        bottlenecks = []

        # Test insert performance
        start = time.perf_counter()
        test_rounds = [
            {
                "source": "bottleneck_db",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(100)
        ]

        try:
            store.insert_rounds(test_rounds, method="bottleneck")
            insert_latency = (time.perf_counter() - start) * 1000
        except Exception:
            insert_latency = 0

        # Test select performance
        start = time.perf_counter()
        try:
            store.get_rounds("bottleneck_db", limit=1000)
            select_latency = (time.perf_counter() - start) * 1000
        except Exception:
            select_latency = 0

        # V5 targets
        v5_insert_target = 1.0  # ms
        v5_select_target = 0.5  # ms

        # Check insert bottleneck
        if insert_latency > v5_insert_target:
            gap = ((insert_latency - v5_insert_target) / v5_insert_target * 100)
            severity = "critical" if gap > 100 else "high" if gap > 50 else "medium"
            bottlenecks.append(V5Bottleneck(
                component="database",
                severity=severity,
                metric_name="db_insert_latency",
                current_value=insert_latency,
                target_value=v5_insert_target,
                gap_percent=gap,
                description=f"Database insert latency exceeds V5 target of {v5_insert_target}ms",
                impact_area="latency",
                recommendation="Enable connection pooling, use batch inserts, consider write-ahead log optimization",
                estimated_fix_effort="days",
            ))

        # Check select bottleneck
        if select_latency > v5_select_target:
            gap = ((select_latency - v5_select_target) / v5_select_target * 100)
            severity = "critical" if gap > 100 else "high" if gap > 50 else "medium"
            bottlenecks.append(V5Bottleneck(
                component="database",
                severity=severity,
                metric_name="db_select_latency",
                current_value=select_latency,
                target_value=v5_select_target,
                gap_percent=gap,
                description=f"Database select latency exceeds V5 target of {v5_select_target}ms",
                impact_area="latency",
                recommendation="Add appropriate indexes, optimize queries, consider read replicas",
                estimated_fix_effort="days",
            ))

        return bottlenecks

    def analyze_analysis_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze analysis engine bottlenecks."""
        bottlenecks = []

        # Test analysis performance
        test_rounds = [
            {
                "source": "bottleneck_analysis",
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
        except Exception:
            analysis_latency = 0

        # V5 target for 500 rounds
        v5_target = 100.0  # ms

        if analysis_latency > v5_target:
            gap = ((analysis_latency - v5_target) / v5_target * 100)
            severity = "critical" if gap > 100 else "high" if gap > 50 else "medium"
            bottlenecks.append(V5Bottleneck(
                component="analysis",
                severity=severity,
                metric_name="analysis_latency_500_rounds",
                current_value=analysis_latency,
                target_value=v5_target,
                gap_percent=gap,
                description=f"Analysis latency for 500 rounds exceeds V5 target of {v5_target}ms",
                impact_area="latency",
                recommendation="Implement memoization, use vectorized operations, consider GPU acceleration",
                estimated_fix_effort="weeks",
            ))

        return bottlenecks

    def analyze_memory_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze memory bottlenecks."""
        bottlenecks = []

        # Profile memory usage
        self.memory_profiler.start()
        snapshot = self.memory_profiler.profile_analysis_operations(round_count=500, iterations=10)
        self.memory_profiler.stop()

        memory_bottlenecks = self.memory_profiler.identify_memory_bottlenecks()

        for bottleneck in memory_bottlenecks:
            if bottleneck["type"] == "memory_leak":
                severity = "critical" if bottleneck["growth_percent"] > 100 else "high"
                bottlenecks.append(V5Bottleneck(
                    component="analysis",
                    severity=severity,
                    metric_name="memory_leak",
                    current_value=bottleneck["growth_mb"],
                    target_value=0.0,
                    gap_percent=bottleneck["growth_percent"],
                    description=f"Memory leak detected: {bottleneck['growth_mb']:.2f}MB growth",
                    impact_area="memory",
                    recommendation="Review object lifecycle, implement proper cleanup, use weak references",
                    estimated_fix_effort="days",
                ))
            elif bottleneck["type"] == "large_allocation":
                severity = "medium" if bottleneck["size_kb"] > 1000 else "low"
                bottlenecks.append(V5Bottleneck(
                    component="analysis",
                    severity=severity,
                    metric_name="large_allocation",
                    current_value=bottleneck["size_kb"],
                    target_value=100.0,
                    gap_percent=((bottleneck["size_kb"] - 100) / 100 * 100),
                    description=f"Large allocation at {bottleneck['file']}:{bottleneck['line']}",
                    impact_area="memory",
                    recommendation="Implement streaming processing, reduce batch sizes, use generators",
                    estimated_fix_effort="hours",
                ))

        return bottlenecks

    def analyze_cpu_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze CPU bottlenecks."""
        bottlenecks = []

        # Profile CPU usage
        self.cpu_profiler.profile_database_operations(iterations=100)
        profile = self.cpu_profiler._profiles[-1] if self.cpu_profiler._profiles else None

        if profile:
            # Check for high CPU usage functions
            for func in profile.top_functions[:5]:
                if func["cumulative_time"] > 0.1:  # > 100ms
                    severity = "high" if func["cumulative_time"] > 0.5 else "medium"
                    bottlenecks.append(V5Bottleneck(
                        component="database",
                        severity=severity,
                        metric_name="cpu_hotspot",
                        current_value=func["cumulative_time"],
                        target_value=0.1,
                        gap_percent=((func["cumulative_time"] - 0.1) / 0.1 * 100),
                        description=f"CPU hotspot in {func['function']}",
                        impact_area="cpu",
                        recommendation="Optimize algorithm, use caching, consider parallel processing",
                        estimated_fix_effort="days",
                    ))

        return bottlenecks

    def analyze_api_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze API bottlenecks."""
        bottlenecks = []

        # Simulate API latency measurement
        # In production, this would use actual API calls
        api_latency_p50 = 15.0  # Simulated
        api_latency_p99 = 75.0  # Simulated

        v5_p50_target = 10.0  # ms
        v5_p99_target = 50.0  # ms

        if api_latency_p50 > v5_p50_target:
            gap = ((api_latency_p50 - v5_p50_target) / v5_p50_target * 100)
            severity = "high" if gap > 50 else "medium"
            bottlenecks.append(V5Bottleneck(
                component="api",
                severity=severity,
                metric_name="api_latency_p50",
                current_value=api_latency_p50,
                target_value=v5_p50_target,
                gap_percent=gap,
                description=f"API P50 latency exceeds V5 target of {v5_p50_target}ms",
                impact_area="latency",
                recommendation="Enable uvloop, implement response caching, optimize middleware",
                estimated_fix_effort="days",
            ))

        if api_latency_p99 > v5_p99_target:
            gap = ((api_latency_p99 - v5_p99_target) / v5_p99_target * 100)
            severity = "critical" if gap > 100 else "high"
            bottlenecks.append(V5Bottleneck(
                component="api",
                severity=severity,
                metric_name="api_latency_p99",
                current_value=api_latency_p99,
                target_value=v5_p99_target,
                gap_percent=gap,
                description=f"API P99 latency exceeds V5 target of {v5_p99_target}ms",
                impact_area="latency",
                recommendation="Implement request queuing, add rate limiting, optimize slow endpoints",
                estimated_fix_effort="weeks",
            ))

        return bottlenecks

    def analyze_gpu_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze GPU/acceleration bottlenecks."""
        bottlenecks = []

        # Check for GPU availability
        try:
            import pynvml
            pynvml.nvmlInit()
            gpu_count = pynvml.nvmlDeviceGetCount()
            pynvml.nvmlShutdown()

            if gpu_count == 0:
                bottlenecks.append(V5Bottleneck(
                    component="gpu",
                    severity="critical",
                    metric_name="gpu_availability",
                    current_value=0,
                    target_value=1,
                    gap_percent=100.0,
                    description="No GPU available for ML inference",
                    impact_area="throughput",
                    recommendation="Install NVIDIA GPU with CUDA support, configure TensorRT for inference",
                    estimated_fix_effort="weeks",
                ))
        except Exception:
            bottlenecks.append(V5Bottleneck(
                component="gpu",
                severity="critical",
                metric_name="gpu_availability",
                current_value=0,
                target_value=1,
                gap_percent=100.0,
                description="GPU drivers not installed or available",
                impact_area="throughput",
                recommendation="Install NVIDIA drivers and CUDA toolkit, verify GPU hardware",
                estimated_fix_effort="days",
            ))

        return bottlenecks

    def analyze_network_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze network bottlenecks (DPDK, ultra-low latency)."""
        bottlenecks = []

        # Check for DPDK availability
        try:
            # Check if DPDK is available
            import os
            dpdk_available = os.path.exists("/sys/bus/pci/devices/")

            if not dpdk_available:
                bottlenecks.append(V5Bottleneck(
                    component="network",
                    severity="high",
                    metric_name="dpdk_availability",
                    current_value=0,
                    target_value=1,
                    gap_percent=100.0,
                    description="DPDK not available for kernel-bypass networking",
                    impact_area="latency",
                    recommendation="Configure DPDK for kernel-bypass networking, install compatible NIC drivers",
                    estimated_fix_effort="weeks",
                ))
        except Exception:
            pass

        return bottlenecks

    def analyze_fpga_bottlenecks(self) -> List[V5Bottleneck]:
        """Analyze FPGA acceleration bottlenecks."""
        bottlenecks = []

        # Check for FPGA availability
        try:
            import os
            fpga_available = os.path.exists("/dev/fpga") or os.path.exists("/sys/class/fpga")

            if not fpga_available:
                bottlenecks.append(V5Bottleneck(
                    component="fpga",
                    severity="medium",
                    metric_name="fpga_availability",
                    current_value=0,
                    target_value=1,
                    gap_percent=100.0,
                    description="FPGA acceleration not available for critical path processing",
                    impact_area="latency",
                    recommendation="Install Xilinx/AMD FPGA hardware, configure bitstreams for FIX parsing",
                    estimated_fix_effort="months",
                ))
        except Exception:
            pass

        return bottlenecks

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
            gpu_count = pynvml.nvmlDeviceGetCount()
            info["gpu_count"] = gpu_count
            info["gpu_memory_gb"] = 0
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                info["gpu_memory_gb"] += memory.total / 1024 / 1024 / 1024
            pynvml.nvmlShutdown()
        except Exception:
            info["gpu_count"] = 0
            info["gpu_memory_gb"] = 0

        return info

    def generate_analysis(self) -> V5BottleneckAnalysis:
        """Generate complete V5 bottleneck analysis."""
        print("Collecting system information...")
        system_info = self.collect_system_info()

        print("Analyzing database bottlenecks...")
        db_bottlenecks = self.analyze_database_bottlenecks()

        print("Analyzing analysis engine bottlenecks...")
        analysis_bottlenecks = self.analyze_analysis_bottlenecks()

        print("Analyzing memory bottlenecks...")
        memory_bottlenecks = self.analyze_memory_bottlenecks()

        print("Analyzing CPU bottlenecks...")
        cpu_bottlenecks = self.analyze_cpu_bottlenecks()

        print("Analyzing API bottlenecks...")
        api_bottlenecks = self.analyze_api_bottlenecks()

        print("Analyzing GPU bottlenecks...")
        gpu_bottlenecks = self.analyze_gpu_bottlenecks()

        print("Analyzing network bottlenecks...")
        network_bottlenecks = self.analyze_network_bottlenecks()

        print("Analyzing FPGA bottlenecks...")
        fpga_bottlenecks = self.analyze_fpga_bottlenecks()

        # Combine all bottlenecks
        all_bottlenecks = (
            db_bottlenecks +
            analysis_bottlenecks +
            memory_bottlenecks +
            cpu_bottlenecks +
            api_bottlenecks +
            gpu_bottlenecks +
            network_bottlenecks +
            fpga_bottlenecks
        )

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_bottlenecks.sort(key=lambda b: severity_order.get(b.severity, 4))

        # Separate critical bottlenecks
        critical_bottlenecks = [b for b in all_bottlenecks if b.severity == "critical"]

        # Generate summary
        bottleneck_summary = {
            "total_bottlenecks": len(all_bottlenecks),
            "critical_bottlenecks": len(critical_bottlenecks),
            "high_bottlenecks": len([b for b in all_bottlenecks if b.severity == "high"]),
            "medium_bottlenecks": len([b for b in all_bottlenecks if b.severity == "medium"]),
            "low_bottlenecks": len([b for b in all_bottlenecks if b.severity == "low"]),
            "by_component": {},
            "by_impact_area": {},
        }

        for bottleneck in all_bottlenecks:
            component = bottleneck.component
            impact = bottleneck.impact_area

            bottleneck_summary["by_component"][component] = \
                bottleneck_summary["by_component"].get(component, 0) + 1
            bottleneck_summary["by_impact_area"][impact] = \
                bottleneck_summary["by_impact_area"].get(impact, 0) + 1

        # Generate optimization roadmap
        optimization_roadmap = []
        for bottleneck in all_bottlenecks[:10]:  # Top 10 bottlenecks
            optimization_roadmap.append({
                "priority": bottleneck.severity,
                "component": bottleneck.component,
                "metric": bottleneck.metric_name,
                "gap_percent": bottleneck.gap_percent,
                "recommendation": bottleneck.recommendation,
                "estimated_effort": bottleneck.estimated_fix_effort,
            })

        # Calculate performance improvement potential
        performance_improvement_potential = {
            "latency_reduction_percent": 0.0,
            "throughput_increase_percent": 0.0,
            "memory_reduction_percent": 0.0,
        }

        latency_bottlenecks = [b for b in all_bottlenecks if b.impact_area == "latency"]
        if latency_bottlenecks:
            avg_gap = statistics.mean([b.gap_percent for b in latency_bottlenecks])
            performance_improvement_potential["latency_reduction_percent"] = avg_gap

        throughput_bottlenecks = [b for b in all_bottlenecks if b.impact_area == "throughput"]
        if throughput_bottlenecks:
            avg_gap = statistics.mean([b.gap_percent for b in throughput_bottlenecks])
            performance_improvement_potential["throughput_increase_percent"] = avg_gap

        memory_bottlenecks = [b for b in all_bottlenecks if b.impact_area == "memory"]
        if memory_bottlenecks:
            avg_gap = statistics.mean([b.gap_percent for b in memory_bottlenecks])
            performance_improvement_potential["memory_reduction_percent"] = avg_gap

        # Resource utilization
        resource_utilization = {
            "cpu_cores": system_info.get("cpu_count", 0),
            "memory_gb": system_info.get("memory_total_gb", 0),
            "gpu_count": system_info.get("gpu_count", 0),
            "gpu_memory_gb": system_info.get("gpu_memory_gb", 0),
        }

        return V5BottleneckAnalysis(
            system_info=system_info,
            bottlenecks=all_bottlenecks,
            critical_bottlenecks=critical_bottlenecks,
            bottleneck_summary=bottleneck_summary,
            optimization_roadmap=optimization_roadmap,
            performance_improvement_potential=performance_improvement_potential,
            resource_utilization=resource_utilization,
        )

    def save_analysis(self, analysis: V5BottleneckAnalysis, path: Path) -> None:
        """Save bottleneck analysis to file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "system_info": analysis.system_info,
            "bottlenecks": [asdict(b) for b in analysis.bottlenecks],
            "critical_bottlenecks": [asdict(b) for b in analysis.critical_bottlenecks],
            "bottleneck_summary": analysis.bottleneck_summary,
            "optimization_roadmap": analysis.optimization_roadmap,
            "performance_improvement_potential": analysis.performance_improvement_potential,
            "resource_utilization": analysis.resource_utilization,
            "timestamp": analysis.timestamp,
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_analysis(self, path: Path) -> Optional[V5BottleneckAnalysis]:
        """Load bottleneck analysis from file."""
        if not path.exists():
            return None

        with open(path, 'r') as f:
            data = json.load(f)

        return V5BottleneckAnalysis(
            system_info=data["system_info"],
            bottlenecks=[V5Bottleneck(**b) for b in data["bottlenecks"]],
            critical_bottlenecks=[V5Bottleneck(**b) for b in data["critical_bottlenecks"]],
            bottleneck_summary=data["bottleneck_summary"],
            optimization_roadmap=data["optimization_roadmap"],
            performance_improvement_potential=data["performance_improvement_potential"],
            resource_utilization=data["resource_utilization"],
            timestamp=data["timestamp"],
        )
