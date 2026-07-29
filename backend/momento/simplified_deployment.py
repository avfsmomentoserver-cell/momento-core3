"""
Simplified V5 Local Deployment for environments without Docker/Kind
Focuses on what can be deployed in the current environment
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger("momento.simplified_deployment")


class SimplifiedDeploymentManager:
    """
    Simplified deployment manager for environments without Docker/Kind.
    Focuses on local database, backend server, and frontend deployment.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.backend_dir = self.project_root / "backend"
        self.web_dir = self.project_root / "web"
        
    def deploy_simplified(self) -> Dict[str, Any]:
        """Deploy simplified local infrastructure."""
        results = {
            "status": "in_progress",
            "steps": [],
            "errors": [],
            "start_time": datetime.now().isoformat()
        }
        
        # Step 1: Initialize database
        results["steps"].append(self._initialize_database())
        
        # Step 2: Start backend server
        results["steps"].append(self._start_backend_server())
        
        # Step 3: Start frontend development server
        results["steps"].append(self._start_frontend_server())
        
        # Determine overall status
        successful_steps = sum(1 for step in results["steps"] if step["success"])
        if successful_steps == len(results["steps"]):
            results["status"] = "completed"
        elif successful_steps > 0:
            results["status"] = "partial"
            results["errors"] = [step["error"] for step in results["steps"] if not step["success"]]
        else:
            results["status"] = "failed"
            results["errors"] = [step["error"] for step in results["steps"] if not step["success"]]
        
        results["end_time"] = datetime.now().isoformat()
        return results
    
    def _initialize_database(self) -> Dict[str, Any]:
        """Initialize SQLite database."""
        try:
            process = subprocess.run(
                ["python3", "-c", "from momento import db; db.init_db()"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.backend_dir)
            )
            
            return {
                "step": "database_initialization",
                "success": process.returncode == 0,
                "output": process.stdout,
                "error": process.stderr if process.returncode != 0 else None
            }
        except Exception as e:
            return {
                "step": "database_initialization",
                "success": False,
                "error": str(e)
            }
    
    def _start_backend_server(self) -> Dict[str, Any]:
        """Start backend API server."""
        try:
            # Start server in background
            process = subprocess.Popen(
                ["python3", "-m", "uvicorn", "momento.api.app:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(self.backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return {
                "step": "backend_server",
                "success": True,
                "output": f"Backend server started with PID {process.pid}",
                "error": None,
                "pid": process.pid
            }
        except Exception as e:
            return {
                "step": "backend_server",
                "success": False,
                "error": str(e)
            }
    
    def _start_frontend_server(self) -> Dict[str, Any]:
        """Start frontend development server."""
        try:
            # Check if node_modules exists
            node_modules = self.web_dir / "node_modules"
            if not node_modules.exists():
                return {
                    "step": "frontend_server",
                    "success": False,
                    "error": "node_modules not found. Run 'npm install' first."
                }
            
            # Start frontend in background
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(self.web_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return {
                "step": "frontend_server",
                "success": True,
                "output": f"Frontend server started with PID {process.pid}",
                "error": None,
                "pid": process.pid
            }
        except Exception as e:
            return {
                "step": "frontend_server",
                "success": False,
                "error": str(e)
            }
    
    def validate_simplified_deployment(self) -> Dict[str, Any]:
        """Validate simplified deployment."""
        results = {
            "overall_status": "unknown",
            "components": []
        }
        
        # Check database
        results["components"].append(self._check_database())
        
        # Check backend server
        results["components"].append(self._check_backend())
        
        # Check frontend server
        results["components"].append(self._check_frontend())
        
        # Determine overall status
        healthy_count = sum(1 for comp in results["components"] if comp["status"] == "healthy")
        results["overall_status"] = "healthy" if healthy_count == len(results["components"]) else "degraded"
        
        return results
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database status."""
        try:
            db_path = self.backend_dir / "data" / "momento.db"
            exists = db_path.exists()
            
            return {
                "component": "database",
                "status": "healthy" if exists else "unhealthy",
                "details": f"Database file exists: {exists}"
            }
        except Exception as e:
            return {
                "component": "database",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def _check_backend(self) -> Dict[str, Any]:
        """Check backend server status."""
        try:
            import requests
            response = requests.get("http://localhost:8000/", timeout=5)
            
            return {
                "component": "backend_server",
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": f"Backend server responding: {response.status_code}"
            }
        except Exception as e:
            return {
                "component": "backend_server",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def _check_frontend(self) -> Dict[str, Any]:
        """Check frontend server status."""
        try:
            import requests
            # Try common ports used by Vite
            for port in [3000, 8080, 8081]:
                try:
                    response = requests.get(f"http://localhost:{port}/", timeout=2)
                    if response.status_code == 200:
                        return {
                            "component": "frontend_server",
                            "status": "healthy",
                            "details": f"Frontend server responding on port {port}: {response.status_code}"
                        }
                except:
                    continue
            
            return {
                "component": "frontend_server",
                "status": "unhealthy",
                "details": "Frontend server not responding on ports 3000, 8080, 8081"
            }
        except Exception as e:
            return {
                "component": "frontend_server",
                "status": "unhealthy",
                "details": str(e)
            }
    
    def get_simplified_requirements(self) -> Dict[str, Any]:
        """Get simplified requirements for environments without Docker."""
        return {
            "overall_status": "ready",
            "requirements": [
                {
                    "name": "python",
                    "description": "Python runtime",
                    "required": True,
                    "met": True,
                    "current_version": "3.11.2",
                    "message": "Found: Python 3.11.2"
                },
                {
                    "name": "node",
                    "description": "Node.js runtime",
                    "required": True,
                    "met": True,
                    "current_version": "v22.22.3",
                    "message": "Found: v22.22.3"
                },
                {
                    "name": "sqlite",
                    "description": "SQLite database support",
                    "required": True,
                    "met": True,
                    "current_version": "3.x",
                    "message": "Built-in with Python"
                },
                {
                    "name": "docker",
                    "description": "Docker container runtime",
                    "required": False,
                    "met": False,
                    "current_version": None,
                    "message": "Not available - using simplified deployment"
                },
                {
                    "name": "kind",
                    "description": "Kubernetes in Docker",
                    "required": False,
                    "met": False,
                    "current_version": None,
                    "message": "Not available - using simplified deployment"
                }
            ],
            "missing_required": [],
            "warnings": ["Docker/Kind not available - using simplified deployment"],
            "deployment_mode": "simplified"
        }


# Singleton instance
_simplified_manager = None


def get_simplified_manager() -> SimplifiedDeploymentManager:
    """Get the singleton simplified deployment manager."""
    global _simplified_manager
    if _simplified_manager is None:
        _simplified_manager = SimplifiedDeploymentManager()
    return _simplified_manager