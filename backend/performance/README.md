# V5 Performance Framework

Comprehensive performance benchmarking, monitoring, and optimization framework for the Momento Core V5 transformation.

## Overview

The V5 Performance Framework provides tools to establish performance baselines, detect regressions, plan capacity, monitor real-time metrics, and analyze bottlenecks aligned with V5 specifications including CUDA, DPDK, FPGA, and ultra-low latency requirements.

## Components

### 1. V5 Baseline Runner (`v5_baseline.py`)

Establishes performance baselines against V5 specifications.

**Features:**
- Database performance benchmarks (PostgreSQL 15+ targets)
- Real-time processing benchmarks (DPDK, FPGA targets)
- GPU/AI benchmarks (CUDA, TensorRT targets)
- API performance benchmarks (FastAPI, uvloop targets)
- Analysis engine benchmarks

**Key Classes:**
- `V5BaselineRunner`: Executes benchmarks and generates reports
- `V5PerformanceTargets`: Defines V5 performance targets
- `V5BenchmarkResult`: Single benchmark result
- `V5BaselineReport`: Complete baseline report

**V5 Performance Targets:**
- Database: Insert P50 < 1ms, P99 < 5ms, Throughput > 10k ops/sec
- Real-time: Packet processing < 2μs, FIX parsing < 14ns
- GPU: Inference < 1ms, Throughput > 1000 inferences/sec
- API: P50 < 10ms, P99 < 50ms, Throughput > 5k req/sec
- Analysis: 500 rounds < 100ms

### 2. V5 Regression Tester (`v5_regression.py`)

Tracks performance over time and detects regressions.

**Features:**
- Automated regression detection
- Performance improvement tracking
- Trend analysis over time
- Configurable thresholds per metric
- Historical data management

**Key Classes:**
- `V5RegressionTester`: Runs regression tests
- `RegressionThreshold`: Defines regression detection thresholds
- `RegressionAlert`: Regression alert
- `RegressionReport`: Complete regression report

### 3. V5 Capacity Planner (`v5_capacity.py`)

Analyzes current capacity and provides scaling recommendations.

**Features:**
- Current capacity assessment
- Gap analysis against V5 requirements
- Scaling recommendations (horizontal/vertical)
- Infrastructure needs assessment
- Migration strategy and timeline

**Key Classes:**
- `V5CapacityPlanner`: Generates capacity plans
- `CapacityRequirement`: V5 capacity requirement
- `ScalingRecommendation`: Scaling recommendation
- `CapacityPlan`: Complete capacity plan

**V5 Capacity Requirements:**
- CPU: 16-32 cores
- Memory: 32-64 GB
- Storage: 500-1000 GB
- Network: 10-25 Gbps
- GPU: 1-2 cards (A100/H100)
- Database connections: 100-500
- Redis memory: 8-16 GB

### 4. V5 Performance Monitor (`v5_monitoring.py`)

Real-time performance monitoring and alerting.

**Features:**
- Real-time metrics collection
- Threshold-based alerting
- Rolling window statistics
- System health assessment
- Monitoring report generation

**Key Classes:**
- `V5PerformanceMonitor`: Real-time monitoring
- `RealtimeMetricsCollector`: Metrics collection
- `RealtimeMetric`: Single metric
- `MetricThreshold`: Alert threshold
- `PerformanceAlert`: Performance alert

**Monitored Metrics:**
- Database latency (insert, select)
- Analysis latency
- API latency
- Memory usage
- CPU usage

### 5. V5 Bottleneck Analyzer (`v5_bottleneck.py`)

Advanced bottleneck analysis for V5 transformation.

**Features:**
- Database bottleneck analysis
- Analysis engine bottleneck analysis
- Memory bottleneck detection
- CPU hotspot profiling
- GPU availability check
- Network/DPDK availability check
- FPGA availability check
- Optimization roadmap generation

**Key Classes:**
- `V5BottleneckAnalyzer`: Analyzes bottlenecks
- `V5Bottleneck`: Single bottleneck
- `V5BottleneckAnalysis`: Complete analysis

### 6. V5 Performance Config (`v5_performance_config.py`)

Centralized configuration for the performance framework.

**Features:**
- Storage path configuration
- Benchmark settings
- Monitoring settings
- Regression testing settings
- V5 target thresholds
- Alert thresholds

**Key Classes:**
- `V5PerformanceConfig`: Configuration object
- `get_config()`: Get global config instance

## Usage

### Quick Start

Run the complete V5 performance analysis:

```bash
cd backend
python scripts/run_v5_baseline.py --all
```

### Individual Components

**Run baseline tests:**
```bash
python scripts/run_v5_baseline.py --baseline --category all
python scripts/run_v5_baseline.py --baseline --category database
python scripts/run_v5_baseline.py --baseline --category gpu
```

**Run regression check:**
```bash
python scripts/run_v5_baseline.py --regression-check
```

**Run capacity planning:**
```bash
python scripts/run_v5_baseline.py --capacity-plan
```

**Run bottleneck analysis:**
```bash
python scripts/run_v5_baseline.py --bottleneck-analysis
```

