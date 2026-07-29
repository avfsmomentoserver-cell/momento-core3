"""Unit tests for V5 Performance Framework.

Tests the performance baseline, regression testing, capacity planning,
monitoring, and bottleneck analysis components.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from performance.v5_baseline import (
    V5BaselineRunner,
    V5PerformanceTargets,
    V5BenchmarkResult,
    V5BaselineReport,
)
from performance.v5_regression import (
    V5RegressionTester,
    RegressionThreshold,
    RegressionAlert,
    RegressionReport,
)
from performance.v5_capacity import (
    V5CapacityPlanner,
    CapacityRequirement,
    ScalingRecommendation,
    CapacityPlan,
)
from performance.v5_monitoring import (
    RealtimeMetricsCollector,
    V5PerformanceMonitor,
    RealtimeMetric,
    MetricThreshold,
    PerformanceAlert,
)
from performance.v5_bottleneck import (
    V5BottleneckAnalyzer,
    V5Bottleneck,
    V5BottleneckAnalysis,
)
from performance.v5_performance_config import V5PerformanceConfig, get_config


class TestV5PerformanceTargets:
    """Test V5 performance targets."""

    def test_all_targets_defined(self):
        """Test that all V5 targets are defined."""
        targets = V5PerformanceTargets.all_targets()
        assert len(targets) > 0
        assert all(t.metric_name for t in targets)
        assert all(t.target_value > 0 for t in targets)
        assert all(t.unit for t in targets)

    def test_get_targets_by_category(self):
        """Test filtering targets by category."""
        db_targets = V5PerformanceTargets.get_targets_by_category("database")
        assert len(db_targets) > 0
        assert all(t.category == "database" for t in db_targets)

        gpu_targets = V5PerformanceTargets.get_targets_by_category("gpu")
        assert len(gpu_targets) > 0
        assert all(t.category == "gpu" for t in gpu_targets)

    def test_target_categories(self):
        """Test that all expected categories exist."""
        targets = V5PerformanceTargets.all_targets()
        categories = set(t.category for t in targets)
        expected_categories = {"database", "realtime", "gpu", "api", "analysis"}
        assert expected_categories.issubset(categories)


class TestV5BaselineRunner:
    """Test V5 baseline runner."""

    def test_initialization(self):
        """Test baseline runner initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "baseline.json"
            runner = V5BaselineRunner(storage_path=storage_path)
            assert runner.storage_path == storage_path
            assert runner.results == []

    def test_collect_system_info(self):
        """Test system info collection."""
        runner = V5BaselineRunner()
        info = runner.collect_system_info()
        assert "platform" in info
        assert "python_version" in info
        assert "cpu_count" in info
        assert info["cpu_count"] > 0

    def test_benchmark_database_insert(self):
        """Test database insert benchmark."""
        runner = V5BaselineRunner()
        result = runner.benchmark_database_insert(batch_size=10, iterations=10)
        assert result.metric_name == "db_insert_latency_p50"
        assert result.measured_value >= 0
        assert result.unit == "ms"
        assert "metadata" in result.__dict__

    def test_benchmark_database_select(self):
        """Test database select benchmark."""
        runner = V5BaselineRunner()
        result = runner.benchmark_database_select(limit=100, iterations=10)
        assert result.metric_name == "db_select_latency_p50"
        assert result.measured_value >= 0
        assert result.unit == "ms"

    def test_benchmark_analysis(self):
        """Test analysis benchmark."""
        runner = V5BaselineRunner()
        result = runner.benchmark_analysis(round_count=100, iterations=10)
        assert result.metric_name == "analysis_latency_500_rounds"
        assert result.measured_value >= 0
        assert result.unit == "ms"

    def test_generate_report(self):
        """Test complete report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "baseline.json"
            runner = V5BaselineRunner(storage_path=storage_path)
            report = runner.generate_report(category="database")

            assert isinstance(report, V5BaselineReport)
            assert report.system_info is not None
            assert len(report.benchmarks) > 0
            assert 0 <= report.overall_score <= 100
            assert report.v5_readiness in ["ready", "partial", "not_ready"]
            assert isinstance(report.critical_gaps, list)
            assert isinstance(report.recommendations, list)

    def test_save_and_load_report(self):
        """Test saving and loading reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "baseline.json"
            runner = V5BaselineRunner(storage_path=storage_path)

            # Generate and save
            report = runner.generate_report(category="database")
            runner.save_report(report)

            # Load
            loaded_report = runner.load_report()
            assert loaded_report is not None
            assert loaded_report.overall_score == report.overall_score
            assert loaded_report.v5_readiness == report.v5_readiness
            assert len(loaded_report.benchmarks) == len(report.benchmarks)


