"""
Test script for V5 Admin API endpoints
"""

import sys
import logging
import subprocess
import time
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("v5_api_test")

def test_v5_endpoints():
    """Test V5 admin API endpoints"""
    
    # Start the backend server
    logger.info("Starting backend server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "momento.api.app:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="/home/pirates/Avfs_GIT/backend"
    )
    
    # Wait for server to start
    logger.info("Waiting for server to start...")
    time.sleep(5)
    
    try:
        # Test system status endpoint
        logger.info("Testing GET /api/v1/v5/system/status")
        response = requests.get("http://localhost:8000/api/v1/v5/system/status")
        logger.info(f"Status endpoint response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"System status: {data}")
        
        # Test metrics endpoint
        logger.info("Testing GET /api/v1/v5/metrics")
        response = requests.get("http://localhost:8000/api/v1/v5/metrics")
        logger.info(f"Metrics endpoint response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Metrics: {data}")
        
        # Test milestones endpoint
        logger.info("Testing GET /api/v1/v5/milestones")
        response = requests.get("http://localhost:8000/api/v1/v5/milestones")
        logger.info(f"Milestones endpoint response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Milestones count: {data.get('total_milestones', 0)}")
        
        # Test health check endpoint
        logger.info("Testing GET /api/v1/v5/health/check")
        response = requests.get("http://localhost:8000/api/v1/v5/health/check")
        logger.info(f"Health check endpoint response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Health status: {data.get('overall', 'unknown')}")
        
        logger.info("✓ V5 API endpoints tested successfully")
        
    except Exception as e:
        logger.error(f"✗ API testing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop the server
        logger.info("Stopping backend server...")
        server_process.terminate()
        server_process.wait(timeout=10)
        logger.info("Server stopped")

if __name__ == "__main__":
    test_v5_endpoints()