**Run monitoring demo:**
```bash
python scripts/run_v5_baseline.py --monitoring-demo --monitoring-duration 60
```

### Programmatic Usage

```python
from performance.v5_baseline import V5BaselineRunner
from performance.v5_regression import V5RegressionTester
from performance.v5_capacity import V5CapacityPlanner
from performance.v5_monitoring import V5PerformanceMonitor
from performance.v5_bottleneck import V5BottleneckAnalyzer
from performance.v5_performance_config import get_config

# Get configuration
config = get_config()

# Run baseline
runner = V5BaselineRunner(storage_path=config.baseline_path)
report = runner.generate_report(category="all")
print(f"V5 Readiness: {report.v5_readiness}")
print(f"Overall Score: {report.overall_score}/100")

# Check regressions
tester = V5RegressionTester(baseline_path=config.baseline_path)
baseline = tester.load_baseline()
current = runner.generate_report()
alerts = tester.detect_regressions(baseline, current)

# Plan capacity
planner = V5CapacityPlanner(baseline_report=baseline)
capacity_plan = planner.generate_capacity_plan()

# Analyze bottlenecks
analyzer = V5BottleneckAnalyzer()
bottleneck_analysis = analyzer.generate_analysis()
```

## Output Files

All performance data is stored in `backend/data/`:

- `v5_baseline.json`: Latest baseline report
- `v5_regression_history.json`: Historical regression data
- `v5_capacity_plan.json`: Capacity planning report
- `v5_bottleneck_analysis.json`: Bottleneck analysis report
- `monitoring_reports/`: Real-time monitoring reports

## V5 Readiness Assessment

The framework assesses V5 readiness based on:

1. **Overall Score** (0-100): Weighted average of all benchmark results
2. **V5 Readiness Level**:
   - `ready`: Score >= 80, all critical targets met
   - `partial`: Score >= 50, some gaps identified
   - `not_ready`: Score < 50, significant gaps

3. **Critical Gaps**: Metrics that exceed tolerance thresholds
4. **Recommendations**: Specific actions to achieve V5 targets

## Performance Categories

### Database
- PostgreSQL 15+ optimizations
- Connection pooling
- Query optimization
- Indexing strategies

### Real-time
- DPDK kernel-bypass networking
- FPGA acceleration (FIX parsing, orderbook updates)
- Lock-free data structures
- Ultra-low latency (< 2μs)

### GPU/AI
- CUDA 12.2+ support
- TensorRT optimization
- Mixed precision (FP16)
- Model quantization

### API
- FastAPI with uvloop
- Response caching
- Async database drivers
- Connection pooling

### Analysis
- Pure function optimization
- Memoization
- Vectorized operations
- Parallel processing

## Integration with CI/CD

Add to your CI pipeline:

```yaml
- name: Run V5 Performance Baseline
  run: |
    cd backend
    python scripts/run_v5_baseline.py --baseline

- name: Check for Regressions
  run: |
    cd backend
    python scripts/run_v5_baseline.py --regression-check
```

## Monitoring in Production

Deploy the monitoring component:

```python
import asyncio
from performance.v5_monitoring import V5PerformanceMonitor, RealtimeMetricsCollector

async def monitor_production():
    collector = RealtimeMetricsCollector(window_size=1000)
    monitor = V5PerformanceMonitor(collector=collector)

    # Add alert callback
    def on_alert(alert):
        print(f"ALERT: {alert.metric_name} = {alert.current_value}")
        # Send to monitoring system

    monitor.add_alert_callback(on_alert)

    # Monitor continuously
    while True:
        # Record metrics from your application
        await collector.record_metric(RealtimeMetric("db_insert_latency", latency, "ms"))

        # Check thresholds
        await monitor.check_thresholds()

        await asyncio.sleep(1.0)
```

## Testing

Run the test suite:

```bash
cd backend
pytest tests/test_v5_performance.py -v
```

## Configuration

Customize performance targets in `v5_performance_config.py`:

```python
from performance.v5_performance_config import V5PerformanceConfig

config = V5PerformanceConfig(
    v5_db_insert_latency_p50_ms=0.5,  # Custom target
    v5_inference_latency_ms=0.5,  # Custom target
    database_tolerance_percent=15.0,  # Stricter tolerance
)
```

## Troubleshooting

**Baseline fails to run:**
- Ensure database is accessible
- Check write permissions for data directory
- Verify all dependencies are installed

**Regression check fails:**
- Ensure baseline exists (run baseline first)
- Check baseline file path configuration

**Capacity planning shows no gaps:**
- This is expected if system meets V5 requirements
- Verify current capacity assessment is accurate

**Bottleneck analysis shows no bottlenecks:**
- System may be well-optimized
- Check if GPU/FPGA detection is working
- Verify benchmark targets are appropriate

## Contributing

When adding new benchmarks:

1. Add target to `V5PerformanceTargets`
2. Implement benchmark method in `V5BaselineRunner`
3. Add regression threshold in `V5RegressionTester`
4. Update configuration in `V5PerformanceConfig`
5. Add tests in `test_v5_performance.py`

## License

Part of the Momento Core Platform project.