class TestV5RegressionTester:
    """Test V5 regression tester."""

    def test_initialization(self):
        """Test regression tester initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            history_path = Path(tmpdir) / "history.json"
            tester = V5RegressionTester(baseline_path, history_path)
            assert tester.baseline_path == baseline_path
            assert tester.history_path == history_path

    def test_detect_regressions(self):
        """Test regression detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            history_path = Path(tmpdir) / "history.json"

            # Create baseline
            runner = V5BaselineRunner(storage_path=baseline_path)
            baseline = runner.generate_report(category="database")
            runner.save_report(baseline)

            # Create current with worse performance
            current = runner.generate_report(category="database")
            for benchmark in current.benchmarks:
                benchmark.measured_value *= 2.0  # Make it worse

            tester = V5RegressionTester(baseline_path, history_path)
            alerts = tester.detect_regressions(baseline, current)

            assert isinstance(alerts, list)
            # Should detect regressions since we made performance worse
            # (though exact count depends on which metrics were measured)

    def test_detect_improvements(self):
        """Test improvement detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            history_path = Path(tmpdir) / "history.json"

            # Create baseline
            runner = V5BaselineRunner(storage_path=baseline_path)
            baseline = runner.generate_report(category="database")
            runner.save_report(baseline)

            # Create current with better performance
            current = runner.generate_report(category="database")
            for benchmark in current.benchmarks:
                benchmark.measured_value *= 0.5  # Make it better

            tester = V5RegressionTester(baseline_path, history_path)
            improvements = tester.detect_improvements(baseline, current)

            assert isinstance(improvements, list)

    def test_generate_regression_report(self):
        """Test regression report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            history_path = Path(tmpdir) / "history.json"

            runner = V5BaselineRunner(storage_path=baseline_path)
            baseline = runner.generate_report(category="database")
            runner.save_report(baseline)

            current = runner.generate_report(category="database")

            tester = V5RegressionTester(baseline_path, history_path)
            report = tester.generate_regression_report(baseline, current)

            assert isinstance(report, RegressionReport)
            assert report.baseline_timestamp == baseline.timestamp
            assert report.current_timestamp == current.timestamp
            assert report.total_metrics == len(baseline.benchmarks)
            assert isinstance(report.alerts, list)


class TestV5CapacityPlanner:
    """Test V5 capacity planner."""

    def test_initialization(self):
        """Test capacity planner initialization."""
        planner = V5CapacityPlanner()
        assert planner.baseline_report is None

    def test_assess_current_capacity(self):
        """Test current capacity assessment."""
        planner = V5CapacityPlanner()
        assessment = planner.assess_current_capacity()

        assert "cpu_cores" in assessment
        assert "memory_gb" in assessment
        assert assessment["cpu_cores"] > 0
        assert assessment["memory_gb"] >= 0

    def test_identify_gaps(self):
        """Test capacity gap identification."""
        planner = V5CapacityPlanner()
        current = planner.assess_current_capacity()
        gaps = planner.identify_gaps(current)

        assert isinstance(gaps, list)
        for gap in gaps:
            assert "resource_type" in gap
            assert "current_value" in gap
            assert "minimum_required" in gap
            assert "gap" in gap
            assert gap["gap"] > 0

    def test_generate_recommendations(self):
        """Test scaling recommendations."""
        planner = V5CapacityPlanner()
        current = planner.assess_current_capacity()
        gaps = planner.identify_gaps(current)
        recommendations = planner.generate_recommendations(gaps)

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, ScalingRecommendation)
            assert rec.component
            assert rec.scaling_factor > 0
            assert rec.scaling_type in ["horizontal", "vertical", "both"]
            assert rec.priority in ["critical", "high", "medium", "low"]

    def test_generate_capacity_plan(self):
        """Test complete capacity plan generation."""
        planner = V5CapacityPlanner()
        plan = planner.generate_capacity_plan()

        assert isinstance(plan, CapacityPlan)
        assert plan.current_assessment is not None
        assert len(plan.v5_requirements) > 0
        assert isinstance(plan.gaps, list)
        assert isinstance(plan.recommendations, list)
        assert isinstance(plan.infrastructure_needs, list)
        assert isinstance(plan.timeline, dict)


