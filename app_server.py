#!/usr/bin/env python3
"""
VoiceFlow Console - Modern SaaS Dashboard Backend
FastAPI server that serves the app.html frontend and provides REST APIs
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
import json
import os
import sys
from datetime import datetime

# Import existing backend modules
from verda_deploy import VerdaClient, VERDA_CLIENT_ID, VERDA_CLIENT_SECRET

# Initialize FastAPI
app = FastAPI(title="VoiceFlow Console API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
verda_client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)

# Data models
class DeploymentRequest(BaseModel):
    name: str
    gpu_type: str
    deployment_type: str = "raw_compute"  # raw_compute or serverless
    use_spot: bool = True

class APIKeyRequest(BaseModel):
    name: str
    description: Optional[str] = None

class StopDeploymentRequest(BaseModel):
    deployment_id: str

# ============================================================================
# SERVE FRONTEND
# ============================================================================

@app.get("/")
async def serve_landing():
    """Serve the console as the landing page"""
    return FileResponse("app.html")

@app.get("/app.html")
@app.get("/console")
async def serve_console():
    """Serve the console"""
    return FileResponse("app.html")

@app.get("/index.html")
async def serve_index():
    """Serve the old index page"""
    return FileResponse("index.html")

# ============================================================================
# DASHBOARD STATS
# ============================================================================

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    try:
        # Get deployments (both containers and instances)
        containers = verda_client.list_deployments()
        instances = verda_client.list_instances()

        total_deployments = len(containers) + len(instances)
        active_count = total_deployments  # Assume all listed are active

        # Calculate monthly cost estimate (mock for now)
        # In real implementation, would track actual GPU costs
        monthly_cost = active_count * 100  # Rough estimate

        # Mock API request count (in real app, track this)
        api_requests = 1200

        return {
            "active_deployments": active_count,
            "api_requests": api_requests,
            "monthly_cost": round(monthly_cost, 2),
            "uptime": 99.9,
            "total_deployments": total_deployments
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "active_deployments": 0,
            "api_requests": 0,
            "monthly_cost": 0,
            "uptime": 0,
            "total_deployments": 0
        }

# ============================================================================
# DEPLOYMENTS
# ============================================================================

@app.get("/api/deployments")
async def get_deployments():
    """Get all deployments"""
    try:
        containers = verda_client.list_deployments()
        instances = verda_client.list_instances()

        # Format deployments for frontend
        formatted = []

        # Add containers
        for d in containers:
            formatted.append({
                "id": d.get('id', 'unknown'),
                "name": d.get('name', 'Unknown'),
                "status": d.get('status', 'unknown'),
                "endpoint": d.get('endpoint', 'N/A'),
                "gpu": d.get('gpu_type', 'N/A'),
                "cost": "$0.000/hr",  # Would need to calculate from GPU type
                "created": d.get('created_at', 'N/A'),
                "type": "serverless"
            })

        # Add instances
        for i in instances:
            formatted.append({
                "id": i.get('id', 'unknown'),
                "name": i.get('hostname', 'Unknown'),
                "status": i.get('status', 'unknown'),
                "endpoint": i.get('ip', 'N/A'),
                "gpu": i.get('gpu_type', 'N/A'),
                "cost": "$0.000/hr",  # Would need to calculate from GPU type
                "created": i.get('created_at', 'N/A'),
                "type": "raw_compute"
            })

        return {"deployments": formatted}
    except Exception as e:
        print(f"Error getting deployments: {e}")
        import traceback
        traceback.print_exc()
        return {"deployments": []}

@app.post("/api/deployments/deploy")
async def deploy_server(request: DeploymentRequest):
    """Deploy a new TTS server"""
    try:
        print(f"Deploying: {request.name} on {request.gpu_type}")

        # Deploy based on type
        if request.deployment_type == "raw_compute":
            # Create raw compute instance
            result = verda_client.create_instance(
                name=request.name,
                gpu_name=request.gpu_type,  # Uses GPU display name
                use_spot=request.use_spot
            )

            return {
                "success": True,
                "deployment_id": result.get('id'),
                "message": f"Instance {request.name} created successfully! Check Deployments tab for connection details.",
                "details": result
            }
        else:
            # Serverless deployment (container)
            result = verda_client.create_container_deployment(
                name=request.name,
                gpu_name=request.gpu_type,
                use_spot=request.use_spot
            )

            return {
                "success": True,
                "deployment_id": result.get('id'),
                "message": f"Container {request.name} deployed successfully!",
                "details": result
            }

    except Exception as e:
        print(f"Deployment error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/deployments/stop")
async def stop_deployment(request: StopDeploymentRequest):
    """Stop a deployment"""
    try:
        deployment_id = request.deployment_id

        # Try to find the deployment in containers first
        containers = verda_client.list_deployments()
        is_container = any(c.get('id') == deployment_id or c.get('name') == deployment_id for c in containers)

        if is_container:
            # It's a container deployment
            result = verda_client.delete_deployment(deployment_id)
            return {
                "success": True,
                "message": f"Container deployment stopped successfully"
            }
        else:
            # It's an instance
            result = verda_client.delete_instance(deployment_id)
            return {
                "success": True,
                "message": f"Instance stopped successfully"
            }
    except Exception as e:
        print(f"Error stopping deployment: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/deployments/{deployment_id}/logs")
async def get_deployment_logs(deployment_id: str):
    """Get logs for a deployment"""
    try:
        logs = verda_client.get_deployment_logs(deployment_id)
        return {"logs": logs}
    except Exception as e:
        print(f"Error getting logs: {e}")
        return {"logs": "Unable to fetch logs"}

# ============================================================================
# GPU OPTIONS
# ============================================================================

@app.get("/api/gpus")
async def get_gpus():
    """Get available GPU types"""
    try:
        gpus = verda_client.get_available_gpus()

        # Format for frontend
        formatted = []
        for gpu in gpus:
            formatted.append({
                "name": gpu['name'],
                "display_name": gpu['display_name'],
                "memory": gpu['memory'],
                "spot_price": gpu['serverless_spot_price'],
                "instance_price": gpu['instance_spot_price'],
                "label": f"{gpu['display_name']} - ${gpu['serverless_spot_price']:.3f}/hr"
            })

        return {"gpus": formatted}
    except Exception as e:
        print(f"Error getting GPUs: {e}")
        return {"gpus": []}

# ============================================================================
# API KEYS
# ============================================================================

API_KEYS_FILE = "api_keys.json"

def load_api_keys():
    """Load API keys from file"""
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_api_keys(keys):
    """Save API keys to file"""
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

@app.get("/api/keys")
async def get_api_keys():
    """Get all API keys"""
    try:
        keys = load_api_keys()
        return {"keys": keys}
    except Exception as e:
        print(f"Error loading API keys: {e}")
        return {"keys": []}

@app.post("/api/keys/generate")
async def generate_api_key(request: APIKeyRequest):
    """Generate a new API key"""
    try:
        import secrets

        # Generate key
        key = f"vf_live_{secrets.token_urlsafe(32)}"

        # Load existing keys
        keys = load_api_keys()

        # Add new key
        new_key = {
            "id": secrets.token_urlsafe(8),
            "name": request.name,
            "description": request.description or "",
            "key": key,
            "created_at": datetime.now().isoformat(),
            "last_used": None
        }
        keys.append(new_key)

        # Save
        save_api_keys(keys)

        return {
            "success": True,
            "key": new_key
        }
    except Exception as e:
        print(f"Error generating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key"""
    try:
        keys = load_api_keys()
        keys = [k for k in keys if k['id'] != key_id]
        save_api_keys(keys)

        return {"success": True, "message": "API key revoked"}
    except Exception as e:
        print(f"Error revoking key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SETTINGS
# ============================================================================

@app.get("/api/settings")
async def get_settings():
    """Get account settings"""
    return {
        "account": {
            "email": "developer@example.com",
            "plan": "Professional",
            "created_at": "2026-01-01"
        },
        "billing": {
            "current_month": 87.50,
            "last_month": 92.30,
            "payment_method": "Credit Card (****1234)"
        }
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "VoiceFlow Console"}

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🎙️  VoiceFlow Console - Modern SaaS Dashboard       ║
║                                                              ║
║  Frontend:  http://localhost:8080                            ║
║  API Docs:  http://localhost:8080/docs                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
