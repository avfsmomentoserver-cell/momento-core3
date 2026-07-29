"""V5 Performance Framework Configuration.

Centralized configuration for V5 performance testing, monitoring,
and capacity planning.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class V5PerformanceConfig:
    """Configuration for V5 performance framework."""

    # Storage paths
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    baseline_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "v5_baseline.json")
    regression_history_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "v5_regression_history.json")
    capacity_plan_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "v5_capacity_plan.json")
    monitoring_reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "monitoring_reports")
    bottleneck_analysis_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "v5_bottleneck_analysis.json")

    # Benchmark settings
    benchmark_warmup_iterations: int = 10
    benchmark_iterations: int = 100
    benchmark_batch_size: int = 100
    benchmark_round_count: int = 500

    # Monitoring settings
    monitoring_interval_seconds: float = 1.0
    monitoring_window_size: int = 1000
    monitoring_duration_seconds: float = 60.0
    monitoring_alert_consecutive_violations: int = 3

    # Regression testing settings
    regression_check_interval_hours: float = 24.0
    regression_history_entries: int = 30
    regression_auto_fail_on_critical: bool = True

    # Capacity planning settings
    capacity_safety_margin: float = 0.2  # 20% safety margin
    capacity_growth_projection_months: int = 12

    # V5 target thresholds (from specifications)
    v5_db_insert_latency_p50_ms: float = 1.0
    v5_db_insert_latency_p99_ms: float = 5.0
    v5_db_select_latency_p50_ms: float = 0.5
    v5_db_throughput_ops_per_sec: float = 10000

    v5_packet_processing_latency_us: float = 2.0
    v5_fix_protocol_parse_ns: float = 14.0
    v5_orderbook_update_ns: float = 4.0
    v5_feature_extraction_ns: float = 50.0

    v5_inference_latency_ms: float = 1.0
    v5_inference_throughput_per_sec: float = 1000
    v5_model_memory_gb: float = 2.0

    v5_api_latency_p50_ms: float = 10.0
    v5_api_latency_p99_ms: float = 50.0
    v5_api_throughput_req_per_sec: float = 5000

    v5_analysis_latency_500_rounds_ms: float = 100.0
    v5_analysis_throughput_per_sec: float = 100

    # Tolerance percentages for each category
    database_tolerance_percent: float = 20.0
    realtime_tolerance_percent: float = 50.0
    gpu_tolerance_percent: float = 50.0
    api_tolerance_percent: float = 30.0
    analysis_tolerance_percent: float = 30.0

    # Alert thresholds
    db_insert_latency_max_ms: float = 10.0
    db_select_latency_max_ms: float = 5.0
    analysis_latency_max_ms: float = 200.0
    api_latency_max_ms: float = 100.0
    memory_usage_max_mb: float = 4096.0
    cpu_usage_max_percent: float = 80.0

    # V5 readiness thresholds
    v5_ready_score_min: float = 80.0
    v5_partial_score_min: float = 50.0

    # Categories
    categories: List[str] = field(default_factory=lambda: ["database", "realtime", "gpu", "api", "analysis"])

    def __post_init__(self):
        """Create directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.monitoring_reports_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = V5PerformanceConfig()


def get_config() -> V5PerformanceConfig:
    """Get the global configuration instance."""
    return config


def reload_config(config_path: Optional[Path] = None) -> V5PerformanceConfig:
    """Reload configuration from file (if implemented)."""
    # For now, return default config
    # Could be extended to load from JSON/YAML file
    return V5PerformanceConfig()
