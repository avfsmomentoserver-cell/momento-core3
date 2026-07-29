"""V5 Capacity Planning and Scaling Analysis.

Analyzes current capacity against V5 requirements and provides scaling recommendations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from .v5_baseline import V5BaselineReport, V5PerformanceTargets


@dataclass
class CapacityRequirement:
    """Capacity requirement for V5."""
    resource_type: str  # cpu, memory, storage, network, gpu
    minimum_value: float
    recommended_value: float
    unit: str
    description: str


@dataclass
class ScalingRecommendation:
    """Scaling recommendation."""
    component: str
    current_capacity: float
    required_capacity: float
    scaling_factor: float
    scaling_type: str  # horizontal, vertical, both
    priority: str  # critical, high, medium, low
    estimated_cost: Optional[str] = None
    implementation_steps: List[str] = field(default_factory=list)


@dataclass
class CapacityPlan:
    """Complete capacity plan."""
    current_assessment: Dict[str, Any]
    v5_requirements: List[CapacityRequirement]
    gaps: List[Dict[str, Any]]
    recommendations: List[ScalingRecommendation]
    infrastructure_needs: List[str]
    migration_strategy: Dict[str, Any]
    cost_estimates: Dict[str, Any]
    timeline: Dict[str, str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))


class V5CapacityPlanner:
    """Plan capacity for V5 transformation."""

    # V5 capacity requirements based on specifications
    V5_REQUIREMENTS = [
        CapacityRequirement(
            resource_type="cpu",
            minimum_value=16,
            recommended_value=32,
            unit="cores",
            description="CPU cores for backend processing"
        ),
        CapacityRequirement(
            resource_type="memory",
            minimum_value=32,
            recommended_value=64,
            unit="GB",
            description="RAM for database cache and application"
        ),
        CapacityRequirement(
            resource_type="storage",
            minimum_value=500,
            recommended_value=1000,
            unit="GB",
            description="Storage for database and logs"
        ),
        CapacityRequirement(
            resource_type="network",
            minimum_value=10,
            recommended_value=25,
            unit="Gbps",
            description="Network bandwidth for real-time data"
        ),
        CapacityRequirement(
            resource_type="gpu",
            minimum_value=1,
            recommended_value=2,
            unit="cards",
            description="GPU cards for ML inference (A100/H100)"
        ),
        CapacityRequirement(
            resource_type="database_connections",
            minimum_value=100,
            recommended_value=500,
            unit="connections",
            description="Database connection pool size"
        ),
        CapacityRequirement(
            resource_type="redis_memory",
            minimum_value=8,
            recommended_value=16,
            unit="GB",
            description="Redis memory for caching"
        ),
    ]

    def __init__(self, baseline_report: Optional[V5BaselineReport] = None):
        self.baseline_report = baseline_report

    def assess_current_capacity(self) -> Dict[str, Any]:
        """Assess current system capacity."""
        import platform
        import os

        assessment = {
            "cpu_cores": os.cpu_count() or 1,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

        # Memory
        try:
            import psutil
            assessment["memory_gb"] = psutil.virtual_memory().total / 1024 / 1024 / 1024
            assessment["memory_available_gb"] = psutil.virtual_memory().available / 1024 / 1024 / 1024
        except ImportError:
            assessment["memory_gb"] = 0
            assessment["memory_available_gb"] = 0

        # GPU
        try:
            import pynvml
            pynvml.nvmlInit()
            gpu_count = pynvml.nvmlDeviceGetCount()
            assessment["gpu_count"] = gpu_count
            assessment["gpu_memory_gb"] = 0
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                assessment["gpu_memory_gb"] += memory.total / 1024 / 1024 / 1024
            pynvml.nvmlShutdown()
        except Exception:
            assessment["gpu_count"] = 0
            assessment["gpu_memory_gb"] = 0

        # Storage
        try:
            import shutil
            assessment["storage_gb"] = shutil.disk_usage("/").total / 1024 / 1024 / 1024
            assessment["storage_available_gb"] = shutil.disk_usage("/").free / 1024 / 1024 / 1024
        except Exception:
            assessment["storage_gb"] = 0
            assessment["storage_available_gb"] = 0

        # Performance from baseline
        if self.baseline_report:
            assessment["db_throughput"] = self.baseline_report.capacity_metrics.get("current_db_throughput", 0)
            assessment["analysis_throughput"] = self.baseline_report.capacity_metrics.get("current_analysis_throughput", 0)
            assessment["max_concurrent_users"] = self.baseline_report.capacity_metrics.get("max_concurrent_users", 0)
        else:
            assessment["db_throughput"] = 0
            assessment["analysis_throughput"] = 0
            assessment["max_concurrent_users"] = 0

        return assessment

    def identify_gaps(self, current: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify capacity gaps against V5 requirements."""
        gaps = []

        for req in self.V5_REQUIREMENTS:
            current_value = 0.0

            if req.resource_type == "cpu":
                current_value = current.get("cpu_cores", 0)
            elif req.resource_type == "memory":
                current_value = current.get("memory_gb", 0)
            elif req.resource_type == "storage":
                current_value = current.get("storage_gb", 0)
            elif req.resource_type == "gpu":
                current_value = current.get("gpu_count", 0)
            elif req.resource_type == "database_connections":
                current_value = current.get("db_throughput", 0) / 100  # Estimate
            elif req.resource_type == "redis_memory":
                current_value = current.get("memory_gb", 0) * 0.25  # Allocate 25% to Redis

            gap = req.minimum_value - current_value
            gap_percent = (gap / req.minimum_value * 100) if req.minimum_value > 0 else 0

            if gap > 0:
                gaps.append({
                    "resource_type": req.resource_type,
                    "current_value": current_value,
                    "minimum_required": req.minimum_value,
                    "recommended": req.recommended_value,
                    "gap": gap,
                    "gap_percent": gap_percent,
                    "unit": req.unit,
                    "description": req.description,
                })

        return gaps

    def generate_recommendations(self, gaps: List[Dict[str, Any]]) -> List[ScalingRecommendation]:
        """Generate scaling recommendations."""
        recommendations = []

        for gap in gaps:
            resource_type = gap["resource_type"]
            current = gap["current_value"]
            required = gap["recommended"]
            scaling_factor = required / current if current > 0 else required

            if resource_type in ["cpu", "memory", "storage"]:
                scaling_type = "vertical"
                priority = "critical" if gap["gap_percent"] > 50 else "high"
            elif resource_type == "gpu":
                scaling_type = "vertical"
                priority = "critical"
            elif resource_type in ["database_connections", "redis_memory"]:
                scaling_type = "horizontal"
                priority = "high"
            else:
                scaling_type = "both"
                priority = "medium"

            # Implementation steps
            steps = []
            if resource_type == "cpu":
                steps = [
                    "Upgrade to CPU with higher core count",
                    "Ensure CPU supports required instruction sets",
                    "Consider hyper-threading for parallel processing",
                ]
            elif resource_type == "memory":
                steps = [
                    "Install additional RAM modules",
                    "Configure PostgreSQL shared_buffers",
                    "Increase Redis maxmemory configuration",
                ]
            elif resource_type == "gpu":
                steps = [
                    "Install NVIDIA A100 or H100 GPU",
                    "Install CUDA 12.2+ drivers",
                    "Configure TensorRT 8.6+",
                ]
            elif resource_type == "storage":
                steps = [
                    "Add SSD storage for database",
                    "Configure RAID for redundancy",
                    "Set up automated backups",
                ]
            elif resource_type == "database_connections":
                steps = [
                    "Implement connection pooling",
                    "Configure PostgreSQL max_connections",
                    "Add read replicas for scaling",
                ]
            elif resource_type == "redis_memory":
                steps = [
                    "Deploy Redis Cluster",
                    "Configure maxmemory-policy",
                    "Set up Redis persistence",
                ]

            recommendations.append(ScalingRecommendation(
                component=resource_type,
                current_capacity=current,
                required_capacity=required,
                scaling_factor=scaling_factor,
                scaling_type=scaling_type,
                priority=priority,
                implementation_steps=steps,
            ))

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))

        return recommendations

    def generate_infrastructure_needs(self, recommendations: List[ScalingRecommendation]) -> List[str]:
        """Generate infrastructure needs list."""
        needs = []

        for rec in recommendations:
            if rec.component == "gpu":
                needs.append("NVIDIA A100 (80GB HBM2e) or H100 (80GB HBM3) GPU")
                needs.append("CUDA 12.2+ toolkit")
                needs.append("TensorRT 8.6+ for model optimization")
            elif rec.component == "cpu":
                needs.append("Multi-core CPU (32+ cores recommended)")
                needs.append("CPU with AVX-512 support for vectorization")
            elif rec.component == "memory":
                needs.append("64GB+ RAM for database cache and ML models")
            elif rec.component == "storage":
                needs.append("NVMe SSD storage for low-latency database access")
                needs.append("1TB+ storage for time-series data")
            elif rec.component == "database_connections":
                needs.append("PostgreSQL 15+ with TimescaleDB extension")
                needs.append("Connection pooling with PgBouncer")
            elif rec.component == "redis_memory":
                needs.append("Redis 7.2+ Cluster with 6 nodes (3 master, 3 replica)")
                needs.append("16GB+ Redis memory for caching layer")

        # Add V5-specific infrastructure
        needs.extend([
            "DPDK 23.07+ for kernel-bypass networking",
            "FPGA acceleration (Xilinx Alveo UL3524) for critical path",
            "Kubernetes 1.28+ for container orchestration",
            "Prometheus + Grafana for monitoring",
            "Nginx 1.25+ with HTTP/2 and Brotli compression",
        ])

        return list(set(needs))  # Remove duplicates

    def generate_migration_strategy(self, recommendations: List[ScalingRecommendation]) -> Dict[str, Any]:
        """Generate migration strategy."""
        critical_items = [r for r in recommendations if r.priority == "critical"]
        high_items = [r for r in recommendations if r.priority == "high"]

        phases = []

        # Phase 1: Critical infrastructure
        if critical_items:
            phases.append({
                "phase": 1,
                "name": "Critical Infrastructure",
                "duration": "2-4 weeks",
                "items": [r.component for r in critical_items],
                "deliverables": [
                    "GPU infrastructure deployed",
                    "CPU and memory upgraded",
                    "PostgreSQL 15+ with TimescaleDB",
                    "Redis Cluster configured",
                ],
            })

        # Phase 2: Performance optimization
        if high_items:
            phases.append({
                "phase": 2,
                "name": "Performance Optimization",
                "duration": "2-3 weeks",
                "items": [r.component for r in high_items],
                "deliverables": [
                    "Connection pooling implemented",
                    "Caching layer optimized",
                    "Database indexing improved",
                ],
            })

        # Phase 3: Real-time stack
        phases.append({
            "phase": 3,
            "name": "Real-time Stack",
            "duration": "3-4 weeks",
            "items": ["dpdk", "fpga", "cuda"],
            "deliverables": [
                "DPDK kernel-bypass networking",
                "FPGA acceleration for critical path",
                "CUDA GPU inference pipeline",
            ],
        })

        # Phase 4: Monitoring and scaling
        phases.append({
            "phase": 4,
            "name": "Monitoring and Scaling",
            "duration": "1-2 weeks",
            "items": ["monitoring", "kubernetes"],
            "deliverables": [
                "Prometheus metrics endpoint",
                "Grafana dashboards",
                "Kubernetes HPA configured",
            ],
        })

        return {
            "total_phases": len(phases),
            "estimated_duration": "8-13 weeks",
            "phases": phases,
            "rollback_plan": "Maintain V4 infrastructure in parallel during migration",
        }

    def estimate_costs(self, recommendations: List[ScalingRecommendation]) -> Dict[str, Any]:
        """Estimate infrastructure costs (rough estimates)."""
        costs = {}

        for rec in recommendations:
            if rec.component == "gpu":
                costs["gpu_hardware"] = "$15,000 - $30,000 per A100/H100"
            elif rec.component == "cpu":
                costs["cpu_upgrade"] = "$2,000 - $5,000 for 32-core CPU"
            elif rec.component == "memory":
                costs["memory_upgrade"] = "$500 - $1,000 for 64GB RAM"
            elif rec.component == "storage":
                costs["storage_upgrade"] = "$500 - $1,000 for 1TB NVMe SSD"
            elif rec.component == "fpga":
                costs["fpga_hardware"] = "$10,000 - $20,000 per FPGA card"

        # Cloud alternatives
        costs["cloud_gpu_instance"] = "$3-5/hour for A100 instance"
        costs["cloud_cpu_instance"] = "$0.5-1/hour for 32-core instance"
        costs["monthly_estimate"] = "$2,000 - $5,000/month for cloud deployment"

        return costs

    def generate_plan(self) -> CapacityPlan:
        """Generate complete capacity plan."""
        current = self.assess_current_capacity()
        gaps = self.identify_gaps(current)
        recommendations = self.generate_recommendations(gaps)
        infrastructure_needs = self.generate_infrastructure_needs(recommendations)
        migration_strategy = self.generate_migration_strategy(recommendations)
        cost_estimates = self.estimate_costs(recommendations)

        return CapacityPlan(
            current_assessment=current,
            v5_requirements=self.V5_REQUIREMENTS,
            gaps=gaps,
            recommendations=recommendations,
            infrastructure_needs=infrastructure_needs,
            migration_strategy=migration_strategy,
            cost_estimates=cost_estimates,
            timeline={
                "start": "Immediate",
                "phase1_complete": "4 weeks",
                "phase2_complete": "7 weeks",
                "phase3_complete": "11 weeks",
                "full_migration": "13 weeks",
            },
        )

    def save_plan(self, plan: CapacityPlan, path: Optional[Path] = None) -> None:
        """Save capacity plan to file."""
        if path is None:
            path = Path(__file__).parent.parent / "data" / "v5_capacity_plan.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(plan)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def main():
    """Generate capacity plan."""
    print("Generating V5 Capacity Plan...")
    print("=" * 60)

    planner = V5CapacityPlanner()
    plan = planner.generate_plan()

    print(f"\nCurrent Assessment:")
    for key, value in plan.current_assessment.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print(f"\nCapacity Gaps:")
    for gap in plan.gaps:
        print(f"  {gap['resource_type'].upper()}:")
        print(f"    Current: {gap['current_value']:.2f} {gap['unit']}")
        print(f"    Required: {gap['minimum_required']:.2f} {gap['unit']}")
        print(f"    Gap: {gap['gap']:.2f} {gap['unit']} ({gap['gap_percent']:.1f}%)")

    print(f"\nRecommendations:")
    for rec in plan.recommendations:
        print(f"  {rec.component.upper()} [{rec.priority}]:")
        print(f"    Current: {rec.current_capacity:.2f}")
        print(f"    Required: {rec.required_capacity:.2f}")
        print(f"    Scaling Factor: {rec.scaling_factor:.2f}x")
        print(f"    Type: {rec.scaling_type}")
        print(f"    Steps:")
        for step in rec.implementation_steps:
            print(f"      - {step}")

    print(f"\nInfrastructure Needs:")
    for need in plan.infrastructure_needs:
        print(f"  - {need}")

    print(f"\nMigration Strategy:")
    print(f"  Total Phases: {plan.migration_strategy['total_phases']}")
    print(f"  Estimated Duration: {plan.migration_strategy['estimated_duration']}")
    for phase in plan.migration_strategy['phases']:
        print(f"\n  Phase {phase['phase']}: {phase['name']} ({phase['duration']})")
        for deliverable in phase['deliverables']:
            print(f"    - {deliverable}")

    print(f"\nCost Estimates:")
    for key, value in plan.cost_estimates.items():
        print(f"  {key}: {value}")

    print(f"\nTimeline:")
    for key, value in plan.timeline.items():
        print(f"  {key}: {value}")

    # Save plan
    planner.save_plan(plan)
    print(f"\nCapacity plan saved")

    return plan


if __name__ == "__main__":
    main()
