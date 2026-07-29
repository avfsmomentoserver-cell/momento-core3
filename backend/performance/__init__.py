"""Performance benchmarking and analysis suite for V5 transformation.

This module provides comprehensive performance measurement tools for establishing
baselines, identifying bottlenecks, and validating V5 performance targets.

V5 Performance Framework:
- v5_baseline: Generate performance baselines against V5 specifications
- v5_regression: Track performance regressions over time
- v5_monitoring: Real-time performance monitoring and alerting
- v5_capacity: Capacity planning and scaling analysis

Legacy V4 Tools:
- benchmark: General performance benchmarking
- profiler: Memory and CPU profiling
- metrics: Performance metrics collection
- load_test: Load testing and stress testing
"""

# V5 Performance Framework
from .v5_baseline import (
    V5BaselineRunner,
    V5PerformanceTargets,
    V5BenchmarkResult,
    V5BaselineReport,
)

from .v5_regression import (
    V5RegressionTester,
    RegressionThreshold,
    RegressionAlert,
    RegressionReport,
)

from .v5_monitoring import (
    RealtimeMetricsCollector,
    V5PerformanceMonitor,
    RealtimeMetric,
    MetricThreshold,
    PerformanceAlert,
    MonitoringReport,
)

from .v5_capacity import (
    V5CapacityPlanner,
    CapacityRequirement,
    ScalingRecommendation,
    CapacityPlan,
)

from .v5_performance_config import (
    V5PerformanceConfig,
    get_config,
)

from .v5_bottleneck import (
    V5BottleneckAnalyzer,
    V5Bottleneck,
    V5BottleneckAnalysis,
)

# Legacy V4 Tools
from .benchmark import PerformanceBenchmark
from .profiler import MemoryProfiler, CPProfiler

__all__ = [
    # V5 Performance Framework
    "V5BaselineRunner",
    "V5PerformanceTargets",
    "V5BenchmarkResult",
    "V5BaselineReport",
    "V5RegressionTester",
    "RegressionThreshold",
    "RegressionAlert",
    "RegressionReport",
    "RealtimeMetricsCollector",
    "V5PerformanceMonitor",
    "RealtimeMetric",
    "MetricThreshold",
    "PerformanceAlert",
    "MonitoringReport",
    "V5CapacityPlanner",
    "CapacityRequirement",
    "ScalingRecommendation",
    "CapacityPlan",
    "V5PerformanceConfig",
    "get_config",
    "V5BottleneckAnalyzer",
    "V5Bottleneck",
    "V5BottleneckAnalysis",
    # Legacy V4 Tools
    "PerformanceBenchmark",
    "MemoryProfiler",
    "CPProfiler",
]
