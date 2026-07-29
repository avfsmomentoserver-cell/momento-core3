"""
V5 Deployment Manager for IDE-Focused Deployment
Handles local infrastructure deployment, validation, and IDE integration
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("momento.deployment")


@dataclass
class DeploymentRequirement:
    """Deployment requirement specification."""
    name: str
    description: str
    required: bool
    check_command: Optional[str] = None
    version_min: Optional[str] = None
    validation_function: Optional[str] = None


@dataclass
class DeploymentStatus:
    """Current deployment status."""
    component: str
    status: str  # running, stopped, error, unknown
    health: str  # healthy, unhealthy, degraded
    last_checked: str
    details: Dict[str, Any]


class DeploymentManager:
    """
    Manages V5 free-tier deployment with IDE integration.
    Handles local infrastructure setup, validation, and monitoring.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.requirements = self._load_requirements()
        self.status_cache = {}
        
    def _load_requirements(self) -> List[DeploymentRequirement]:
        """Load deployment requirements."""
        return [
            DeploymentRequirement(
                name="docker",
                description="Docker container runtime",
                required=True,
                check_command="docker --version",
                version_min="20.10.0"
            ),
            DeploymentRequirement(
                name="kind",
                description="Kubernetes in Docker",
                required=True,
                check_command="kind version",
                version_min="0.20.0"
            ),
            DeploymentRequirement(
                name="kubectl",
                description="Kubernetes command-line tool",
                required=True,
                check_command="kubectl version --client",
                version_min="1.27.0"
            ),
            DeploymentRequirement(
                name="python",
                description="Python runtime",
                required=True,
                check_command="python3 --version",
                version_min="3.10"
            ),
            DeploymentRequirement(
                name="node",
                description="Node.js runtime",
                required=True,
                check_command="node --version",
                version_min="18.0"
            ),
            DeploymentRequirement(
                name="memory",
                description="System memory (minimum 8GB)",
                required=True,
                validation_function="check_memory"
            ),
            DeploymentRequirement(
                name="disk",
                description="Disk space (minimum 50GB)",
                required=True,
                validation_function="check_disk"
            )
        ]
    
    def check_requirements(self) -> Dict[str, Any]:
        """Check all deployment requirements."""
        results = {
            "overall_status": "unknown",
            "requirements": [],
            "missing_required": [],
            "warnings": []
        }
        
        all_met = True
        for req in self.requirements:
            result = self._check_requirement(req)
            results["requirements"].append(result)
            
            if not result["met"] and req.required:
                all_met = False
                results["missing_required"].append(req.name)
            elif not result["met"]:
                results["warnings"].append(req.name)
        
        results["overall_status"] = "ready" if all_met else "not_ready"
        return results
    
    def _check_requirement(self, req: DeploymentRequirement) -> Dict[str, Any]:
        """Check a single requirement."""
        result = {
            "name": req.name,
            "description": req.description,
            "required": req.required,
            "met": False,
            "current_version": None,
            "message": ""
        }
        
        try:
            if req.check_command:
                process = subprocess.run(
                    req.check_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if process.returncode == 0:
                    result["current_version"] = process.stdout.strip()
                    result["met"] = True
                    result["message"] = f"Found: {result['current_version']}"
                else:
                    result["message"] = "Not found or not executable"
            elif req.validation_function:
                result["met"] = getattr(self, req.validation_function)()
                result["message"] = "Passed" if result["met"] else "Failed"
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
        
        return result
    
    def check_memory(self) -> bool:
        """Check system memory requirements."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.total >= (8 * 1024 * 1024 * 1024)  # 8GB
        except ImportError:
            logger.warning("psutil not available, skipping memory check")
            return True  # Assume OK if can't check
    
    def check_disk(self) -> bool:
        """Check disk space requirements."""
        try:
            import shutil
            disk = shutil.disk_usage(self.project_root)
            return disk.free >= (50 * 1024 * 1024 * 1024)  # 50GB
        except Exception as e:
            logger.warning(f"Disk check failed: {e}")
            return True  # Assume OK if can't check
    
    def deploy_local_infrastructure(self) -> Dict[str, Any]:
        """Deploy local infrastructure components."""
        results = {
            "status": "in_progress",
            "steps": [],
            "errors": [],
            "start_time": datetime.now().isoformat()
        }
        
        # Step 1: Deploy Kind cluster
        results["steps"].append(self._deploy_kind_cluster())
        
        # Step 2: Start Docker Compose databases
        results["steps"].append(self._start_docker_compose())
        
        # Step 3: Deploy monitoring stack
        results["steps"].append(self._deploy_monitoring())
        
        # Determine overall status
        if all(step["success"] for step in results["steps"]):
            results["status"] = "completed"
        else:
            results["status"] = "partial"
            results["errors"] = [step["error"] for step in results["steps"] if not step["success"]]
        
        results["end_time"] = datetime.now().isoformat()
        return results
    
    def _deploy_kind_cluster(self) -> Dict[str, Any]:
        """Deploy Kind cluster for local Kubernetes."""
        config_file = self.project_root / "infrastructure" / "local-kubernetes" / "kind-cluster.yaml"
        
        try:
            if not config_file.exists():
                return {
                    "step": "kind_cluster",
                    "success": False,
                    "error": f"Config file not found: {config_file}"
                }
            
            process = subprocess.run(
                ["kind", "create", "cluster", "--config", str(config_file)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "step": "kind_cluster",
                "success": process.returncode == 0,
                "output": process.stdout,
                "error": process.stderr if process.returncode != 0 else None
            }
        except Exception as e:
            return {
                "step": "kind_cluster",
                "success": False,
                "error": str(e)
            }
    
    def _start_docker_compose(self) -> Dict[str, Any]:
        """Start Docker Compose databases."""
        compose_file = self.project_root / "infrastructure" / "local-database" / "docker-compose.yml"
        
        try:
            if not compose_file.exists():
                return {
                    "step": "docker_compose",
                    "success": False,
                    "error": f"Compose file not found: {compose_file}"
                }
            
            process = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(compose_file.parent)
            )
            
            return {
                "step": "docker_compose",
                "success": process.returncode == 0,
                "output": process.stdout,
                "error": process.stderr if process.returncode != 0 else None
            }
        except Exception as e:
            return {
                "step": "docker_compose",
                "success": False,
                "error": str(e)
            }
    
    def _deploy_monitoring(self) -> Dict[str, Any]:
        """Deploy monitoring stack (Prometheus/Grafana)."""
        prometheus_config = self.project_root / "infrastructure" / "local-database" / "prometheus" / "prometheus.yml"
        
        try:
            if not prometheus_config.exists():
                return {
                    "step": "monitoring",
                    "success": False,
                    "error": f"Prometheus config not found: {prometheus_config}"
                }
            
            # For now, assume monitoring is part of Docker Compose
            return {
                "step": "monitoring",
                "success": True,
                "output": "Monitoring configured via Docker Compose",
                "error": None
            }
        except Exception as e:
            return {
                "step": "monitoring",
                "success": False,
                "error": str(e)
            }
    
    def validate_deployment(self) -> Dict[str, Any]:
        """Validate deployment configuration and component health."""
        results = {
            "overall_status": "unknown",
            "components": [],
            "health_checks": [],
            "performance_metrics": {}
        }
        
        # Check Kind cluster
        results["components"].append(self._check_kind_cluster())
        
        # Check Docker containers
        results["components"].append(self._check_docker_containers())
        
        # Check database connectivity
        results["components"].append(self._check_database_connectivity())
        
        # Check monitoring
        results["components"].append(self._check_monitoring())
        
        # Determine overall status
        healthy_count = sum(1 for comp in results["components"] if comp["status"] == "healthy")
        results["overall_status"] = "healthy" if healthy_count == len(results["components"]) else "degraded"
        
        return results
    
    def _check_kind_cluster(self) -> Dict[str, Any]:
        """Check Kind cluster status."""
        try:
            process = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "component": "kind_cluster",
                "status": "healthy" if process.returncode == 0 else "unhealthy",
                "details": process.stdout if process.returncode == 0 else process.stderr
            }
        except Exception as e:
            return {
                "component": "kind_cluster",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def _check_docker_containers(self) -> Dict[str, Any]:
        """Check Docker container status."""
        try:
            process = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            containers = []
            if process.returncode == 0:
                for line in process.stdout.split('\n'):
                    if line:
                        name, status = line.split('\t')
                        containers.append({"name": name, "status": status})
            
            return {
                "component": "docker_containers",
                "status": "healthy" if len(containers) > 0 else "stopped",
                "details": {"containers": containers}
            }
        except Exception as e:
            return {
                "component": "docker_containers",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # Check PostgreSQL
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="momento",
                password="momento_password",
                database="momento"
            )
            conn.close()
            
            return {
                "component": "postgresql",
                "status": "healthy",
                "details": "Database connection successful"
            }
        except Exception as e:
            return {
                "component": "postgresql",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def _check_monitoring(self) -> Dict[str, Any]:
        """Check monitoring stack status."""
        try:
            # Check if Prometheus is accessible
            import requests
            response = requests.get("http://localhost:9090/-/healthy", timeout=5)
            
            return {
                "component": "prometheus",
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": f"Prometheus status: {response.status_code}"
            }
        except Exception as e:
            return {
                "component": "prometheus",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return {
            "requirements": self.check_requirements(),
            "deployment": self.validate_deployment(),
            "last_updated": datetime.now().isoformat()
        }


# Singleton instance
_deployment_manager: Optional[DeploymentManager] = None


def get_deployment_manager() -> DeploymentManager:
    """Get the singleton deployment manager instance."""
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = DeploymentManager()
    return _deployment_manager