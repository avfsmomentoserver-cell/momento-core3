#!/usr/bin/env python3
"""V5 Performance Baseline Runner.

Comprehensive script to run V5 performance baselines, generate reports,
and establish performance targets aligned with V5 specifications.

Usage:
    python scripts/run_v5_baseline.py --category all
    python scripts/run_v5_baseline.py --category database
    python scripts/run_v5_baseline.py --regression-check
    python scripts/run_v5_baseline.py --capacity-plan
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from performance.v5_baseline import V5BaselineRunner, V5PerformanceTargets
from performance.v5_regression import V5RegressionTester
from performance.v5_capacity import V5CapacityPlanner
from performance.v5_monitoring import V5PerformanceMonitor, RealtimeMetricsCollector
from performance.v5_bottleneck import V5BottleneckAnalyzer
from performance.v5_performance_config import get_config


def run_baseline(category: str = "all", output_path: str = None) -> dict:
    """Run V5 performance baseline tests."""
    print("=" * 80)
    print("V5 Performance Baseline Runner")
    print("=" * 80)
    print()

    config = get_config()
    storage_path = Path(output_path) if output_path else config.baseline_path

    runner = V5BaselineRunner(storage_path=storage_path)

    print(f"Running baseline for category: {category}")
    print(f"Storage path: {storage_path}")
    print()

    # Generate report
    report = runner.generate_report(category=category)

    # Print summary
    print("\n" + "=" * 80)
    print("BASELINE SUMMARY")
    print("=" * 80)
    print(f"Overall Score: {report.overall_score:.2f}/100")
    print(f"V5 Readiness: {report.v5_readiness}")
    print(f"Total Benchmarks: {len(report.benchmarks)}")
    print(f"Critical Gaps: {len(report.critical_gaps)}")
    print()

    if report.critical_gaps:
        print("CRITICAL GAPS:")
        for gap in report.critical_gaps:
            print(f"  - {gap}")
        print()

    if report.recommendations:
        print("RECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  - {rec}")
        print()

    # Print benchmark results by category
    categories = {}
    for benchmark in report.benchmarks:
        if benchmark.category not in categories:
            categories[benchmark.category] = []
        categories[benchmark.category].append(benchmark)

    print("BENCHMARK RESULTS BY CATEGORY:")
    for cat, benchmarks in categories.items():
        print(f"\n{cat.upper()}:")
        for b in benchmarks:
            status = "✓" if b.achieved else "✗"
            print(f"  {status} {b.metric_name}: {b.measured_value:.3f} {b.unit} "
                  f"(target: {b.target_value:.3f} {b.unit}, gap: {b.gap_percent:.1f}%)")

    print("\n" + "=" * 80)
    print("CAPACITY METRICS:")
    print("=" * 80)
    for key, value in report.capacity_metrics.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("SCALING PROJECTIONS:")
    print("=" * 80)
    for key, value in report.scaling_projections.items():
        print(f"  {key}: {value}")

    return {
        "overall_score": report.overall_score,
        "v5_readiness": report.v5_readiness,
        "critical_gaps_count": len(report.critical_gaps),
        "benchmarks_count": len(report.benchmarks),
    }


def run_regression_check() -> dict:
    """Run regression check against baseline."""
    print("=" * 80)
    print("V5 Performance Regression Check")
    print("=" * 80)
    print()

    config = get_config()
    tester = V5RegressionTester(
        baseline_path=config.baseline_path,
        history_path=config.regression_history_path
    )

    print("Loading baseline...")
    baseline = tester.load_baseline()

    if not baseline:
        print("ERROR: No baseline found. Run baseline first with --baseline")
        return {"error": "no_baseline"}

    print(f"Baseline timestamp: {baseline.timestamp}")
    print()

    print("Running current benchmark...")
    current = tester.run_current_benchmark()
    print(f"Current timestamp: {current.timestamp}")
    print()

    # Detect regressions
    print("Detecting regressions...")
    alerts = tester.detect_regressions(baseline, current)

    # Detect improvements
    print("Detecting improvements...")
    improvements = tester.detect_improvements(baseline, current)

    # Generate report
    report = tester.generate_regression_report(baseline, current)

    # Print summary
    print("\n" + "=" * 80)
    print("REGRESSION SUMMARY")
    print("=" * 80)
    print(f"Baseline: {baseline.timestamp}")
    print(f"Current: {current.timestamp}")
    print(f"Duration: {report.duration_hours:.2f} hours")
    print(f"Total Metrics: {report.total_metrics}")
    print(f"Regressed: {report.regressed_metrics}")
    print(f"Improved: {report.improved_metrics}")
    print(f"Stable: {report.stable_metrics}")
    print()

    if alerts:
        print("REGRESSION ALERTS:")
        for alert in alerts:
            print(f"  [{alert.severity.upper()}] {alert.metric_name}")
            print(f"    Current: {alert.current_value:.3f}")
            print(f"    Baseline: {alert.baseline_value:.3f}")
            print(f"    Degradation: {alert.degradation_percent:.1f}%")
            print(f"    Threshold: {alert.threshold_percent:.1f}%")
        print()

    if improvements:
        print("IMPROVEMENTS:")
        for imp in improvements:
            print(f"  ✓ {imp['metric_name']}: {imp['improvement_percent']:.1f}% improvement")
        print()

    print(report.summary)
    print()

    # Save to history
    tester.save_to_history(report)

    return {
        "regressed_metrics": report.regressed_metrics,
        "improved_metrics": report.improved_metrics,
        "stable_metrics": report.stable_metrics,
        "has_critical_regressions": any(a.severity == "critical" for a in alerts),
    }


def run_capacity_plan() -> dict:
    """Run capacity planning analysis."""
    print("=" * 80)
    print("V5 Capacity Planning")
    print("=" * 80)
    print()

    config = get_config()

    # Load baseline
    runner = V5BaselineRunner(storage_path=config.baseline_path)
    baseline = runner.load_report()

    # Create capacity planner
    planner = V5CapacityPlanner(baseline_report=baseline)

    # Assess current capacity
    print("Assessing current capacity...")
    current = planner.assess_current_capacity()

    # Identify gaps
    print("Identifying capacity gaps...")
    gaps = planner.identify_gaps(current)

    # Generate recommendations
    print("Generating recommendations...")
    recommendations = planner.generate_recommendations(gaps)

    # Generate complete plan
    plan = planner.generate_capacity_plan()

    # Print summary
    print("\n" + "=" * 80)
    print("CAPACITY ASSESSMENT")
    print("=" * 80)
    for key, value in current.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("CAPACITY GAPS")
    print("=" * 80)
    if gaps:
        for gap in gaps:
            print(f"  {gap['resource_type']}:")
            print(f"    Current: {gap['current_value']:.2f} {gap['unit']}")
            print(f"    Required: {gap['minimum_required']:.2f} {gap['unit']}")
            print(f"    Recommended: {gap['recommended']:.2f} {gap['unit']}")
            print(f"    Gap: {gap['gap']:.2f} ({gap['gap_percent']:.1f}%)")
    else:
        print("  No capacity gaps detected!")

    print("\n" + "=" * 80)
    print("SCALING RECOMMENDATIONS")
    print("=" * 80)
    for rec in recommendations:
        print(f"  {rec.component}:")
        print(f"    Priority: {rec.priority}")
        print(f"    Scaling Type: {rec.scaling_type}")
        print(f"    Scaling Factor: {rec.scaling_factor:.2f}x")
        print(f"    Current: {rec.current_capacity:.2f}")
        print(f"    Required: {rec.required_capacity:.2f}")
        if rec.estimated_cost:
            print(f"    Estimated Cost: {rec.estimated_cost}")

    print("\n" + "=" * 80)
    print("INFRASTRUCTURE NEEDS")
    print("=" * 80)
    for need in plan.infrastructure_needs:
        print(f"  - {need}")

    print("\n" + "=" * 80)
    print("TIMELINE")
    print("=" * 80)
    for phase, date in plan.timeline.items():
        print(f"  {phase}: {date}")

    # Save plan
    planner.save_plan(plan, config.capacity_plan_path)

    return {
        "gaps_count": len(gaps),
        "recommendations_count": len(recommendations),
        "infrastructure_needs_count": len(plan.infrastructure_needs),
    }


def run_bottleneck_analysis() -> dict:
    """Run V5 bottleneck analysis."""
    print("=" * 80)
    print("V5 Bottleneck Analysis")
    print("=" * 80)
    print()

    config = get_config()
    analyzer = V5BottleneckAnalyzer()

    # Generate analysis
    analysis = analyzer.generate_analysis()

    # Print summary
    print("\n" + "=" * 80)
    print("BOTTLENECK SUMMARY")
    print("=" * 80)
    print(f"Total Bottlenecks: {analysis.bottleneck_summary['total_bottlenecks']}")
    print(f"Critical: {analysis.bottleneck_summary['critical_bottlenecks']}")
    print(f"High: {analysis.bottleneck_summary['high_bottlenecks']}")
    print(f"Medium: {analysis.bottleneck_summary['medium_bottlenecks']}")
    print(f"Low: {analysis.bottleneck_summary['low_bottlenecks']}")
    print()

    print("BY COMPONENT:")
    for component, count in analysis.bottleneck_summary['by_component'].items():
        print(f"  {component}: {count}")

    print("\nBY IMPACT AREA:")
    for impact, count in analysis.bottleneck_summary['by_impact_area'].items():
        print(f"  {impact}: {count}")

    print("\n" + "=" * 80)
    print("CRITICAL BOTTLENECKS")
    print("=" * 80)
    if analysis.critical_bottlenecks:
        for bottleneck in analysis.critical_bottlenecks:
            print(f"\n{bottleneck.component.upper()} - {bottleneck.metric_name}")
            print(f"  Current: {bottleneck.current_value:.3f}")
            print(f"  Target: {bottleneck.target_value:.3f}")
            print(f"  Gap: {bottleneck.gap_percent:.1f}%")
            print(f"  Description: {bottleneck.description}")
            print(f"  Recommendation: {bottleneck.recommendation}")
            print(f"  Estimated Effort: {bottleneck.estimated_fix_effort}")
    else:
        print("No critical bottlenecks detected!")

    print("\n" + "=" * 80)
    print("OPTIMIZATION ROADMAP (Top 10)")
    print("=" * 80)
    for i, item in enumerate(analysis.optimization_roadmap, 1):
        print(f"\n{i}. [{item['priority'].upper()}] {item['component']} - {item['metric']}")
        print(f"   Gap: {item['gap_percent']:.1f}%")
        print(f"   Recommendation: {item['recommendation']}")
        print(f"   Estimated Effort: {item['estimated_effort']}")

    print("\n" + "=" * 80)
    print("PERFORMANCE IMPROVEMENT POTENTIAL")
    print("=" * 80)
    for metric, potential in analysis.performance_improvement_potential.items():
        print(f"  {metric}: {potential:.1f}%")

    print("\n" + "=" * 80)
    print("RESOURCE UTILIZATION")
    print("=" * 80)
    for resource, value in analysis.resource_utilization.items():
        print(f"  {resource}: {value}")

    # Save analysis
    analyzer.save_analysis(analysis, config.bottleneck_analysis_path)

    return {
        "total_bottlenecks": analysis.bottleneck_summary['total_bottlenecks'],
        "critical_bottlenecks": analysis.bottleneck_summary['critical_bottlenecks'],
        "performance_improvement_potential": analysis.performance_improvement_potential,
    }


def run_monitoring_demo(duration_seconds: int = 60) -> dict:
    """Run a demo of real-time monitoring."""
    print("=" * 80)
    print("V5 Real-time Monitoring Demo")
    print("=" * 80)
    print()

    import asyncio
    import time

    collector = RealtimeMetricsCollector(window_size=1000)
    monitor = V5PerformanceMonitor(collector=collector)

    print(f"Monitoring for {duration_seconds} seconds...")
    print("Press Ctrl+C to stop early")
    print()

    async def monitoring_loop():
        from performance.v5_monitoring import RealtimeMetric

        start_time = time.time()
        metrics_collected = 0

        while time.time() - start_time < duration_seconds:
            # Simulate metrics
            metrics = [
                RealtimeMetric("db_insert_latency", 0.5 + (time.time() % 5) * 0.1, "ms"),
                RealtimeMetric("db_select_latency", 0.3 + (time.time() % 3) * 0.05, "ms"),
                RealtimeMetric("analysis_latency", 50.0 + (time.time() % 10) * 5.0, "ms"),
                RealtimeMetric("api_latency", 15.0 + (time.time() % 8) * 2.0, "ms"),
                RealtimeMetric("memory_usage_mb", 512.0 + (time.time() % 20) * 10.0, "MB"),
                RealtimeMetric("cpu_usage_percent", 30.0 + (time.time() % 15) * 3.0, "%"),
            ]

            for metric in metrics:
                await collector.record_metric(metric)
                metrics_collected += 1

            # Check thresholds
            alerts = await monitor.check_thresholds()
            if alerts:
                for alert in alerts:
                    print(f"[{alert.severity.upper()}] {alert.metric_name}: {alert.current_value:.2f}")

            # Print progress
            elapsed = time.time() - start_time
            remaining = duration_seconds - elapsed
            if int(elapsed) % 10 == 0:
                print(f"Progress: {elapsed:.0f}s / {duration_seconds}s ({metrics_collected} metrics)")

            await asyncio.sleep(1.0)

        # Generate report
        report = await monitor.generate_report(duration_seconds)
        return report, metrics_collected

    try:
        report, metrics_count = asyncio.run(monitoring_loop())
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        report = None
        metrics_count = 0

    if report:
        print("\n" + "=" * 80)
        print("MONITORING REPORT")
        print("=" * 80)
        print(f"Duration: {report.duration_seconds:.2f}s")
        print(f"Metrics Collected: {report.metrics_collected}")
        print(f"Alerts Triggered: {report.alerts_triggered}")
        print(f"System Health: {report.system_health}")
        print()

        print("METRIC STATISTICS:")
        for metric_name, stats in report.metric_statistics.items():
            print(f"  {metric_name}:")
            print(f"    Count: {stats['count']}")
            print(f"    Mean: {stats['mean']:.3f}")
            print(f"    P50: {stats['p50']:.3f}")
            print(f"    P95: {stats['p95']:.3f}")
            print(f"    P99: {stats['p99']:.3f}")

        if report.alerts:
            print("\nALERTS:")
            for alert in report.alerts:
                print(f"  [{alert.severity.upper()}] {alert.metric_name}: {alert.current_value:.2f}")

    return {
        "metrics_collected": metrics_count,
        "alerts_triggered": report.alerts_triggered if report else 0,
        "system_health": report.system_health if report else "unknown",
    }


def main():
    parser = argparse.ArgumentParser(description="V5 Performance Baseline Runner")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run baseline tests"
    )
    parser.add_argument(
        "--category",
        choices=["all", "database", "realtime", "gpu", "api", "analysis"],
        default="all",
        help="Category to benchmark"
    )
    parser.add_argument(
        "--regression-check",
        action="store_true",
        help="Run regression check against baseline"
    )
    parser.add_argument(
        "--capacity-plan",
        action="store_true",
        help="Run capacity planning analysis"
    )
    parser.add_argument(
        "--monitoring-demo",
        action="store_true",
        help="Run real-time monitoring demo"
    )
    parser.add_argument(
        "--monitoring-duration",
        type=int,
        default=60,
        help="Duration for monitoring demo (seconds)"
    )
    parser.add_argument(
        "--bottleneck-analysis",
        action="store_true",
        help="Run bottleneck analysis"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for baseline report"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all checks (baseline, regression, capacity, bottleneck)"
    )

    args = parser.parse_args()

    if args.all:
        print("Running complete V5 performance analysis...")
        print()

        # Run baseline
        baseline_result = run_baseline(args.category, args.output)
        print()

        # Run regression check
        regression_result = run_regression_check()
        print()

        # Run capacity plan
        capacity_result = run_capacity_plan()
        print()

        # Run bottleneck analysis
        bottleneck_result = run_bottleneck_analysis()
        print()

        print("=" * 80)
        print("COMPLETE ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"Baseline Score: {baseline_result['overall_score']:.2f}/100")
        print(f"V5 Readiness: {baseline_result['v5_readiness']}")
        print(f"Regressed Metrics: {regression_result['regressed_metrics']}")
        print(f"Improved Metrics: {regression_result['improved_metrics']}")
        print(f"Capacity Gaps: {capacity_result['gaps_count']}")
        print(f"Total Bottlenecks: {bottleneck_result['total_bottlenecks']}")
        print(f"Critical Bottlenecks: {bottleneck_result['critical_bottlenecks']}")
        print()

        return 0

    if args.baseline:
        result = run_baseline(args.category, args.output)
        return 0 if result['overall_score'] >= 50 else 1

    if args.regression_check:
        result = run_regression_check()
        return 1 if result['has_critical_regressions'] else 0

    if args.capacity_plan:
        result = run_capacity_plan()
        return 0

    if args.monitoring_demo:
        result = run_monitoring_demo(args.monitoring_duration)
        return 0

    if args.bottleneck_analysis:
        result = run_bottleneck_analysis()
        return 0

    # Default: run baseline
    result = run_baseline(args.category, args.output)
    return 0 if result['overall_score'] >= 50 else 1


if __name__ == "__main__":
    sys.exit(main())
