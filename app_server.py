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

        # Calculate monthly cost estimate based on active GPUs
        # TODO: Track actual GPU hours for real billing
        monthly_cost = active_count * 100  # Rough estimate

        # Get real API request count from usage stats
        usage_stats = load_usage_stats()
        current_month = datetime.now().strftime("%Y-%m")
        monthly_requests = sum(
            count for day, count in usage_stats.get("requests_by_day", {}).items()
            if day.startswith(current_month)
        )

        return {
            "active_deployments": active_count,
            "api_requests": monthly_requests,
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
USAGE_STATS_FILE = "usage_stats.json"

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

def load_usage_stats():
    """Load usage statistics from file"""
    default_stats = {
        "total_requests": 0,
        "requests_by_key": {},
        "requests_by_day": {},
        "requests_by_deployment": {},
        "last_updated": None
    }
    if os.path.exists(USAGE_STATS_FILE):
        with open(USAGE_STATS_FILE, 'r') as f:
            saved = json.load(f)
            for key in default_stats:
                if key not in saved:
                    saved[key] = default_stats[key]
            return saved
    return default_stats

def save_usage_stats(stats):
    """Save usage statistics to file"""
    stats["last_updated"] = datetime.now().isoformat()
    with open(USAGE_STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def record_api_usage(key_id: str, deployment_id: str = None):
    """Record an API usage event"""
    stats = load_usage_stats()
    today = datetime.now().strftime("%Y-%m-%d")

    # Increment total requests
    stats["total_requests"] = stats.get("total_requests", 0) + 1

    # Increment requests by key
    if key_id not in stats["requests_by_key"]:
        stats["requests_by_key"][key_id] = {"total": 0, "last_used": None}
    stats["requests_by_key"][key_id]["total"] += 1
    stats["requests_by_key"][key_id]["last_used"] = datetime.now().isoformat()

    # Increment requests by day
    if today not in stats["requests_by_day"]:
        stats["requests_by_day"][today] = 0
    stats["requests_by_day"][today] += 1

    # Increment requests by deployment
    if deployment_id:
        if deployment_id not in stats["requests_by_deployment"]:
            stats["requests_by_deployment"][deployment_id] = 0
        stats["requests_by_deployment"][deployment_id] += 1

    save_usage_stats(stats)

    # Also update last_used on the API key
    keys = load_api_keys()
    for key in keys:
        if key["id"] == key_id:
            key["last_used"] = datetime.now().isoformat()
            key["request_count"] = key.get("request_count", 0) + 1
            break
    save_api_keys(keys)

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
# USAGE ANALYTICS
# ============================================================================

@app.get("/api/usage")
async def get_usage_analytics():
    """Get detailed usage analytics"""
    try:
        stats = load_usage_stats()
        keys = load_api_keys()

        # Get last 30 days of data
        today = datetime.now()
        daily_data = []
        for i in range(30):
            day = (today - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data.append({
                "date": day,
                "requests": stats.get("requests_by_day", {}).get(day, 0)
            })
        daily_data.reverse()

        # Enrich key data with usage stats
        key_usage = []
        for key in keys:
            key_stats = stats.get("requests_by_key", {}).get(key["id"], {})
            key_usage.append({
                "id": key["id"],
                "name": key["name"],
                "total_requests": key.get("request_count", key_stats.get("total", 0)),
                "last_used": key.get("last_used") or key_stats.get("last_used"),
                "created_at": key.get("created_at")
            })

        # Current month totals
        current_month = today.strftime("%Y-%m")
        this_month_requests = sum(
            count for day, count in stats.get("requests_by_day", {}).items()
            if day.startswith(current_month)
        )

        # Last month totals
        last_month = (today.replace(day=1) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m")
        last_month_requests = sum(
            count for day, count in stats.get("requests_by_day", {}).items()
            if day.startswith(last_month)
        )

        return {
            "total_requests": stats.get("total_requests", 0),
            "this_month": this_month_requests,
            "last_month": last_month_requests,
            "daily_data": daily_data,
            "key_usage": key_usage,
            "deployment_usage": stats.get("requests_by_deployment", {}),
            "last_updated": stats.get("last_updated")
        }
    except Exception as e:
        print(f"Error getting usage analytics: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total_requests": 0,
            "this_month": 0,
            "last_month": 0,
            "daily_data": [],
            "key_usage": [],
            "deployment_usage": {},
            "last_updated": None
        }

@app.post("/api/usage/record")
async def record_usage(key_id: str, deployment_id: Optional[str] = None):
    """Record an API usage event (for testing/manual recording)"""
    try:
        record_api_usage(key_id, deployment_id)
        return {"success": True, "message": "Usage recorded"}
    except Exception as e:
        print(f"Error recording usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SETTINGS
# ============================================================================

SETTINGS_FILE = "settings.json"

def load_settings():
    """Load settings from file"""
    default_settings = {
        "account": {
            "email": "developer@example.com",
            "name": "Developer",
            "company": "",
            "plan": "Professional",
            "created_at": "2026-01-01"
        },
        "billing": {
            "current_month": 0.00,
            "last_month": 0.00,
            "payment_method": None,
            "billing_email": ""
        },
        "notifications": {
            "deployment_started": True,
            "deployment_stopped": True,
            "deployment_failed": True,
            "usage_alerts": True,
            "weekly_summary": False,
            "email_notifications": True
        },
        "webhooks": []
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            saved = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key in default_settings:
                if key not in saved:
                    saved[key] = default_settings[key]
            return saved
    return default_settings

def save_settings(settings):
    """Save settings to file"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

@app.get("/api/settings")
async def get_settings():
    """Get account settings"""
    return load_settings()

class AccountUpdateRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None

@app.put("/api/settings/account")
async def update_account(request: AccountUpdateRequest):
    """Update account settings"""
    settings = load_settings()
    if request.email:
        settings["account"]["email"] = request.email
    if request.name:
        settings["account"]["name"] = request.name
    if request.company is not None:
        settings["account"]["company"] = request.company
    save_settings(settings)
    return {"success": True, "account": settings["account"]}

class NotificationUpdateRequest(BaseModel):
    deployment_started: Optional[bool] = None
    deployment_stopped: Optional[bool] = None
    deployment_failed: Optional[bool] = None
    usage_alerts: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    email_notifications: Optional[bool] = None

@app.put("/api/settings/notifications")
async def update_notifications(request: NotificationUpdateRequest):
    """Update notification preferences"""
    settings = load_settings()
    updates = request.model_dump(exclude_none=True)
    for key, value in updates.items():
        settings["notifications"][key] = value
    save_settings(settings)
    return {"success": True, "notifications": settings["notifications"]}

class WebhookRequest(BaseModel):
    url: str
    events: List[str]
    name: Optional[str] = None

@app.get("/api/settings/webhooks")
async def get_webhooks():
    """Get all webhooks"""
    settings = load_settings()
    return {"webhooks": settings.get("webhooks", [])}

@app.post("/api/settings/webhooks")
async def create_webhook(request: WebhookRequest):
    """Create a new webhook"""
    import secrets
    settings = load_settings()
    webhook = {
        "id": secrets.token_urlsafe(8),
        "name": request.name or f"Webhook {len(settings.get('webhooks', [])) + 1}",
        "url": request.url,
        "events": request.events,
        "created_at": datetime.now().isoformat(),
        "last_triggered": None,
        "active": True
    }
    if "webhooks" not in settings:
        settings["webhooks"] = []
    settings["webhooks"].append(webhook)
    save_settings(settings)
    return {"success": True, "webhook": webhook}

@app.delete("/api/settings/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook"""
    settings = load_settings()
    settings["webhooks"] = [w for w in settings.get("webhooks", []) if w["id"] != webhook_id]
    save_settings(settings)
    return {"success": True, "message": "Webhook deleted"}

@app.put("/api/settings/webhooks/{webhook_id}/toggle")
async def toggle_webhook(webhook_id: str):
    """Toggle webhook active status"""
    settings = load_settings()
    for webhook in settings.get("webhooks", []):
        if webhook["id"] == webhook_id:
            webhook["active"] = not webhook.get("active", True)
            save_settings(settings)
            return {"success": True, "active": webhook["active"]}
    raise HTTPException(status_code=404, detail="Webhook not found")

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
