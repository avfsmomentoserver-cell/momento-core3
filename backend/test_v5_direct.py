"""
Direct test of V5 endpoints with curl
"""

import subprocess
import time
import json

# Start the backend server
print("Starting backend server...")
server_process = subprocess.Popen(
    ["python3", "-m", "uvicorn", "momento.api.app:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd="/home/pirates/Avfs_GIT/backend"
)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(8)

try:
    # Test root endpoint
    print("\nTesting root endpoint...")
    result = subprocess.run(["curl", "-s", "http://localhost:8000/"], capture_output=True, text=True)
    print(f"Root endpoint: {result.status_code}")
    if result.status_code == 200:
        print(result.stdout[:200])
    
    # Test docs endpoint
    print("\nTesting docs endpoint...")
    result = subprocess.run(["curl", "-s", "http://localhost:8000/docs"], capture_output=True, text=True)
    print(f"Docs endpoint: {result.status_code}")
    
    # Test V5 system status
    print("\nTesting GET /api/v1/v5/system/status...")
    result = subprocess.run(["curl", "-s", "http://localhost:8000/api/v1/v5/system/status"], capture_output=True, text=True)
    print(f"V5 status endpoint: {result.status_code}")
    if result.status_code == 200:
        data = json.loads(result.stdout)
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {result.stdout}")
    
    # Test available routes
    print("\nTesting /api/v1/ routes...")
    result = subprocess.run(["curl", "-s", "http://localhost:8000/api/v1/"], capture_output=True, text=True)
    print(f"API root: {result.status_code}")
    
except Exception as e:
    print(f"Error during testing: {e}")
finally:
    # Stop the server
    print("\nStopping backend server...")
    server_process.terminate()
    server_process.wait(timeout=10)
    print("Server stopped")