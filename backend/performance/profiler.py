"""Memory and CPU profiling tools for bottleneck identification.

Provides detailed profiling of system components to identify memory leaks,
CPU hotspots, and resource utilization patterns.
"""

from __future__ import annotations

import cProfile
import io
import pstats
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from momento import db, store, analysis


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: str
    current_mb: float
    peak_mb: float
    allocations: int
    top_allocations: List[Dict[str, Any]]


@dataclass
class CPUProfile:
    """CPU profiling results."""
    timestamp: str
    total_time: float
    function_calls: int
    top_functions: List[Dict[str, Any]]
    cumulative_stats: Dict[str, Any]


@dataclass
class BottleneckReport:
    """Complete bottleneck analysis report."""
    memory_bottlenecks: List[Dict[str, Any]]
    cpu_bottlenecks: List[Dict[str, Any]]
    database_bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    severity: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class MemoryProfiler:
    """Memory profiling for identifying memory leaks and high-usage components."""

    def __init__(self):
        self._snapshots: List[MemorySnapshot] = []
        self._baseline: Optional[MemorySnapshot] = None

    def start(self):
        """Start memory tracking."""
        tracemalloc.start()
        self._baseline = self._take_snapshot("baseline")

    def stop(self):
        """Stop memory tracking."""
        tracemalloc.stop()

    def _take_snapshot(self, label: str = "") -> MemorySnapshot:
        """Take a memory snapshot."""
        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()

        # Get top allocations
        top_stats = snapshot.statistics('lineno')
        top_allocations = []
        for stat in top_stats[:10]:
            top_allocations.append({
                "file": str(stat.traceback[0].filename),
                "line": stat.traceback[0].lineno,
                "size_kb": stat.size / 1024,
                "count": stat.count,
            })

        return MemorySnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            current_mb=current / 1024 / 1024,
            peak_mb=peak / 1024 / 1024,
            allocations=len(snapshot.statistics('lineno')),
            top_allocations=top_allocations,
        )

    @contextmanager
    def profile_operation(self, operation_name: str):
        """Profile a specific operation."""
        self.start()
        try:
            yield
        finally:
            snapshot = self._take_snapshot(operation_name)
            self._snapshots.append(snapshot)
            self.stop()

    def profile_database_operations(self, iterations: int = 100) -> MemorySnapshot:
        """Profile database operations."""
        self.start()

        test_rounds = [
            {
                "source": "profiler",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(10)
        ]

        for _ in range(iterations):
            try:
                store.insert_rounds(test_rounds, method="profiler")
                store.get_rounds("profiler", limit=100)
            except Exception:
                pass

        snapshot = self._take_snapshot("database_operations")
        self._snapshots.append(snapshot)
        self.stop()
        return snapshot

    def profile_analysis_operations(self, round_count: int = 500, iterations: int = 100) -> MemorySnapshot:
        """Profile analysis operations."""
        self.start()

        test_rounds = [
            {
                "source": "profiler",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "multiplier": 1.0 + (i % 100) / 10.0,
                "color": "red",
                "band": "low",
                "points": 10.0,
            }
            for i in range(round_count)
        ]

        for _ in range(iterations):
            try:
                analysis.analyze(test_rounds, store.analysis_settings())
            except Exception:
                pass

        snapshot = self._take_snapshot("analysis_operations")
        self._snapshots.append(snapshot)
        self.stop()
        return snapshot

    def get_memory_growth(self) -> Dict[str, Any]:
        """Calculate memory growth between snapshots."""
        if len(self._snapshots) < 2:
            return {"growth_mb": 0, "growth_percent": 0}

        first = self._snapshots[0]
        last = self._snapshots[-1]

        growth_mb = last.current_mb - first.current_mb
        growth_percent = (growth_mb / first.current_mb * 100) if first.current_mb > 0 else 0

        return {
            "growth_mb": growth_mb,
            "growth_percent": growth_percent,
            "first_snapshot": first.timestamp,
            "last_snapshot": last.timestamp,
        }

    def identify_memory_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify memory bottlenecks from snapshots."""
        bottlenecks = []

        for snapshot in self._snapshots:
            for alloc in snapshot.top_allocations:
                if alloc["size_kb"] > 100:  # > 100KB allocation
                    bottlenecks.append({
                        "type": "large_allocation",
                        "file": alloc["file"],
                        "line": alloc["line"],
                        "size_kb": alloc["size_kb"],
                        "count": alloc["count"],
                        "timestamp": snapshot.timestamp,
                    })

        # Check for memory growth
        growth = self.get_memory_growth()
        if growth["growth_percent"] > 50:  # > 50% growth
            bottlenecks.append({
                "type": "memory_leak",
                "growth_mb": growth["growth_mb"],
                "growth_percent": growth["growth_percent"],
                "first_snapshot": growth["first_snapshot"],
                "last_snapshot": growth["last_snapshot"],
            })

        return bottlenecks


class CPProfiler:
    """CPU profiling for identifying performance hotspots."""

    def __init__(self):
        self._profiles: List[CPUProfile] = []

    @contextmanager
    def profile_function(self, function_name: str):
        """Profile a specific function."""
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            yield
        finally:
            profiler.disable()
            self._profiles.append(self._parse_profile(profiler, function_name))

    def _parse_profile(self, profiler: cProfile.Profile, name: str) -> CPUProfile:
        """Parse cProfile results."""
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(20)

        # Parse top functions
        top_functions = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            if len(top_functions) < 20:
                top_functions.append({
                    "function": str(func),
                    "cumulative_time": ct,
                    "total_time": tt,
                    "call_count": cc,
                })

        return CPUProfile(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            total_time=stats.total_tt,
            function_calls=stats.total_calls,
            top_functions=top_functions,
            cumulative_stats={"raw_output": s.getvalue()},
        )

    def profile_database_operations(self, iterations: int = 100) -> CPUProfile:
        """Profile database operations."""
        with self.profile_function("database_operations"):
            test_rounds = [
                {
                    "source": "profiler",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "multiplier": 1.0 + (i % 100) / 10.0,
                    "color": "red",
                    "band": "low",
                    "points": 10.0,
                }
                for i in range(10)
            ]

            for _ in range(iterations):
                try:
                    store.insert_rounds(test_rounds, method="profiler")
                    store.get_rounds("profiler", limit=100)
                except Exception:
                    pass

        return self._profiles[-1]

    def profile_analysis_operations(self, round_count: int = 500, iterations: int = 100) -> CPUProfile:
        """Profile analysis operations."""
        with self.profile_function("analysis_operations"):
            test_rounds = [
                {
                    "source": "profiler",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "multiplier": 1.0 + (i % 100) / 10.0,
                    "color": "red",
                    "band": "low",
                    "points": 10.0,
                }
                for i in range(round_count)
            ]

            for _ in range(iterations):
                try:
                    analysis.analyze(test_rounds, store.analysis_settings())
                except Exception:
                    pass

        return self._profiles[-1]

    def identify_cpu_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify CPU bottlenecks from profiles."""
        bottlenecks = []

        for profile in self._profiles:
            for func in profile.top_functions:
                # Functions taking > 10% of total time
                if func["cumulative_time"] / profile.total_time > 0.1:
                    bottlenecks.append({
                        "type": "cpu_hotspot",
                        "function": func["function"],
                        "cumulative_time": func["cumulative_time"],
                        "total_time": func["total_time"],
                        "call_count": func["call_count"],
                        "percentage": func["cumulative_time"] / profile.total_time * 100,
                        "timestamp": profile.timestamp,
                    })

        return bottlenecks


class BottleneckAnalyzer:
    """Comprehensive bottleneck analysis combining memory and CPU profiling."""

    def __init__(self):
        self.memory_profiler = MemoryProfiler()
        self.cpu_profiler = CPProfiler()

    def analyze_database_bottlenecks(self, iterations: int = 100) -> Dict[str, Any]:
        """Analyze database-specific bottlenecks."""
        memory_snapshot = self.memory_profiler.profile_database_operations(iterations)
        cpu_profile = self.cpu_profiler.profile_database_operations(iterations)

        return {
            "memory_snapshot": memory_snapshot,
            "cpu_profile": cpu_profile,
            "identified_issues": self._identify_database_issues(memory_snapshot, cpu_profile),
        }

    def analyze_analysis_bottlenecks(self, round_count: int = 500, iterations: int = 100) -> Dict[str, Any]:
        """Analyze analysis engine bottlenecks."""
        memory_snapshot = self.memory_profiler.profile_analysis_operations(round_count, iterations)
        cpu_profile = self.cpu_profiler.profile_analysis_operations(round_count, iterations)

        return {
            "memory_snapshot": memory_snapshot,
            "cpu_profile": cpu_profile,
            "identified_issues": self._identify_analysis_issues(memory_snapshot, cpu_profile),
        }

    def _identify_database_issues(self, memory_snapshot: MemorySnapshot, cpu_profile: CPUProfile) -> List[str]:
        """Identify database-specific issues."""
        issues = []

        # Check for high memory usage
        if memory_snapshot.current_mb > 100:
            issues.append(f"High memory usage during database operations: {memory_snapshot.current_mb:.2f}MB")

        # Check for slow operations
        if cpu_profile.total_time > 1.0:
            issues.append(f"Slow database operations: {cpu_profile.total_time:.2f}s total")

        # Check for lock contention
        for func in cpu_profile.top_functions:
            if "lock" in func["function"].lower() or "wait" in func["function"].lower():
                issues.append(f"Potential lock contention in: {func['function']}")

        return issues

    def _identify_analysis_issues(self, memory_snapshot: MemorySnapshot, cpu_profile: CPUProfile) -> List[str]:
        """Identify analysis engine-specific issues."""
        issues = []

        # Check for high memory usage
        if memory_snapshot.current_mb > 200:
            issues.append(f"High memory usage during analysis: {memory_snapshot.current_mb:.2f}MB")

        # Check for slow operations
        if cpu_profile.total_time > 5.0:
            issues.append(f"Slow analysis operations: {cpu_profile.total_time:.2f}s total")

        # Check for inefficient algorithms
        for func in cpu_profile.top_functions:
            if func["cumulative_time"] / cpu_profile.total_time > 0.3:
                issues.append(f"Major CPU hotspot: {func['function']} ({func['percentage']:.1f}% of time)")

        return issues

    def generate_bottleneck_report(self) -> BottleneckReport:
        """Generate comprehensive bottleneck report."""
        memory_bottlenecks = self.memory_profiler.identify_memory_bottlenecks()
        cpu_bottlenecks = self.cpu_profiler.identify_cpu_bottlenecks()

        # Generate recommendations
        recommendations = self._generate_recommendations(memory_bottlenecks, cpu_bottlenecks)

        # Determine severity
        severity = self._calculate_severity(memory_bottlenecks, cpu_bottlenecks)

        return BottleneckReport(
            memory_bottlenecks=memory_bottlenecks,
            cpu_bottlenecks=cpu_bottlenecks,
            database_bottlenecks=[],
            recommendations=recommendations,
            severity=severity,
        )

    def _generate_recommendations(self, memory_bottlenecks: List, cpu_bottlenecks: List) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Memory recommendations
        for bottleneck in memory_bottlenecks:
            if bottleneck["type"] == "memory_leak":
                recommendations.append(
                    f"Memory leak detected: {bottleneck['growth_mb']:.2f}MB growth. "
                    "Implement memory pooling and investigate object lifecycle."
                )
            elif bottleneck["type"] == "large_allocation":
                recommendations.append(
                    f"Large allocation at {bottleneck['file']}:{bottleneck['line']} "
                    f"({bottleneck['size_kb']:.2f}KB). Consider batching or streaming."
                )

        # CPU recommendations
        for bottleneck in cpu_bottlenecks:
            if bottleneck["type"] == "cpu_hotspot":
                recommendations.append(
                    f"CPU hotspot in {bottleneck['function']} ({bottleneck['percentage']:.1f}%). "
                    "Consider caching, memoization, or algorithm optimization."
                )

        return recommendations

    def _calculate_severity(self, memory_bottlenecks: List, cpu_bottlenecks: List) -> str:
        """Calculate overall severity of bottlenecks."""
        critical_count = sum(
            1 for b in memory_bottlenecks + cpu_bottlenecks
            if b.get("growth_percent", 0) > 100 or b.get("percentage", 0) > 30
        )

        if critical_count > 3:
            return "critical"
        elif critical_count > 1:
            return "high"
        elif len(memory_bottlenecks) + len(cpu_bottlenecks) > 5:
            return "medium"
        else:
            return "low"


if __name__ == "__main__":
    analyzer = BottleneckAnalyzer()

    print("Analyzing database bottlenecks...")
    db_analysis = analyzer.analyze_database_bottlenecks(iterations=50)
    print(f"Memory usage: {db_analysis['memory_snapshot'].current_mb:.2f}MB")
    print(f"CPU time: {db_analysis['cpu_profile'].total_time:.2f}s")
    print("Issues:", db_analysis["identified_issues"])

    print("\nAnalyzing analysis bottlenecks...")
    analysis_analysis = analyzer.analyze_analysis_bottlenecks(round_count=200, iterations=50)
    print(f"Memory usage: {analysis_analysis['memory_snapshot'].current_mb:.2f}MB")
    print(f"CPU time: {analysis_analysis['cpu_profile'].total_time:.2f}s")
    print("Issues:", analysis_analysis["identified_issues"])

    print("\nGenerating bottleneck report...")
    report = analyzer.generate_bottleneck_report()
    print(f"Severity: {report.severity}")
    print("Recommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")