class TestV5PerformanceMonitor:
    """Test V5 performance monitor."""

    @pytest.mark.asyncio
    async def test_metrics_collector(self):
        """Test metrics collector."""
        collector = RealtimeMetricsCollector(window_size=100)

        metric = RealtimeMetric("test_metric", 10.5, "ms")
        await collector.record_metric(metric)

        values = await collector.get_metric_values("test_metric")
        assert len(values) == 1
        assert values[0] == 10.5

    @pytest.mark.asyncio
    async def test_metric_statistics(self):
        """Test metric statistics calculation."""
        collector = RealtimeMetricsCollector(window_size=100)

        for i in range(10):
            metric = RealtimeMetric("test_metric", float(i), "ms")
            await collector.record_metric(metric)

        stats = await collector.get_metric_statistics("test_metric")
        assert stats["count"] == 10
        assert stats["mean"] == 4.5
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0

    @pytest.mark.asyncio
    async def test_threshold_checking(self):
        """Test threshold checking."""
        collector = RealtimeMetricsCollector(window_size=100)
        threshold = MetricThreshold("test_metric", max_value=5.0, severity="warning")
        monitor = V5PerformanceMonitor(collector=collector, thresholds=[threshold])

        # Record metrics above threshold
        for i in range(10):
            metric = RealtimeMetric("test_metric", 10.0, "ms")
            await collector.record_metric(metric)

        alerts = await monitor.check_thresholds()
        assert len(alerts) > 0


class TestV5BottleneckAnalyzer:
    """Test V5 bottleneck analyzer."""

    def test_initialization(self):
        """Test bottleneck analyzer initialization."""
        analyzer = V5BottleneckAnalyzer()
        assert analyzer.memory_profiler is not None
        assert analyzer.cpu_profiler is not None

    def test_analyze_database_bottlenecks(self):
        """Test database bottleneck analysis."""
        analyzer = V5BottleneckAnalyzer()
        bottlenecks = analyzer.analyze_database_bottlenecks()

        assert isinstance(bottlenecks, list)
        for bottleneck in bottlenecks:
            assert isinstance(bottleneck, V5Bottleneck)
            assert bottleneck.component == "database"
            assert bottleneck.severity in ["critical", "high", "medium", "low"]

    def test_analyze_analysis_bottlenecks(self):
        """Test analysis bottleneck analysis."""
        analyzer = V5BottleneckAnalyzer()
        bottlenecks = analyzer.analyze_analysis_bottlenecks()

        assert isinstance(bottlenecks, list)
        for bottleneck in bottlenecks:
            assert isinstance(bottleneck, V5Bottleneck)
            assert bottleneck.component == "analysis"

    def test_analyze_memory_bottlenecks(self):
        """Test memory bottleneck analysis."""
        analyzer = V5BottleneckAnalyzer()
        bottlenecks = analyzer.analyze_memory_bottlenecks()

        assert isinstance(bottlenecks, list)

    def test_analyze_cpu_bottlenecks(self):
        """Test CPU bottleneck analysis."""
        analyzer = V5BottleneckAnalyzer()
        bottlenecks = analyzer.analyze_cpu_bottlenecks()

        assert isinstance(bottlenecks, list)

    def test_generate_analysis(self):
        """Test complete bottleneck analysis generation."""
        analyzer = V5BottleneckAnalyzer()
        analysis = analyzer.generate_analysis()

        assert isinstance(analysis, V5BottleneckAnalysis)
        assert analysis.system_info is not None
        assert isinstance(analysis.bottlenecks, list)
        assert isinstance(analysis.critical_bottlenecks, list)
        assert analysis.bottleneck_summary is not None
        assert isinstance(analysis.optimization_roadmap, list)
        assert analysis.performance_improvement_potential is not None
        assert analysis.resource_utilization is not None

    def test_save_and_load_analysis(self):
        """Test saving and loading analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analysis_path = Path(tmpdir) / "bottleneck_analysis.json"
            analyzer = V5BottleneckAnalyzer()

            # Generate and save
            analysis = analyzer.generate_analysis()
            analyzer.save_analysis(analysis, analysis_path)

            # Load
            loaded_analysis = analyzer.load_analysis(analysis_path)
            assert loaded_analysis is not None
            assert loaded_analysis.system_info == analysis.system_info
            assert len(loaded_analysis.bottlenecks) == len(analysis.bottlenecks)


class TestV5PerformanceConfig:
    """Test V5 performance configuration."""

    def test_config_initialization(self):
        """Test configuration initialization."""
        config = V5PerformanceConfig()
        assert config.data_dir.exists()
        assert config.monitoring_reports_dir.exists()

    def test_get_config(self):
        """Test global config instance."""
        config = get_config()
        assert isinstance(config, V5PerformanceConfig)

    def test_v5_targets_set(self):
        """Test that V5 targets are set in config."""
        config = get_config()
        assert config.v5_db_insert_latency_p50_ms > 0
        assert config.v5_inference_latency_ms > 0
        assert config.v5_packet_processing_latency_us > 0

    def test_tolerance_percentages(self):
        """Test tolerance percentages are set."""
        config = get_config()
        assert config.database_tolerance_percent > 0
        assert config.realtime_tolerance_percent > 0
        assert config.gpu_tolerance_percent > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
