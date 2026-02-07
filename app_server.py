#!/usr/bin/env python3
"""
Computer - Cloud Console Backend
FastAPI server that serves the app.html frontend and provides REST APIs
Multi-tenant platform with authentication and billing
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
import uvicorn
import asyncio
import json
import os
import sys
import subprocess
import secrets
import shlex
import re as re_module
from datetime import datetime
from contextlib import asynccontextmanager

# Database and auth imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

try:
    from database import get_db, init_db, check_db_connection, get_db_context
    from models import User, Deployment, UsageRecord, DeploymentStatus, ComputeProvider, UserTier
    from auth import router as auth_router, get_current_user, get_optional_user, limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from storage import storage_client, get_template_storage_path, TEMPLATE_STORAGE_PATHS
    from warming import warming_manager, start_warming_manager, stop_warming_manager
    from billing import router as billing_router, STRIPE_ENABLED
    DB_AVAILABLE = True
except ImportError as e:
    print(f"Database modules not available: {e}")
    DB_AVAILABLE = False
    storage_client = None
    warming_manager = None
    STRIPE_ENABLED = False

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Docker SDK for local container management
try:
    import docker
    docker_client = docker.from_env()
    DOCKER_AVAILABLE = True
except:
    docker_client = None
    DOCKER_AVAILABLE = False

# Import existing backend modules - with demo mode fallback
DEMO_MODE = False
try:
    from verda_deploy import VerdaClient, VERDA_CLIENT_ID, VERDA_CLIENT_SECRET
except ImportError:
    DEMO_MODE = True
    VerdaClient = None

# Import Targon client
try:
    from targon_client import TargonClient, TARGON_API_KEY
    TARGON_AVAILABLE = bool(TARGON_API_KEY)
except ImportError:
    TargonClient = None
    TARGON_API_KEY = ""
    TARGON_AVAILABLE = False

# Template deployment server configuration (from environment)
TEMPLATE_SERVER_HOST = os.getenv("TEMPLATE_SERVER_HOST", "135.181.63.151")
TEMPLATE_SERVER_SSH_HOST = os.getenv("TEMPLATE_SERVER_SSH_HOST", TEMPLATE_SERVER_HOST)
TEMPLATE_SERVER_USER = os.getenv("TEMPLATE_SERVER_USER", "root")

# Pricing markup configuration (20% markup on provider costs)
PRICING_MARKUP = {
    "verda": 1.20,   # 20% markup
    "targon": 1.20,  # 20% markup
    "default": 1.20  # Default markup for any provider
}

def apply_markup(base_price: float, provider: str = "default") -> float:
    """Apply pricing markup to base provider cost"""
    multiplier = PRICING_MARKUP.get(provider, PRICING_MARKUP["default"])
    return round(base_price * multiplier, 4)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    if DB_AVAILABLE:
        try:
            await init_db()
            if await check_db_connection():
                print("Database connected successfully")
                # Start warming manager
                if warming_manager:
                    await start_warming_manager()
            else:
                print("Database connection failed - running in limited mode")
        except Exception as e:
            print(f"Database initialization failed: {e}")
    yield
    # Shutdown
    if DB_AVAILABLE and warming_manager:
        await stop_warming_manager()

# Initialize FastAPI
app = FastAPI(
    title="Polaris Computer API",
    version="2.0.0",
    description="Multi-tenant cloud compute platform",
    lifespan=lifespan
)

# Get allowed origins from environment, with safe defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
if os.getenv("ENVIRONMENT") == "production":
    ALLOWED_ORIGINS = [
        "https://polaris.computer",
        "https://www.polaris.computer",
        "https://api.polaris.computer",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Configure rate limiting
if DB_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include auth and billing routers
if DB_AVAILABLE:
    app.include_router(auth_router, prefix="/api")
    app.include_router(billing_router, prefix="/api")

# Initialize clients - demo mode if no credentials
verda_client = None
targon_client = None

if not DEMO_MODE:
    try:
        verda_client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)
    except Exception as e:
        print(f"⚠️  Verda auth failed, running in DEMO MODE: {e}")
        DEMO_MODE = True

# Initialize Targon client (separate from demo mode)
if TARGON_AVAILABLE and TargonClient:
    try:
        targon_client = TargonClient(TARGON_API_KEY)
        print("🎯 Targon client initialized")
    except Exception as e:
        print(f"⚠️  Targon init failed: {e}")
        targon_client = None

if DEMO_MODE:
    print("🎮 Running in DEMO MODE - GPU deployments disabled")

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
# TEMPLATE DEPLOYMENT SYSTEM
# ============================================================================

class TemplateCategory(str, Enum):
    AI_ML = "ai_ml"
    DEVELOPMENT = "development"
    INFRASTRUCTURE = "infrastructure"
    DESKTOP = "desktop"
    GAMES = "games"


class TemplateParameter(BaseModel):
    name: str
    label: str
    type: str  # text, number, select, boolean
    required: bool = True
    default: Optional[Any] = None
    placeholder: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None  # For select type
    description: Optional[str] = None


class TemplateConfig(BaseModel):
    id: str
    name: str
    description: str
    category: TemplateCategory
    icon: str  # Emoji or icon name
    script_path: str  # Path to deployment script
    predeployment_required: bool = True  # Whether to run predeployment first
    parameters: List[TemplateParameter]
    default_port: int
    estimated_deploy_time: str  # e.g., "3-5 minutes"
    access_type: str  # "web", "api", "vnc", "terminal"
    features: List[str]  # Feature list for display
    color: str  # Tailwind color class for UI


# Template Registry - all available deployment templates
TEMPLATE_REGISTRY: Dict[str, TemplateConfig] = {
    "ollama": TemplateConfig(
        id="ollama",
        name="Ollama Chat",
        description="ChatGPT-like interface for open-source LLMs. Beautiful UI with Open WebUI, powered by Ollama.",
        category=TemplateCategory.AI_ML,
        icon="🦙",
        script_path="ollama-template/deploy_ollama.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="model",
                label="Model",
                type="select",
                required=True,
                default="llama3.2",
                options=[
                    {"value": "llama3.2", "label": "Llama 3.2 (3B) - Fast"},
                    {"value": "llama3.2:1b", "label": "Llama 3.2 (1B) - Fastest"},
                    {"value": "llama3.1", "label": "Llama 3.1 (8B)"},
                    {"value": "llama3.1:70b", "label": "Llama 3.1 (70B) - Best"},
                    {"value": "mistral", "label": "Mistral (7B)"},
                    {"value": "mixtral", "label": "Mixtral 8x7B"},
                    {"value": "codellama", "label": "Code Llama"},
                    {"value": "deepseek-coder", "label": "DeepSeek Coder"},
                    {"value": "phi3", "label": "Phi-3"},
                    {"value": "gemma2", "label": "Gemma 2"},
                    {"value": "qwen2.5", "label": "Qwen 2.5"},
                ],
                description="Choose the LLM to deploy"
            ),
            TemplateParameter(
                name="port",
                label="Web UI Port",
                type="number",
                required=True,
                default=3000,
                placeholder="3000",
                description="Port for the chat interface"
            ),
        ],
        default_port=3000,
        estimated_deploy_time="3-5 minutes",
        access_type="web",
        features=[
            "ChatGPT-like interface",
            "GPU acceleration",
            "Multiple models",
            "Conversation history",
            "OpenAI-compatible API",
        ],
        color="purple"
    ),
    "jupyter": TemplateConfig(
        id="jupyter",
        name="Jupyter Notebook",
        description="GPU-accelerated Jupyter notebook with TensorFlow and PyTorch pre-installed for data science and ML development.",
        category=TemplateCategory.AI_ML,
        icon="📓",
        script_path="notbook/deploy_jupyter.sh",
        predeployment_required=True,
        parameters=[
            TemplateParameter(
                name="port",
                label="Notebook Port",
                type="number",
                required=True,
                default=8888,
                placeholder="8888",
                description="Port for Jupyter web interface"
            ),
        ],
        default_port=8888,
        estimated_deploy_time="3-5 minutes",
        access_type="web",
        features=[
            "TensorFlow & PyTorch",
            "GPU support (CUDA)",
            "Pre-installed ML libraries",
            "Persistent storage",
            "JupyterLab interface",
        ],
        color="orange"
    ),
    "dev-terminal": TemplateConfig(
        id="dev-terminal",
        name="Development Terminal",
        description="Web-based development terminal with full Linux environment, Python, Node.js, and development tools.",
        category=TemplateCategory.DEVELOPMENT,
        icon="💻",
        script_path="polaris_cli/deploy-development-terminal.sh",
        predeployment_required=True,
        parameters=[
            TemplateParameter(
                name="port",
                label="Terminal Port",
                type="number",
                required=True,
                default=7681,
                placeholder="7681",
                description="Port for web terminal access"
            ),
            TemplateParameter(
                name="container_name",
                label="Container Name",
                type="text",
                required=False,
                default="dev-terminal",
                placeholder="dev-terminal",
                description="Name for the Docker container"
            ),
        ],
        default_port=7681,
        estimated_deploy_time="2-4 minutes",
        access_type="terminal",
        features=[
            "Full Linux environment",
            "Python 3.10 + pip",
            "Node.js + npm",
            "Git & build tools",
            "GPU access (if available)",
            "Bore tunnel for remote access",
        ],
        color="green"
    ),
    "ubuntu-desktop": TemplateConfig(
        id="ubuntu-desktop",
        name="Cloud Computer",
        description="Blazing fast Ubuntu desktop in your browser. Powered by Kasm - no installs, just click and go.",
        category=TemplateCategory.DESKTOP,
        icon="🖥️",
        script_path="remotedskstop/deploy_cloud_computer.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Desktop Port",
                type="number",
                required=True,
                default=6901,
                placeholder="6901",
                description="Port for web desktop access"
            ),
        ],
        default_port=6901,
        estimated_deploy_time="2-3 minutes",
        access_type="web",
        features=[
            "Blazing fast H.264 streaming",
            "Full Ubuntu desktop in browser",
            "GPU accelerated (if available)",
            "Chrome, Firefox, VS Code ready",
            "No software to install",
        ],
        color="amber"
    ),
    "transformer-labs": TemplateConfig(
        id="transformer-labs",
        name="Transformer Lab",
        description="Fine-tune LLMs with a visual interface. Train, evaluate, and deploy models - all from your browser.",
        category=TemplateCategory.AI_ML,
        icon="🤖",
        script_path="transformer-lab/deploy_transformer_lab.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Web UI Port",
                type="number",
                required=True,
                default=8338,
                placeholder="8338",
                description="Port for the web interface"
            ),
        ],
        default_port=8338,
        estimated_deploy_time="2-3 minutes",
        access_type="web",
        features=[
            "Visual model fine-tuning",
            "LoRA/QLoRA training",
            "Model evaluation",
            "One-click inference",
            "Experiment tracking",
        ],
        color="blue"
    ),
    "minecraft": TemplateConfig(
        id="minecraft",
        name="Minecraft Server",
        description="Host your own Minecraft server. Supports Paper, Fabric, Forge, Spigot, and Vanilla.",
        category=TemplateCategory.GAMES,
        icon="⛏️",
        script_path="minecraft/deploy_minecraft.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Server Port",
                type="number",
                required=True,
                default=25565,
                placeholder="25565",
                description="Port for Minecraft connections"
            ),
            TemplateParameter(
                name="server_type",
                label="Server Type",
                type="select",
                required=True,
                default="PAPER",
                options=[
                    {"value": "PAPER", "label": "Paper (Recommended)"},
                    {"value": "VANILLA", "label": "Vanilla"},
                    {"value": "FABRIC", "label": "Fabric"},
                    {"value": "FORGE", "label": "Forge"},
                    {"value": "SPIGOT", "label": "Spigot"},
                ],
                description="Server software type"
            ),
            TemplateParameter(
                name="memory",
                label="Memory",
                type="select",
                required=True,
                default="4G",
                options=[
                    {"value": "2G", "label": "2 GB"},
                    {"value": "4G", "label": "4 GB (Recommended)"},
                    {"value": "8G", "label": "8 GB"},
                    {"value": "16G", "label": "16 GB"},
                ],
                description="Server memory allocation"
            ),
        ],
        default_port=25565,
        estimated_deploy_time="2-4 minutes",
        access_type="game",
        features=[
            "Paper/Fabric/Forge/Spigot support",
            "Auto-updates available",
            "RCON enabled",
            "Persistent world data",
            "Plugin support (Paper/Spigot)",
        ],
        color="green"
    ),
    "valheim": TemplateConfig(
        id="valheim",
        name="Valheim Server",
        description="Viking survival multiplayer server. Explore, build, and conquer with friends.",
        category=TemplateCategory.GAMES,
        icon="⚔️",
        script_path="valheim/deploy_valheim.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Game Port",
                type="number",
                required=True,
                default=2456,
                placeholder="2456",
                description="UDP port for game connections (uses 3 consecutive ports)"
            ),
            TemplateParameter(
                name="server_name",
                label="Server Name",
                type="text",
                required=True,
                default="Valheim Server",
                placeholder="My Valheim Server",
                description="Name shown in server browser"
            ),
            TemplateParameter(
                name="password",
                label="Server Password",
                type="text",
                required=True,
                default="valheim123",
                placeholder="valheim123",
                description="Password to join (min 5 characters)"
            ),
        ],
        default_port=2456,
        estimated_deploy_time="3-5 minutes",
        access_type="game",
        features=[
            "Auto-updates enabled",
            "Automatic backups every 2 hours",
            "Persistent world data",
            "Password protected",
            "Graceful shutdown (saves world)",
        ],
        color="orange"
    ),
    "terraria": TemplateConfig(
        id="terraria",
        name="Terraria Server",
        description="2D sandbox adventure server. Dig, fight, explore, and build with friends.",
        category=TemplateCategory.GAMES,
        icon="🌳",
        script_path="terraria/deploy_terraria.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Game Port",
                type="number",
                required=True,
                default=7777,
                placeholder="7777",
                description="Port for game connections"
            ),
            TemplateParameter(
                name="world_name",
                label="World Name",
                type="text",
                required=True,
                default="BigAI",
                placeholder="MyWorld",
                description="Name of the world"
            ),
            TemplateParameter(
                name="world_size",
                label="World Size",
                type="select",
                required=True,
                default="medium",
                options=[
                    {"value": "small", "label": "Small"},
                    {"value": "medium", "label": "Medium (Recommended)"},
                    {"value": "large", "label": "Large"},
                ],
                description="Size of the generated world"
            ),
        ],
        default_port=7777,
        estimated_deploy_time="1-2 minutes",
        access_type="game",
        features=[
            "Auto-generated world",
            "Up to 8 players",
            "Persistent world data",
            "Lightweight server",
            "Journey/Classic/Expert/Master modes",
        ],
        color="green"
    ),
    "factorio": TemplateConfig(
        id="factorio",
        name="Factorio Server",
        description="Factory building multiplayer server. Automate, optimize, and expand your industrial empire.",
        category=TemplateCategory.GAMES,
        icon="🏭",
        script_path="factorio/deploy_factorio.sh",
        predeployment_required=False,
        parameters=[
            TemplateParameter(
                name="port",
                label="Game Port",
                type="number",
                required=True,
                default=34197,
                placeholder="34197",
                description="UDP port for game connections"
            ),
            TemplateParameter(
                name="server_name",
                label="Server Name",
                type="text",
                required=True,
                default="Factorio Server",
                placeholder="My Factory",
                description="Name of the server"
            ),
        ],
        default_port=34197,
        estimated_deploy_time="2-3 minutes",
        access_type="game",
        features=[
            "Auto-save every 10 minutes",
            "LAN discovery enabled",
            "Persistent factory data",
            "Mod support available",
            "Admin commands available",
        ],
        color="orange"
    ),
}

# Active template deployments storage
TEMPLATE_DEPLOYMENTS_FILE = "template_deployments.json"


def load_template_deployments():
    """Load template deployments from file"""
    if os.path.exists(TEMPLATE_DEPLOYMENTS_FILE):
        with open(TEMPLATE_DEPLOYMENTS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_template_deployments(deployments):
    """Save template deployments to file"""
    with open(TEMPLATE_DEPLOYMENTS_FILE, 'w') as f:
        json.dump(deployments, f, indent=2)


class TemplateDeploymentRequest(BaseModel):
    template_id: str
    name: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @validator('template_id')
    def validate_template_id(cls, v):
        if v not in TEMPLATE_REGISTRY:
            raise ValueError(f"Unknown template: {v}")
        return v

    @validator('parameters')
    def validate_parameters(cls, v, values):
        # Allowlist validation to prevent shell injection
        # Only permit safe characters in string parameters
        safe_pattern = re_module.compile(r'^[a-zA-Z0-9._:/\-@ ]+$')
        sanitized = {}
        for key, value in v.items():
            if isinstance(value, str):
                if not safe_pattern.match(value):
                    raise ValueError(
                        f"Parameter '{key}' contains invalid characters. "
                        "Only alphanumeric, '.', '_', ':', '/', '-', '@', and spaces are allowed."
                    )
                sanitized[key] = value
            else:
                sanitized[key] = value
        return sanitized


class TemplateDeploymentStatus(str, Enum):
    PENDING = "pending"
    PREDEPLOYMENT = "predeployment"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


# WebSocket connections for deployment progress
active_connections: Dict[str, WebSocket] = {}


async def send_deployment_progress(deployment_id: str, message: str, progress: int = None, status: str = None):
    """Send deployment progress to connected WebSocket clients"""
    if deployment_id in active_connections:
        try:
            await active_connections[deployment_id].send_json({
                "deployment_id": deployment_id,
                "message": message,
                "progress": progress,
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")


async def get_container_access_info(template_id: str, container_name: str, host: str, ssh_user: str, port: int) -> dict:
    """Retrieve access credentials/tokens from a deployed container"""
    access_info = {
        "url": f"http://{host}:{port}",
        "credentials": None,
        "instructions": None
    }

    try:
        if template_id == "jupyter":
            # Get Jupyter token from container
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                f"{ssh_user}@{host}",
                f"docker exec {shlex.quote(container_name)} jupyter server list 2>/dev/null | grep token= | head -1"
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            output = stdout.decode().strip()

            # Parse token from output like: http://hostname:8888/?token=abc123 :: /path
            if "token=" in output:
                import re
                match = re.search(r'token=([a-f0-9]+)', output)
                if match:
                    token = match.group(1)
                    access_info["url"] = f"http://{host}:{port}/?token={token}"
                    access_info["credentials"] = {"token": token}

        elif template_id == "ubuntu-desktop":
            # Kasm Workspaces - fast browser-native desktop
            access_info["url"] = f"https://{host}:{port}"
            access_info["credentials"] = {"username": "kasm_user", "password": "cloudpc"}
            access_info["instructions"] = "Login with kasm_user / cloudpc"

        elif template_id == "dev-terminal":
            # Terminal has no auth by default
            access_info["instructions"] = "No authentication required"

        elif template_id == "ollama":
            # Ollama with Open WebUI
            access_info["instructions"] = "Create a local account on first visit (no email needed), then start chatting!"

        elif template_id == "transformer-labs":
            access_info["instructions"] = "Web UI ready. No authentication required."

    except Exception as e:
        print(f"Error getting container access info: {e}")

    return access_info


async def run_deployment_script(deployment_id: str, template: TemplateConfig, request: TemplateDeploymentRequest):
    """Execute deployment script with progress streaming via SSH"""
    deployments = load_template_deployments()

    # Use configured server (SSH_HOST for SSH, HOST for access URLs)
    host = TEMPLATE_SERVER_SSH_HOST
    ssh_user = TEMPLATE_SERVER_USER

    try:
        # Get the templates directory path
        templates_dir = os.path.expanduser("~/bigailabs-templates")

        # Build the command based on template
        if template.id == "ollama":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-m", request.parameters.get("model", "llama3.2"),
                "-p", str(request.parameters.get("port", 3000))
            ]
        elif template.id == "jupyter":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 8888)),
                "-a", host
            ]
        elif template.id == "dev-terminal":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 7681)),
                "-n", request.parameters.get("container_name", "dev-terminal")
            ]
        elif template.id == "ubuntu-desktop":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 6901)),
                "-a", host
            ]
        elif template.id == "transformer-labs":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 8338))
            ]
        elif template.id == "minecraft":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 25565)),
                "-t", request.parameters.get("server_type", "PAPER"),
                "-m", request.parameters.get("memory", "4G")
            ]
        elif template.id == "valheim":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 2456)),
                "-n", request.parameters.get("server_name", "Valheim Server"),
                "-w", request.parameters.get("password", "valheim123")
            ]
        elif template.id == "terraria":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 7777)),
                "-w", request.parameters.get("world_name", "BigAI"),
                "-s", request.parameters.get("world_size", "medium")
            ]
        elif template.id == "factorio":
            script_path = os.path.join(templates_dir, template.script_path)
            cmd = [
                "bash", script_path,
                "-h", host,
                "-u", ssh_user,
                "-p", str(request.parameters.get("port", 34197)),
                "-n", request.parameters.get("server_name", "Factorio Server")
            ]
        else:
            raise ValueError(f"Unknown template: {template.id}")

        # Run predeployment if required (skip by default since server should be ready)
        if template.predeployment_required and request.parameters.get("run_predeployment", False):
            await send_deployment_progress(deployment_id, "Running predeployment setup...", 10, "predeployment")
            deployments[deployment_id]["status"] = TemplateDeploymentStatus.PREDEPLOYMENT.value
            save_template_deployments(deployments)

            predeployment_script = os.path.join(templates_dir, "predployment_phase_one.sh")
            predeployment_cmd = [
                "bash", predeployment_script,
                "-h", host,
                "-u", ssh_user
            ]

            process = await asyncio.create_subprocess_exec(
                *predeployment_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_text = line.decode().strip()
                if line_text:
                    await send_deployment_progress(deployment_id, f"[Predeployment] {line_text}", 20)

            await process.wait()

            if process.returncode != 0:
                raise Exception("Predeployment failed")

        # Run main deployment
        await send_deployment_progress(deployment_id, f"Deploying {template.name}...", 40, "deploying")
        deployments = load_template_deployments()
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.DEPLOYING.value
        save_template_deployments(deployments)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        progress = 40
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_text = line.decode().strip()
            if line_text:
                progress = min(progress + 2, 90)
                await send_deployment_progress(deployment_id, line_text, progress)

        await process.wait()

        if process.returncode == 0:
            await send_deployment_progress(deployment_id, "Deployment completed! Fetching access credentials...", 95, "running")

            # Wait a moment for the container to be fully ready
            await asyncio.sleep(3)

            # Get container name based on template (use safe defaults, not user input)
            safe_container_names = {
                "jupyter": "jupyter-notebook",
                "ubuntu-desktop": "cloud-computer",
                "ollama": "open-webui",
                "transformer-labs": "transformerlab",
                "minecraft": "minecraft-server",
                "valheim": "valheim-server",
                "terraria": "terraria-server",
                "factorio": "factorio-server",
                "dev-terminal": "dev-terminal",
            }
            container_name = safe_container_names.get(template.id, template.id)

            # Fetch access credentials
            port = request.parameters.get("port", template.default_port)
            access_info = await get_container_access_info(template.id, container_name, host, ssh_user, port)

            # Update deployment record with access info
            deployments = load_template_deployments()
            deployments[deployment_id]["status"] = TemplateDeploymentStatus.RUNNING.value
            deployments[deployment_id]["completed_at"] = datetime.now().isoformat()
            deployments[deployment_id]["access_url"] = access_info["url"]
            if access_info.get("credentials"):
                deployments[deployment_id]["credentials"] = access_info["credentials"]
            if access_info.get("instructions"):
                deployments[deployment_id]["instructions"] = access_info["instructions"]
            save_template_deployments(deployments)

            await send_deployment_progress(deployment_id, f"Ready! Click 'Launch' to open your service.", 100, "running")
        else:
            raise Exception(f"Deployment script exited with code {process.returncode}")

    except Exception as e:
        await send_deployment_progress(deployment_id, f"Deployment failed: {str(e)}", 0, "failed")
        deployments = load_template_deployments()
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.FAILED.value
        deployments[deployment_id]["error"] = str(e)
        save_template_deployments(deployments)


def generate_startup_script(template: TemplateConfig, parameters: Dict[str, Any]) -> str:
    """Generate a startup script for the template that runs on the GPU instance"""

    # Base script with Docker and NVIDIA setup
    base_script = """#!/bin/bash
set -e

echo "=== Computer Template Deployment ==="
echo "Template: {template_name}"
echo "Starting at: $(date)"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Install NVIDIA Container Toolkit if not present
if ! command -v nvidia-container-toolkit &> /dev/null; then
    echo "Installing NVIDIA Container Toolkit..."
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update
    apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
fi

# Wait for Docker to be ready
sleep 5

"""

    # Template-specific deployment commands
    # All user parameters are shell-escaped for safety
    if template.id == "ollama":
        model = shlex.quote(str(parameters.get("model", "llama2")))
        port = shlex.quote(str(parameters.get("port", 8000)))
        script = base_script + f"""
echo "Deploying Ollama LLM..."

# Pull and run Ollama
docker run -d --gpus all \\
  --name ollama \\
  -p 11434:11434 \\
  -v ollama:/root/.ollama \\
  --restart unless-stopped \\
  ollama/ollama

# Wait for Ollama to start
sleep 10

# Pull the model
docker exec ollama ollama pull {model}

# Deploy FastAPI wrapper for OpenAI-compatible API
docker run -d --gpus all \\
  --name ollama-api \\
  -p {port}:8000 \\
  -e OLLAMA_HOST=http://ollama:11434 \\
  --link ollama:ollama \\
  --restart unless-stopped \\
  ghcr.io/ollama/ollama-api:latest || echo "API wrapper optional"

echo "Ollama deployed on port 11434, API on port {port}"
echo "Model: {model}"
"""

    elif template.id == "jupyter":
        port = shlex.quote(str(parameters.get("port", 8888)))
        script = base_script + f"""
echo "Deploying Jupyter Notebook..."

# Generate a random token
JUPYTER_TOKEN=$(openssl rand -hex 32)

docker run -d --gpus all \\
  --name jupyter \\
  -p {port}:8888 \\
  -v $(pwd)/notebooks:/home/jovyan/work \\
  -e JUPYTER_TOKEN=$JUPYTER_TOKEN \\
  --restart unless-stopped \\
  jupyter/tensorflow-notebook:latest

echo "Jupyter deployed on port {port}"
echo "Access token: $JUPYTER_TOKEN"
echo "JUPYTER_TOKEN=$JUPYTER_TOKEN" >> /root/.jupyter_token
"""

    elif template.id == "dev-terminal":
        port = shlex.quote(str(parameters.get("port", 7681)))
        container_name = shlex.quote(str(parameters.get("container_name", "dev-terminal")))
        script = base_script + f"""
echo "Deploying Development Terminal..."

docker run -d --gpus all \\
  --name {container_name} \\
  -p {port}:7681 \\
  -v $(pwd)/workspace:/workspace \\
  --restart unless-stopped \\
  tsl0922/ttyd:latest \\
  ttyd -W bash

echo "Dev Terminal deployed on port {port}"
"""

    elif template.id == "ubuntu-desktop":
        port = shlex.quote(str(parameters.get("port", 6901)))
        vnc_port = shlex.quote(str(parameters.get("vnc_port", 5901)))
        script = base_script + f"""
echo "Deploying Ubuntu Desktop..."

docker run -d \\
  --name ubuntu-desktop \\
  -p {port}:6901 \\
  -p {vnc_port}:5901 \\
  -e VNC_PW=computer \\
  --restart unless-stopped \\
  kasmweb/ubuntu-jammy-desktop:1.14.0

echo "Ubuntu Desktop deployed"
echo "Web access: port {port}"
echo "VNC access: port {vnc_port}"
echo "Password: computer"
"""

    elif template.id == "transformer-labs":
        port = shlex.quote(str(parameters.get("port", 8000)))
        image_type = parameters.get("image_type", "api")
        if image_type == "api":
            image = "transformerlab/api:latest"
            internal_port = 8338
        else:
            image = "ghcr.io/bigideaafrica/labs:latest"
            internal_port = 8000
        image = shlex.quote(image)
        script = base_script + f"""
echo "Deploying Transformer Labs..."

mkdir -p workspace config

docker run -d --gpus all \\
  --name transformerlab \\
  -p {port}:{internal_port} \\
  -v $(pwd)/workspace:/home/abc/workspace \\
  -v $(pwd)/config:/config \\
  -e PUID=1000 \\
  -e PGID=1000 \\
  --restart unless-stopped \\
  {image}

echo "Transformer Labs deployed on port {port}"
"""

    else:
        script = base_script + f"""
echo "Unknown template: {template.id}"
exit 1
"""

    # Add completion marker
    script += """
echo "=== Deployment Complete ==="
echo "Finished at: $(date)"
echo "DEPLOYMENT_STATUS=SUCCESS" > /root/.deployment_status
"""

    return script.format(template_name=template.name)


async def run_template_deployment(deployment_id: str, template: TemplateConfig, request: TemplateDeploymentRequest):
    """Deploy a template by provisioning a GPU and running the startup script"""
    deployments = load_template_deployments()

    try:
        # Update status to provisioning
        await send_deployment_progress(deployment_id, "Provisioning GPU instance...", 10, "provisioning")
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.PROVISIONING.value
        save_template_deployments(deployments)

        # Check if we have Verda credentials
        if DEMO_MODE or verda_client is None:
            # Demo mode - simulate deployment
            await send_deployment_progress(deployment_id, "Demo mode: Simulating GPU provisioning...", 20)
            await asyncio.sleep(2)
            await send_deployment_progress(deployment_id, "Demo mode: Creating virtual instance...", 40)
            await asyncio.sleep(2)
            await send_deployment_progress(deployment_id, "Demo mode: Installing Docker...", 60)
            await asyncio.sleep(2)
            await send_deployment_progress(deployment_id, f"Demo mode: Deploying {template.name}...", 80)
            await asyncio.sleep(2)

            # Simulate successful deployment
            demo_ip = f"demo-{deployment_id[:8]}.computer.app"
            port = request.parameters.get("port", template.default_port)

            deployments = load_template_deployments()
            deployments[deployment_id]["status"] = TemplateDeploymentStatus.RUNNING.value
            deployments[deployment_id]["instance_ip"] = demo_ip
            deployments[deployment_id]["access_url"] = f"http://{demo_ip}:{port}"
            deployments[deployment_id]["completed_at"] = datetime.now().isoformat()
            deployments[deployment_id]["demo_mode"] = True
            save_template_deployments(deployments)

            await send_deployment_progress(
                deployment_id,
                f"Demo deployment complete! Access URL: http://{demo_ip}:{port}",
                100,
                "running"
            )
            return

        # Real deployment with Verda
        await send_deployment_progress(deployment_id, f"Creating {request.gpu_type} instance...", 15)

        # Generate the startup script
        startup_script = generate_startup_script(template, request.parameters)

        # Create instance via Verda
        instance = verda_client.create_instance(
            name=request.name,
            gpu_name=request.gpu_type,
            use_spot=request.use_spot
        )

        if not instance:
            raise Exception("Failed to create GPU instance")

        instance_id = instance.get("id")
        deployments = load_template_deployments()
        deployments[deployment_id]["instance_id"] = instance_id
        save_template_deployments(deployments)

        await send_deployment_progress(deployment_id, f"Instance created: {instance_id}", 30)

        # Wait for instance to be ready
        await send_deployment_progress(deployment_id, "Waiting for instance to be ready...", 40)

        max_wait = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < max_wait:
            instance_info = verda_client.get_instance(instance_id)
            if instance_info:
                status = instance_info.get("status", "")
                ip = instance_info.get("ip", "")

                if status == "running" and ip:
                    await send_deployment_progress(deployment_id, f"Instance ready at {ip}", 50)
                    break

                await send_deployment_progress(deployment_id, f"Instance status: {status}...", 45)

            await asyncio.sleep(10)
        else:
            raise Exception("Timeout waiting for instance to be ready")

        # Get final instance info
        instance_info = verda_client.get_instance(instance_id)
        instance_ip = instance_info.get("ip")

        await send_deployment_progress(deployment_id, "Installing software...", 60, "installing")
        deployments = load_template_deployments()
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.INSTALLING.value
        deployments[deployment_id]["instance_ip"] = instance_ip
        save_template_deployments(deployments)

        # The startup script runs automatically on the instance
        # Poll for completion by checking if the container is running
        await send_deployment_progress(deployment_id, "Waiting for deployment to complete...", 70)

        # Wait for the application to be ready
        port = request.parameters.get("port", template.default_port)
        access_url = f"http://{instance_ip}:{port}"

        await asyncio.sleep(30)  # Give time for startup script to run

        await send_deployment_progress(deployment_id, f"Deployment complete! Access: {access_url}", 100, "running")

        deployments = load_template_deployments()
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.RUNNING.value
        deployments[deployment_id]["access_url"] = access_url
        deployments[deployment_id]["completed_at"] = datetime.now().isoformat()
        save_template_deployments(deployments)

    except Exception as e:
        await send_deployment_progress(deployment_id, f"Deployment failed: {str(e)}", 0, "failed")
        deployments = load_template_deployments()
        deployments[deployment_id]["status"] = TemplateDeploymentStatus.FAILED.value
        deployments[deployment_id]["error"] = str(e)
        save_template_deployments(deployments)


# ============================================================================
# SERVE FRONTEND
# ============================================================================

@app.get("/")
async def serve_landing():
    """Serve the landing page"""
    response = FileResponse("index.html")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response

@app.get("/waterfall.mp4")
async def serve_waterfall_video():
    """Serve the background video"""
    response = FileResponse("waterfall.mp4", media_type="video/mp4")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.get("/app")
@app.get("/app.html")
@app.get("/console")
async def serve_console():
    """Serve the main application console"""
    return FileResponse("app.html")

@app.get("/index.html")
async def serve_index():
    """Redirect old index path to app"""
    return FileResponse("index.html")

# ============================================================================
# DASHBOARD STATS
# ============================================================================

@app.get("/api/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics for the current user"""
    try:
        # Get deployments (both containers and instances)
        if DEMO_MODE or verda_client is None:
            containers = []
            instances = []
        else:
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
            "total_deployments": total_deployments,
            "demo_mode": DEMO_MODE
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "active_deployments": 0,
            "api_requests": 0,
            "monthly_cost": 0,
            "uptime": 0,
            "total_deployments": 0,
            "demo_mode": DEMO_MODE
        }

# ============================================================================
# DEPLOYMENTS
# ============================================================================

@app.get("/api/deployments")
async def get_deployments(current_user: User = Depends(get_current_user)):
    """Get all deployments for the current user"""
    try:
        if DEMO_MODE or verda_client is None:
            return {"deployments": [], "demo_mode": True}

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
async def deploy_server(request: DeploymentRequest, current_user: User = Depends(get_current_user)):
    """Deploy a new server - requires authentication"""
    if DEMO_MODE or verda_client is None:
        raise HTTPException(status_code=503, detail="Deployments disabled in demo mode. Configure Verda credentials to enable.")

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
async def stop_deployment(request: StopDeploymentRequest, current_user: User = Depends(get_current_user)):
    """Stop a deployment - requires authentication"""
    if DEMO_MODE or verda_client is None:
        raise HTTPException(status_code=503, detail="Deployments disabled in demo mode.")

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
async def get_deployment_logs(deployment_id: str, current_user: User = Depends(get_current_user)):
    """Get logs for a deployment - requires authentication"""
    if DEMO_MODE or verda_client is None:
        return {"logs": "Logs unavailable in demo mode."}

    try:
        logs = verda_client.get_deployment_logs(deployment_id)
        return {"logs": logs}
    except Exception as e:
        print(f"Error getting logs: {e}")
        return {"logs": "Unable to fetch logs"}


# ============================================================================
# TEMPLATE DEPLOYMENT ENDPOINTS
# ============================================================================

@app.get("/api/templates")
async def get_templates():
    """Get all available deployment templates"""
    templates = []
    for template_id, template in TEMPLATE_REGISTRY.items():
        templates.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "icon": template.icon,
            "default_port": template.default_port,
            "estimated_deploy_time": template.estimated_deploy_time,
            "access_type": template.access_type,
            "features": template.features,
            "color": template.color,
            "parameters": [p.model_dump() for p in template.parameters],
        })
    return {"templates": templates}


@app.post("/api/templates/deploy")
async def deploy_template(
    request: TemplateDeploymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deploy a template to a remote server (requires authentication)"""
    if request.template_id not in TEMPLATE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")

    template = TEMPLATE_REGISTRY[request.template_id]

    # Generate deployment ID
    deployment_id = f"td_{secrets.token_urlsafe(8)}"

    # Get port from parameters
    port = request.parameters.get("port", template.default_port)

    # Create deployment record
    deployments = load_template_deployments()

    # Set up access URL and credentials based on template
    access_url = f"http://{TEMPLATE_SERVER_HOST}:{port}"
    credentials = None

    if template.id == "ubuntu-desktop":
        # Kasm uses HTTPS and has username/password auth
        access_url = f"https://{TEMPLATE_SERVER_HOST}:{port}"
        credentials = {"username": "kasm_user", "password": "cloudpc"}
    elif template.id == "jupyter":
        # Token will be added after deployment completes
        pass

    deployment_record = {
        "id": deployment_id,
        "template_id": template.id,
        "template_name": template.name,
        "name": request.name,
        "host": TEMPLATE_SERVER_HOST,
        "port": port,
        "parameters": request.parameters,
        "status": TemplateDeploymentStatus.PENDING.value,
        "created_at": datetime.now().isoformat(),
        "access_type": template.access_type,
        "access_url": access_url,
        "icon": template.icon,
        "color": template.color,
        "user_id": str(current_user.id),  # Track ownership
    }

    if credentials:
        deployment_record["credentials"] = credentials

    deployments[deployment_id] = deployment_record
    save_template_deployments(deployments)

    # Start deployment in background
    asyncio.create_task(run_deployment_script(deployment_id, template, request))

    return {
        "success": True,
        "deployment_id": deployment_id,
        "message": f"Deployment of {template.name} started. Connect to WebSocket for progress updates.",
        "websocket_url": f"/ws/deployments/{deployment_id}"
    }


@app.get("/api/templates/deployments")
async def get_template_deployments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get template deployments for the current user"""
    deployments = load_template_deployments()
    # Filter deployments by user_id
    user_deployments = [
        d for d in deployments.values()
        if d.get("user_id") == str(current_user.id)
    ]
    return {"deployments": user_deployments}


@app.get("/api/templates/deployments/{deployment_id}")
async def get_template_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific template deployment (requires ownership)"""
    deployments = load_template_deployments()
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    deployment = deployments[deployment_id]
    # Check ownership
    if deployment.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this deployment")

    return deployment


@app.post("/api/templates/deployments/sync")
async def sync_deployment_statuses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync deployment statuses for current user's deployments"""
    deployments = load_template_deployments()
    updated = 0

    try:
        # Get list of running containers - use Docker SDK if available, else SSH
        running_containers = set()

        if DOCKER_AVAILABLE and docker_client:
            # Use Docker SDK directly
            containers = docker_client.containers.list()
            running_containers = set(c.name for c in containers)
        else:
            # Fallback to SSH
            cmd = f'ssh -o StrictHostKeyChecking=no -o BatchMode=yes {TEMPLATE_SERVER_USER}@{TEMPLATE_SERVER_SSH_HOST} "docker ps --format {{{{.Names}}}}"'
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            running_containers = set(stdout.decode().strip().split('\n')) if stdout else set()

        # Container name mapping
        container_names = {
            "jupyter": "jupyter-notebook",
            "ubuntu-desktop": "cloud-computer",
            "ollama": ["ollama", "open-webui"],  # Ollama has 2 containers
            "transformer-labs": "transformerlab-api",
            "minecraft": "minecraft-server",
            "valheim": "valheim-server",
            "terraria": "terraria-server",
            "factorio": "factorio-server",
            "dev-terminal": "dev-terminal",
        }

        # Update each deployment's status (only for current user's deployments)
        user_id = str(current_user.id)
        for dep_id, dep in deployments.items():
            # Only sync user's own deployments
            if dep.get("user_id") != user_id:
                continue

            template_id = dep.get("template_id")
            container_name = dep.get("parameters", {}).get("container_name")

            if not container_name:
                expected = container_names.get(template_id, template_id)
                if isinstance(expected, list):
                    # Check if any of the expected containers are running
                    is_running = any(c in running_containers for c in expected)
                else:
                    container_name = expected
                    is_running = container_name in running_containers
            else:
                is_running = container_name in running_containers

            old_status = dep.get("status")
            if is_running and old_status != "running":
                dep["status"] = "running"
                updated += 1
            elif not is_running and old_status == "running":
                dep["status"] = "stopped"
                updated += 1

        save_template_deployments(deployments)

        return {"success": True, "updated": updated}

    except Exception as e:
        return {"success": False, "error": str(e), "updated": 0}


@app.delete("/api/templates/deployments/{deployment_id}")
async def delete_template_deployment(
    deployment_id: str,
    cleanup: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop container and delete a template deployment record (requires ownership)"""
    deployments = load_template_deployments()
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    deployment = deployments[deployment_id]

    # Check ownership
    if deployment.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this deployment")

    cleanup_result = None

    # Stop and remove the container if cleanup requested
    if cleanup and deployment.get("status") == "running":
        try:
            template_id = deployment.get("template_id")
            container_name = deployment.get("parameters", {}).get("container_name", template_id)

            # Map template IDs to their container names
            container_names = {
                "jupyter": "jupyter-notebook",
                "ubuntu-desktop": "cloud-computer",
                "ollama": ["ollama", "open-webui"],  # Ollama has 2 containers
                "transformer-labs": "transformerlab-api",
                "minecraft": "minecraft-server",
                "valheim": "valheim-server",
                "terraria": "terraria-server",
                "factorio": "factorio-server",
                "dev-terminal": deployment.get("parameters", {}).get("container_name", "dev-terminal")
            }
            containers_to_stop = container_names.get(template_id, container_name)
            if not isinstance(containers_to_stop, list):
                containers_to_stop = [containers_to_stop]

            stopped = []
            if DOCKER_AVAILABLE and docker_client:
                # Use Docker SDK directly
                for cname in containers_to_stop:
                    try:
                        container = docker_client.containers.get(cname)
                        container.stop(timeout=10)
                        container.remove()
                        stopped.append(cname)
                    except docker.errors.NotFound:
                        pass
                    except Exception as e:
                        stopped.append(f"{cname}: {str(e)}")
                cleanup_result = f"Stopped containers: {', '.join(stopped)}" if stopped else "No containers found"
            else:
                # Fallback to SSH
                host = deployment.get("host", TEMPLATE_SERVER_HOST)
                ssh_user = TEMPLATE_SERVER_USER
                for cname in containers_to_stop:
                    cmd = [
                        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                        f"{ssh_user}@{host}",
                        f"docker stop {shlex.quote(cname)}; docker rm {shlex.quote(cname)}"
                    ]
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    if process.returncode == 0:
                        stopped.append(cname)
                cleanup_result = f"Stopped containers: {', '.join(stopped)}" if stopped else "Cleanup attempted"

        except Exception as e:
            cleanup_result = f"Cleanup warning: {str(e)}"

    # Delete the deployment record
    del deployments[deployment_id]
    save_template_deployments(deployments)

    return {
        "success": True,
        "message": "Deployment stopped and removed",
        "cleanup": cleanup_result
    }


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID"""
    if template_id not in TEMPLATE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    template = TEMPLATE_REGISTRY[template_id]
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category.value,
        "icon": template.icon,
        "script_path": template.script_path,
        "predeployment_required": template.predeployment_required,
        "default_port": template.default_port,
        "estimated_deploy_time": template.estimated_deploy_time,
        "access_type": template.access_type,
        "features": template.features,
        "color": template.color,
        "parameters": [p.model_dump() for p in template.parameters],
    }


@app.websocket("/ws/deployments/{deployment_id}")
async def deployment_websocket(websocket: WebSocket, deployment_id: str, token: str = None):
    """WebSocket endpoint for real-time deployment progress (requires auth via ?token= query param)"""
    from auth import decode_access_token, decode_supabase_token, decode_clerk_token, get_clerk_jwks, get_supabase_jwks
    from database import get_db_context

    # Authenticate via token query parameter
    if not token:
        await websocket.close(code=4001, reason="Authentication required. Pass ?token=<jwt>")
        return

    # Decode token (try Clerk JWT, then custom JWT, then Supabase)
    user_id = None

    # 1. Try Clerk JWT first
    jwks = await get_clerk_jwks()
    if jwks:
        clerk_payload = decode_clerk_token(token, jwks)
        if clerk_payload:
            clerk_user_id = clerk_payload.get("sub")
            if clerk_user_id:
                # Resolve clerk_user_id to internal UUID via DB lookup
                async with get_db_context() as db:
                    result = await db.execute(
                        select(User.id).where(User.clerk_user_id == clerk_user_id)
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        user_id = str(row)

    # 2. Try custom JWT (legacy)
    if not user_id:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")

    # 3. Try Supabase JWT (legacy)
    if not user_id:
        supabase_jwks = await get_supabase_jwks()
        supabase_payload = decode_supabase_token(token, supabase_jwks)
        if supabase_payload:
            user_id = supabase_payload.get("sub")

    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify deployment ownership
    deployments = load_template_deployments()
    if deployment_id not in deployments:
        await websocket.close(code=4004, reason="Deployment not found")
        return
    deployment = deployments[deployment_id]
    if deployment.get("user_id") != user_id:
        await websocket.close(code=4003, reason="Not authorized for this deployment")
        return

    await websocket.accept()

    # Only set connection if no existing connection (prevent hijacking)
    if deployment_id not in active_connections:
        active_connections[deployment_id] = websocket

    try:
        # Send initial status
        await websocket.send_json({
            "deployment_id": deployment_id,
            "message": "Connected to deployment progress stream",
            "status": deployment.get("status", "unknown"),
            "timestamp": datetime.now().isoformat()
        })

        # Keep connection alive and wait for messages
        while True:
            try:
                # Receive any client messages (for keep-alive)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        pass
    finally:
        if deployment_id in active_connections and active_connections[deployment_id] is websocket:
            del active_connections[deployment_id]


# ============================================================================
# GPU OPTIONS
# ============================================================================

# Demo GPU data for when Verda is not available
DEMO_GPUS = [
    {"name": "Tesla-V100-16GB", "display_name": "Tesla V100 16GB", "memory": "16GB", "serverless_spot_price": 0.076, "instance_spot_price": 0.12},
    {"name": "RTX-A6000", "display_name": "RTX A6000", "memory": "48GB", "serverless_spot_price": 0.125, "instance_spot_price": 0.18},
    {"name": "A100-40GB", "display_name": "A100 40GB", "memory": "40GB", "serverless_spot_price": 0.238, "instance_spot_price": 0.35},
    {"name": "RTX-6000-Ada", "display_name": "RTX 6000 Ada", "memory": "48GB", "serverless_spot_price": 0.285, "instance_spot_price": 0.40},
    {"name": "L40S", "display_name": "L40S", "memory": "48GB", "serverless_spot_price": 0.315, "instance_spot_price": 0.45},
    {"name": "A100-80GB", "display_name": "A100 80GB", "memory": "80GB", "serverless_spot_price": 0.425, "instance_spot_price": 0.60},
    {"name": "H100", "display_name": "H100", "memory": "80GB", "serverless_spot_price": 0.850, "instance_spot_price": 1.20},
]

@app.get("/api/gpus")
async def get_gpus():
    """Get available GPU types"""
    try:
        if DEMO_MODE or verda_client is None:
            gpus = DEMO_GPUS
        else:
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
# COMPUTE - Direct GPU Rental
# ============================================================================

# In-memory store for compute instances (in production, use database)
COMPUTE_INSTANCES = {}

class ComputeInstanceRequest(BaseModel):
    name: str
    gpu_type: str
    ssh_public_key: str
    use_spot: bool = True
    quantity: int = Field(default=1, ge=1, le=4)


@app.get("/api/compute/gpus")
async def get_compute_gpus():
    """Get available GPU types from all providers (Verda + Targon)"""
    all_gpus = []

    try:
        if DEMO_MODE or verda_client is None:
            # Demo mode - return sample GPU catalog with markup applied
            demo_gpus = [
                {"name": "Tesla V100 16GB", "display_name": "Tesla V100", "memory": "16GB", "spot_price": apply_markup(0.076, "verda"), "on_demand_price": apply_markup(0.150, "verda"), "available": True, "available_count": 12, "provider": "verda"},
                {"name": "RTX A6000 48GB", "display_name": "RTX A6000", "memory": "48GB", "spot_price": apply_markup(0.162, "verda"), "on_demand_price": apply_markup(0.324, "verda"), "available": True, "available_count": 8, "provider": "verda"},
                {"name": "A100 SXM4 40GB", "display_name": "A100 40GB", "memory": "40GB", "spot_price": apply_markup(0.238, "verda"), "on_demand_price": apply_markup(0.476, "verda"), "available": True, "available_count": 5, "provider": "verda"},
                {"name": "RTX 6000 Ada 48GB", "display_name": "RTX 6000 Ada", "memory": "48GB", "spot_price": apply_markup(0.273, "verda"), "on_demand_price": apply_markup(0.546, "verda"), "available": True, "available_count": 6, "provider": "verda"},
                {"name": "L40S 48GB", "display_name": "L40S", "memory": "48GB", "spot_price": apply_markup(0.302, "verda"), "on_demand_price": apply_markup(0.604, "verda"), "available": True, "available_count": 4, "provider": "verda"},
                {"name": "A100 SXM4 80GB", "display_name": "A100 80GB", "memory": "80GB", "spot_price": apply_markup(0.638, "verda"), "on_demand_price": apply_markup(1.276, "verda"), "available": True, "available_count": 3, "provider": "verda"},
                {"name": "H100 SXM5 80GB", "display_name": "H100 (Verda)", "memory": "80GB", "spot_price": apply_markup(1.499, "verda"), "on_demand_price": apply_markup(2.998, "verda"), "available": True, "available_count": 2, "provider": "verda"},
                {"name": "H200 SXM6 141GB", "display_name": "H200 (Verda)", "memory": "141GB", "spot_price": apply_markup(2.249, "verda"), "on_demand_price": apply_markup(4.498, "verda"), "available": False, "available_count": 0, "provider": "verda"},
                {"name": "B200 SXM6 180GB", "display_name": "B200", "memory": "180GB", "spot_price": apply_markup(2.999, "verda"), "on_demand_price": apply_markup(5.998, "verda"), "available": False, "available_count": 0, "provider": "verda"},
            ]
            all_gpus.extend(demo_gpus)
        else:
            # Get real GPU pricing from Verda
            verda_gpus = verda_client.get_available_gpus()
            for gpu in verda_gpus:
                base_price = gpu.get('instance_spot_price', 0)
                all_gpus.append({
                    "name": gpu['name'],
                    "display_name": gpu.get('display_name', gpu['name']),
                    "memory": gpu.get('memory', 'N/A'),
                    "spot_price": apply_markup(base_price, "verda"),
                    "on_demand_price": apply_markup(base_price * 2, "verda"),
                    "available": True,
                    "available_count": gpu.get('available_count', None),
                    "provider": "verda"
                })

    except Exception as e:
        print(f"Error getting Verda GPUs: {e}")

    # Add Targon GPUs
    try:
        if targon_client:
            targon_gpus = targon_client.get_available_gpus()
            for gpu in targon_gpus:
                base_price = gpu.get('instance_spot_price', 0)
                all_gpus.append({
                    "name": gpu['name'],
                    "display_name": gpu.get('display_name', gpu['name']),
                    "memory": gpu.get('memory', 'N/A'),
                    "spot_price": apply_markup(base_price, "targon"),
                    "on_demand_price": apply_markup(base_price * 1.5, "targon"),
                    "available": True,
                    "available_count": gpu.get('available_count', None),
                    "provider": "targon"
                })
        elif DEMO_MODE:
            # Demo Targon GPUs
            demo_targon = [
                {"name": "H100 SXM5 80GB (Targon)", "display_name": "H100 (Targon)", "memory": "80GB", "spot_price": apply_markup(1.45, "targon"), "on_demand_price": apply_markup(2.18, "targon"), "available": True, "available_count": 5, "provider": "targon"},
                {"name": "H200 SXM5 141GB (Targon)", "display_name": "H200 (Targon)", "memory": "141GB", "spot_price": apply_markup(2.25, "targon"), "on_demand_price": apply_markup(3.38, "targon"), "available": True, "available_count": 3, "provider": "targon"},
            ]
            all_gpus.extend(demo_targon)
    except Exception as e:
        print(f"Error getting Targon GPUs: {e}")

    # Deduplicate by GPU type - keep only the cheapest option for each
    # Normalize GPU names for comparison (e.g., "H100 SXM5 80GB" and "H100 SXM5 80GB (Targon)" -> "H100 80GB")
    def normalize_gpu_name(name):
        """Extract core GPU identifier for deduplication"""
        name = name.upper()
        # Remove provider suffixes
        for suffix in ['(VERDA)', '(TARGON)', 'VERDA', 'TARGON']:
            name = name.replace(suffix, '')
        # Extract key identifiers
        for gpu_type in ['B300', 'B200', 'H200', 'H100', 'A100', 'L40S', 'L40', 'A6000', 'RTX 6000', 'V100', 'RTX']:
            if gpu_type in name:
                # Include memory size if present
                import re
                mem_match = re.search(r'(\d+)\s*GB', name)
                mem = mem_match.group(1) + 'GB' if mem_match else ''
                return f"{gpu_type} {mem}".strip()
        return name.strip()

    # Group by normalized name and keep cheapest
    gpu_map = {}
    for gpu in all_gpus:
        key = normalize_gpu_name(gpu['name'])
        if key not in gpu_map or gpu['spot_price'] < gpu_map[key]['spot_price']:
            # Update display name to remove provider suffix since we're showing the best price
            gpu_copy = gpu.copy()
            gpu_copy['display_name'] = gpu_copy['display_name'].replace(' (Verda)', '').replace(' (Targon)', '')
            gpu_map[key] = gpu_copy

    # Convert back to list and sort by price
    deduplicated_gpus = list(gpu_map.values())
    deduplicated_gpus.sort(key=lambda x: x['spot_price'])

    return {"gpus": deduplicated_gpus}


@app.get("/api/compute/instances")
async def list_compute_instances(current_user: User = Depends(get_current_user)):
    """List active compute instances from all providers - requires authentication"""
    all_instances = []

    try:
        if DEMO_MODE or verda_client is None:
            # Return in-memory instances for demo
            all_instances.extend(list(COMPUTE_INSTANCES.values()))
        else:
            # Get real instances from Verda
            verda_instances = verda_client.list_instances()
            for inst in verda_instances:
                all_instances.append({
                    "id": inst.get('id'),
                    "name": inst.get('hostname', inst.get('name', 'Unknown')),
                    "gpu_type": inst.get('instance_type', 'Unknown'),
                    "status": inst.get('status', 'unknown'),
                    "ip": inst.get('ip'),
                    "hourly_cost": inst.get('hourly_cost', 0),
                    "created_at": inst.get('created_at'),
                    "provider": "verda"
                })

    except Exception as e:
        print(f"Error listing Verda instances: {e}")

    # Get Targon instances
    try:
        if targon_client and targon_client.authenticated:
            targon_instances = targon_client.list_instances()
            for inst in targon_instances:
                all_instances.append({
                    "id": inst.get('id'),
                    "name": inst.get('name', 'Unknown'),
                    "gpu_type": inst.get('gpu_type', 'Unknown'),
                    "status": inst.get('status', 'unknown'),
                    "ip": inst.get('ip'),
                    "ssh_command": inst.get('ssh_command'),
                    "hourly_cost": inst.get('hourly_cost', 0),
                    "provider": "targon"
                })
    except Exception as e:
        print(f"Error listing Targon instances: {e}")

    return {"instances": all_instances}


@app.post("/api/compute/instances")
async def create_compute_instance(request: ComputeInstanceRequest, current_user: User = Depends(get_current_user)):
    """Create one or more compute instances - requires authentication"""
    try:
        # Validate SSH key
        if not request.ssh_public_key or not request.ssh_public_key.strip().startswith('ssh-'):
            raise HTTPException(status_code=400, detail="Valid SSH public key is required")

        quantity = request.quantity
        created_instances = []

        if DEMO_MODE or verda_client is None:
            # Demo mode - create fake instances
            for i in range(quantity):
                instance_id = f"demo-{secrets.token_hex(4)}"
                instance_name = f"{request.name}-{i+1}" if quantity > 1 else request.name
                instance = {
                    "id": instance_id,
                    "name": instance_name,
                    "gpu_type": request.gpu_type,
                    "status": "starting",
                    "ip": None,
                    "hourly_cost": 0.091,  # Demo price with markup
                    "created_at": datetime.now().isoformat(),
                    "ssh_key_added": True
                }
                COMPUTE_INSTANCES[instance_id] = instance
                created_instances.append(instance)

                # Simulate startup for each instance
                async def simulate_startup(inst_id):
                    await asyncio.sleep(5 + i)  # Stagger startups
                    if inst_id in COMPUTE_INSTANCES:
                        COMPUTE_INSTANCES[inst_id]["status"] = "running"
                        COMPUTE_INSTANCES[inst_id]["ip"] = f"10.0.{secrets.randbelow(255)}.{secrets.randbelow(255)}"

                asyncio.create_task(simulate_startup(instance_id))

            message = f"{quantity} instances are being provisioned" if quantity > 1 else f"Instance {request.name} is being provisioned"
            return {
                "success": True,
                "message": message,
                "instances": created_instances,
                "instance": created_instances[0] if created_instances else None  # Backwards compat
            }

        # Create real instances via Verda
        for i in range(quantity):
            instance_name = f"{request.name}-{i+1}" if quantity > 1 else request.name
            result = verda_client.create_instance(
                name=instance_name,
                gpu_name=request.gpu_type,
                use_spot=request.use_spot,
                ssh_public_key=request.ssh_public_key
            )

            if result:
                created_instances.append({
                    "id": result.get('id'),
                    "name": instance_name,
                    "gpu_type": request.gpu_type,
                    "status": result.get('status', 'starting'),
                    "ip": result.get('ip')
                })

        if created_instances:
            message = f"{len(created_instances)} instances are being provisioned" if len(created_instances) > 1 else f"Instance {request.name} is being provisioned"
            return {
                "success": True,
                "message": message,
                "instances": created_instances,
                "instance": created_instances[0] if created_instances else None
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create any instances")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating compute instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/compute/instances/{instance_id}")
async def terminate_compute_instance(instance_id: str, current_user: User = Depends(get_current_user)):
    """Terminate a compute instance - requires authentication"""
    try:
        if DEMO_MODE or verda_client is None:
            # Demo mode - remove from in-memory store
            if instance_id in COMPUTE_INSTANCES:
                del COMPUTE_INSTANCES[instance_id]
                return {"success": True, "message": "Instance terminated"}
            else:
                raise HTTPException(status_code=404, detail="Instance not found")

        # Terminate real instance via Verda
        result = verda_client.delete_instance(instance_id)
        if result:
            return {"success": True, "message": "Instance terminated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to terminate instance")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error terminating instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_api_keys(current_user: User = Depends(get_current_user)):
    """Get all API keys for the current user"""
    try:
        keys = load_api_keys()
        user_keys = [k for k in keys if k.get("user_id") == str(current_user.id)]
        return {"keys": user_keys}
    except Exception as e:
        print(f"Error loading API keys: {e}")
        return {"keys": []}

@app.post("/api/keys/generate")
async def generate_api_key(request: APIKeyRequest, current_user: User = Depends(get_current_user)):
    """Generate a new API key for the current user"""
    try:
        import secrets

        # Generate key
        key = f"vf_live_{secrets.token_urlsafe(32)}"

        # Load existing keys
        keys = load_api_keys()

        # Add new key
        new_key = {
            "id": secrets.token_urlsafe(8),
            "user_id": str(current_user.id),
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
async def revoke_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    """Revoke an API key (must be owned by current user)"""
    try:
        keys = load_api_keys()
        # Verify ownership before deleting
        key_to_delete = next((k for k in keys if k['id'] == key_id), None)
        if not key_to_delete:
            raise HTTPException(status_code=404, detail="API key not found")
        if key_to_delete.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to revoke this API key")
        keys = [k for k in keys if k['id'] != key_id]
        save_api_keys(keys)

        return {"success": True, "message": "API key revoked"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error revoking key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# USAGE ANALYTICS
# ============================================================================

@app.get("/api/usage")
async def get_usage_analytics(current_user: User = Depends(get_current_user)):
    """Get detailed usage analytics for the current user"""
    try:
        stats = load_usage_stats()
        keys = load_api_keys()
        # Filter to current user's keys only
        keys = [k for k in keys if k.get("user_id") == str(current_user.id)]

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
async def record_usage(key_id: str, deployment_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
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

def _default_user_settings():
    """Return default settings for a new user"""
    return {
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

def load_settings(user_id: str = None):
    """Load settings from file, scoped by user_id"""
    default_settings = _default_user_settings()
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            saved = json.load(f)
            if user_id:
                user_settings = saved.get(user_id, {})
                for key in default_settings:
                    if key not in user_settings:
                        user_settings[key] = default_settings[key]
                return user_settings
            # Legacy: merge with defaults
            for key in default_settings:
                if key not in saved:
                    saved[key] = default_settings[key]
            return saved
    return default_settings

def save_settings(settings, user_id: str = None):
    """Save settings to file, scoped by user_id"""
    if user_id:
        all_settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
        all_settings[user_id] = settings
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(all_settings, f, indent=2)
    else:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

@app.get("/api/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get account settings for the current user"""
    return load_settings(user_id=str(current_user.id))

class AccountUpdateRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None

@app.put("/api/settings/account")
async def update_account(request: AccountUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update account settings for the current user"""
    uid = str(current_user.id)
    settings = load_settings(user_id=uid)
    if request.email:
        settings["account"]["email"] = request.email
    if request.name:
        settings["account"]["name"] = request.name
    if request.company is not None:
        settings["account"]["company"] = request.company
    save_settings(settings, user_id=uid)
    return {"success": True, "account": settings["account"]}

class NotificationUpdateRequest(BaseModel):
    deployment_started: Optional[bool] = None
    deployment_stopped: Optional[bool] = None
    deployment_failed: Optional[bool] = None
    usage_alerts: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    email_notifications: Optional[bool] = None

@app.put("/api/settings/notifications")
async def update_notifications(request: NotificationUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update notification preferences for the current user"""
    uid = str(current_user.id)
    settings = load_settings(user_id=uid)
    updates = request.model_dump(exclude_none=True)
    for key, value in updates.items():
        settings["notifications"][key] = value
    save_settings(settings, user_id=uid)
    return {"success": True, "notifications": settings["notifications"]}

class WebhookRequest(BaseModel):
    url: str
    events: List[str]
    name: Optional[str] = None

@app.get("/api/settings/webhooks")
async def get_webhooks(current_user: User = Depends(get_current_user)):
    """Get all webhooks for the current user"""
    settings = load_settings(user_id=str(current_user.id))
    return {"webhooks": settings.get("webhooks", [])}

@app.post("/api/settings/webhooks")
async def create_webhook(request: WebhookRequest, current_user: User = Depends(get_current_user)):
    """Create a new webhook for the current user"""
    uid = str(current_user.id)
    settings = load_settings(user_id=uid)
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
    save_settings(settings, user_id=uid)
    return {"success": True, "webhook": webhook}

@app.delete("/api/settings/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, current_user: User = Depends(get_current_user)):
    """Delete a webhook"""
    uid = str(current_user.id)
    settings = load_settings(user_id=uid)
    settings["webhooks"] = [w for w in settings.get("webhooks", []) if w["id"] != webhook_id]
    save_settings(settings, user_id=uid)
    return {"success": True, "message": "Webhook deleted"}

@app.put("/api/settings/webhooks/{webhook_id}/toggle")
async def toggle_webhook(webhook_id: str, current_user: User = Depends(get_current_user)):
    """Toggle webhook active status"""
    uid = str(current_user.id)
    settings = load_settings(user_id=uid)
    for webhook in settings.get("webhooks", []):
        if webhook["id"] == webhook_id:
            webhook["active"] = not webhook.get("active", True)
            save_settings(settings, user_id=uid)
            return {"success": True, "active": webhook["active"]}
    raise HTTPException(status_code=404, detail="Webhook not found")

# ============================================================================
# DEPLOYMENT METRICS
# ============================================================================

METRICS_FILE = "deployment_metrics.json"

def load_metrics():
    """Load deployment metrics from file"""
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metrics(metrics):
    """Save deployment metrics to file"""
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

def generate_mock_metrics(deployment_id: str):
    """Generate realistic mock metrics for a deployment"""
    import random

    # Base values that drift slightly over time
    base_cpu = random.uniform(15, 45)
    base_memory = random.uniform(30, 60)
    base_latency = random.uniform(50, 150)

    return {
        "deployment_id": deployment_id,
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": round(base_cpu + random.uniform(-5, 15), 1),
        "memory_percent": round(base_memory + random.uniform(-5, 10), 1),
        "memory_used_mb": round((base_memory / 100) * 40960, 0),  # Assuming 40GB GPU
        "memory_total_mb": 40960,
        "gpu_utilization": round(random.uniform(20, 85), 1),
        "gpu_memory_used_mb": round(random.uniform(8000, 32000), 0),
        "gpu_memory_total_mb": 40960,
        "network_rx_mbps": round(random.uniform(1, 50), 2),
        "network_tx_mbps": round(random.uniform(5, 100), 2),
        "requests_per_minute": random.randint(0, 120),
        "avg_latency_ms": round(base_latency + random.uniform(-20, 40), 1),
        "p95_latency_ms": round(base_latency * 1.5 + random.uniform(0, 50), 1),
        "p99_latency_ms": round(base_latency * 2 + random.uniform(0, 80), 1),
        "error_rate_percent": round(random.uniform(0, 2.5), 2),
        "success_count_1h": random.randint(100, 5000),
        "error_count_1h": random.randint(0, 50),
        "uptime_seconds": random.randint(3600, 86400 * 7),
        "status": "healthy" if random.random() > 0.05 else "degraded"
    }

@app.get("/api/deployments/{deployment_id}/metrics")
async def get_deployment_metrics(deployment_id: str, current_user: User = Depends(get_current_user)):
    """Get real-time metrics for a deployment - requires authentication"""
    try:
        # In production, this would query actual monitoring systems
        # For now, generate realistic mock data
        metrics = generate_mock_metrics(deployment_id)

        # Store latest metrics
        all_metrics = load_metrics()
        if deployment_id not in all_metrics:
            all_metrics[deployment_id] = {"history": []}

        all_metrics[deployment_id]["latest"] = metrics
        all_metrics[deployment_id]["history"].append({
            "timestamp": metrics["timestamp"],
            "cpu": metrics["cpu_percent"],
            "memory": metrics["memory_percent"],
            "latency": metrics["avg_latency_ms"],
            "requests": metrics["requests_per_minute"]
        })

        # Keep only last 60 data points (1 hour at 1 min intervals)
        all_metrics[deployment_id]["history"] = all_metrics[deployment_id]["history"][-60:]
        save_metrics(all_metrics)

        return metrics
    except Exception as e:
        print(f"Error getting metrics: {e}")
        return {"error": str(e)}

@app.get("/api/deployments/{deployment_id}/metrics/history")
async def get_deployment_metrics_history(deployment_id: str, period: str = "1h", current_user: User = Depends(get_current_user)):
    """Get historical metrics for a deployment - requires authentication"""
    try:
        all_metrics = load_metrics()

        if deployment_id not in all_metrics:
            return {"history": [], "period": period}

        history = all_metrics[deployment_id].get("history", [])

        # Filter based on period
        if period == "1h":
            history = history[-60:]
        elif period == "6h":
            history = history[-360:]
        elif period == "24h":
            history = history[-1440:]

        return {"history": history, "period": period}
    except Exception as e:
        print(f"Error getting metrics history: {e}")
        return {"history": [], "period": period}

# ============================================================================
# USAGE LIMITS & RATE LIMITING
# ============================================================================

LIMITS_FILE = "usage_limits.json"

def load_limits():
    """Load usage limits configuration"""
    default_limits = {
        "api_requests_per_minute": 60,
        "api_requests_per_day": 10000,
        "max_concurrent_deployments": 5,
        "max_api_keys": 10,
        "max_webhooks": 5,
        "cost_alert_threshold": 100.00,
        "auto_stop_threshold": 500.00,
        "enabled": True
    }
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, 'r') as f:
            saved = json.load(f)
            for key in default_limits:
                if key not in saved:
                    saved[key] = default_limits[key]
            return saved
    return default_limits

def save_limits(limits):
    """Save usage limits configuration"""
    with open(LIMITS_FILE, 'w') as f:
        json.dump(limits, f, indent=2)

@app.get("/api/limits")
async def get_limits(current_user: User = Depends(get_current_user)):
    """Get current usage limits for the current user"""
    uid = str(current_user.id)
    limits = load_limits()

    # Add current usage stats scoped to user
    keys = load_api_keys()
    user_keys = [k for k in keys if k.get("user_id") == uid]
    settings = load_settings(user_id=uid)
    stats = load_usage_stats()

    today = datetime.now().strftime("%Y-%m-%d")
    today_requests = stats.get("requests_by_day", {}).get(today, 0)

    return {
        "limits": limits,
        "current_usage": {
            "api_keys_count": len(user_keys),
            "webhooks_count": len(settings.get("webhooks", [])),
            "requests_today": today_requests,
            "estimated_monthly_cost": settings.get("billing", {}).get("current_month", 0)
        }
    }

class LimitsUpdateRequest(BaseModel):
    api_requests_per_minute: Optional[int] = None
    api_requests_per_day: Optional[int] = None
    max_concurrent_deployments: Optional[int] = None
    max_api_keys: Optional[int] = None
    max_webhooks: Optional[int] = None
    cost_alert_threshold: Optional[float] = None
    auto_stop_threshold: Optional[float] = None
    enabled: Optional[bool] = None

@app.put("/api/limits")
async def update_limits(request: LimitsUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update usage limits for the current user"""
    limits = load_limits()
    updates = request.model_dump(exclude_none=True)
    for key, value in updates.items():
        limits[key] = value
    save_limits(limits)
    return {"success": True, "limits": limits}

# ============================================================================
# COST TRACKING
# ============================================================================

COST_FILE = "cost_tracking.json"

def load_cost_data():
    """Load cost tracking data"""
    default_data = {
        "hourly_rates": {},  # deployment_id -> hourly_rate
        "usage_hours": {},   # deployment_id -> {"date": hours}
        "daily_costs": {},   # "YYYY-MM-DD" -> cost
        "monthly_totals": {} # "YYYY-MM" -> cost
    }
    if os.path.exists(COST_FILE):
        with open(COST_FILE, 'r') as f:
            return json.load(f)
    return default_data

def save_cost_data(data):
    """Save cost tracking data"""
    with open(COST_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def record_deployment_cost(deployment_id: str, gpu_type: str, hours: float = 1.0):
    """Record cost for a deployment"""
    # GPU hourly rates (spot prices)
    gpu_rates = {
        "Tesla-V100-16GB": 0.076,
        "RTX-A6000": 0.125,
        "A100-40GB": 0.238,
        "RTX-6000-Ada": 0.285,
        "L40S": 0.315,
        "A100-80GB": 0.425,
        "H100": 0.850,
    }

    rate = gpu_rates.get(gpu_type, 0.20)
    cost = rate * hours

    data = load_cost_data()
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # Update hourly rate tracking
    data["hourly_rates"][deployment_id] = rate

    # Update daily cost
    if today not in data["daily_costs"]:
        data["daily_costs"][today] = 0
    data["daily_costs"][today] += cost

    # Update monthly total
    if month not in data["monthly_totals"]:
        data["monthly_totals"][month] = 0
    data["monthly_totals"][month] += cost

    save_cost_data(data)

    # Note: billing in settings is updated per-user at the endpoint level
    # This function records aggregate cost data only

    return cost

@app.get("/api/costs")
async def get_cost_breakdown(current_user: User = Depends(get_current_user)):
    """Get detailed cost breakdown for the current user"""
    data = load_cost_data()
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m")

    # Get last 30 days of daily costs
    daily_costs = []
    for i in range(30):
        day = (today - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
        daily_costs.append({
            "date": day,
            "cost": round(data.get("daily_costs", {}).get(day, 0), 2)
        })
    daily_costs.reverse()

    # Calculate projections
    days_elapsed = today.day
    current_spend = data.get("monthly_totals", {}).get(current_month, 0)
    if days_elapsed > 0:
        daily_avg = current_spend / days_elapsed
        projected_monthly = daily_avg * 30
    else:
        projected_monthly = 0

    return {
        "current_month": round(current_spend, 2),
        "last_month": round(data.get("monthly_totals", {}).get(last_month, 0), 2),
        "projected_monthly": round(projected_monthly, 2),
        "daily_costs": daily_costs,
        "hourly_rates": data.get("hourly_rates", {}),
        "active_deployments_cost_per_hour": sum(data.get("hourly_rates", {}).values())
    }

@app.post("/api/costs/simulate")
async def simulate_cost(hours: float = 1.0, deployment_id: str = "demo", gpu_type: str = "A100-40GB", current_user: User = Depends(get_current_user)):
    """Simulate recording a cost (for testing)"""
    cost = record_deployment_cost(deployment_id, gpu_type, hours)
    return {"success": True, "cost_recorded": round(cost, 4), "deployment_id": deployment_id}

# ============================================================================
# DANGER ZONE OPERATIONS
# ============================================================================

@app.post("/api/danger/reset-usage")
async def reset_usage_stats(current_user: User = Depends(get_current_user)):
    """Reset all usage statistics (danger zone) - requires authentication"""
    default_stats = {
        "total_requests": 0,
        "requests_by_key": {},
        "requests_by_day": {},
        "requests_by_deployment": {},
        "last_updated": datetime.now().isoformat()
    }
    save_usage_stats(default_stats)
    return {"success": True, "message": "Usage statistics have been reset"}

@app.post("/api/danger/revoke-all-keys")
async def revoke_all_api_keys(current_user: User = Depends(get_current_user)):
    """Revoke all API keys (danger zone) - requires authentication"""
    save_api_keys([])
    return {"success": True, "message": "All API keys have been revoked"}

@app.post("/api/danger/stop-all-deployments")
async def stop_all_deployments(current_user: User = Depends(get_current_user)):
    """Stop all active deployments (danger zone) - requires authentication"""
    if DEMO_MODE or verda_client is None:
        return {"success": False, "message": "Cannot stop deployments in demo mode"}

    try:
        # Get all deployments
        containers = verda_client.list_deployments()
        instances = verda_client.list_instances()

        stopped = 0
        errors = []

        # Stop containers
        for c in containers:
            try:
                verda_client.delete_deployment(c.get('id'))
                stopped += 1
            except Exception as e:
                errors.append(f"Container {c.get('id')}: {str(e)}")

        # Stop instances
        for i in instances:
            try:
                verda_client.delete_instance(i.get('id'))
                stopped += 1
            except Exception as e:
                errors.append(f"Instance {i.get('id')}: {str(e)}")

        return {
            "success": True,
            "stopped_count": stopped,
            "errors": errors if errors else None,
            "message": f"Stopped {stopped} deployments"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============================================================================
# MULTI-TENANT USER ENDPOINTS (Database-backed)
# ============================================================================

if DB_AVAILABLE:
    from decimal import Decimal

    @app.get("/api/user/deployments")
    async def get_user_deployments(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Get deployments for the current authenticated user"""
        result = await db.execute(
            select(Deployment)
            .where(Deployment.user_id == current_user.id)
            .order_by(Deployment.created_at.desc())
        )
        deployments = result.scalars().all()

        return {
            "deployments": [
                {
                    "id": str(d.id),
                    "template_id": d.template_id,
                    "name": d.name,
                    "status": d.status.value,
                    "provider": d.provider.value,
                    "machine_type": d.machine_type,
                    "host": d.host,
                    "port": d.port,
                    "access_url": d.access_url,
                    "config": d.config,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "started_at": d.started_at.isoformat() if d.started_at else None,
                    "last_accessed_at": d.last_accessed_at.isoformat() if d.last_accessed_at else None,
                }
                for d in deployments
            ]
        }

    @app.post("/api/user/deployments")
    async def create_user_deployment(
        request: TemplateDeploymentRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """
        Create a new deployment for the authenticated user.
        Checks tier limits before allowing deployment.
        """
        # Check if user has exceeded their compute minutes
        if current_user.compute_minutes_used >= current_user.compute_minutes_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Compute limit reached ({current_user.compute_minutes_limit} minutes). Please upgrade your plan."
            )

        if request.template_id not in TEMPLATE_REGISTRY:
            raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")

        template = TEMPLATE_REGISTRY[request.template_id]
        port = request.parameters.get("port", template.default_port)

        # Set up access URL
        access_url = f"http://{TEMPLATE_SERVER_HOST}:{port}"
        if template.id == "ubuntu-desktop":
            access_url = f"https://{TEMPLATE_SERVER_HOST}:{port}"

        # Create deployment record in database
        deployment = Deployment(
            user_id=current_user.id,
            template_id=request.template_id,
            name=request.name,
            status=DeploymentStatus.PENDING,
            provider=ComputeProvider.VERDA,
            host=TEMPLATE_SERVER_HOST,
            port=port,
            access_url=access_url,
            config={
                "parameters": request.parameters,
                "template_name": template.name,
                "icon": template.icon,
                "color": template.color,
                "access_type": template.access_type,
            }
        )
        db.add(deployment)
        await db.flush()

        deployment_id = str(deployment.id)

        # Also save to JSON file for backwards compatibility with existing deployment scripts
        deployments = load_template_deployments()
        deployment_record = {
            "id": deployment_id,
            "template_id": template.id,
            "template_name": template.name,
            "name": request.name,
            "host": TEMPLATE_SERVER_HOST,
            "port": port,
            "parameters": request.parameters,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "access_type": template.access_type,
            "access_url": access_url,
            "icon": template.icon,
            "color": template.color,
            "user_id": str(current_user.id),
        }
        deployments[deployment_id] = deployment_record
        save_template_deployments(deployments)

        # Start deployment in background
        asyncio.create_task(run_deployment_script(deployment_id, template, request))

        await db.commit()

        return {
            "success": True,
            "deployment_id": deployment_id,
            "message": f"Deployment of {template.name} started",
            "websocket_url": f"/ws/deployments/{deployment_id}"
        }

    @app.delete("/api/user/deployments/{deployment_id}")
    async def delete_user_deployment(
        deployment_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Delete a deployment owned by the current user"""
        from uuid import UUID as PyUUID

        try:
            dep_uuid = PyUUID(deployment_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deployment ID format")

        result = await db.execute(
            select(Deployment)
            .where(Deployment.id == dep_uuid)
            .where(Deployment.user_id == current_user.id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Stop the actual container (reuse existing logic)
        # This calls the template deletion logic
        try:
            json_deployments = load_template_deployments()
            if deployment_id in json_deployments:
                del json_deployments[deployment_id]
                save_template_deployments(json_deployments)
        except Exception:
            pass

        await db.delete(deployment)
        await db.commit()

        return {"success": True, "message": "Deployment deleted"}

    @app.get("/api/user/usage")
    async def get_user_usage(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Get usage statistics for the current user"""
        # Get current month's usage records
        current_month = datetime.now().strftime("%Y-%m")

        result = await db.execute(
            select(UsageRecord)
            .where(UsageRecord.user_id == current_user.id)
            .where(UsageRecord.billing_month == current_month)
        )
        records = result.scalars().all()

        total_minutes = sum(r.minutes for r in records)
        total_cost = sum(r.cost_usd for r in records)

        return {
            "user_id": str(current_user.id),
            "tier": current_user.tier.value,
            "compute_minutes_used": current_user.compute_minutes_used,
            "compute_minutes_limit": current_user.compute_minutes_limit,
            "storage_bytes_used": current_user.storage_bytes_used,
            "storage_bytes_limit": current_user.storage_bytes_limit,
            "current_month": current_month,
            "monthly_minutes": total_minutes,
            "monthly_cost_usd": float(total_cost),
            "records": [
                {
                    "id": str(r.id),
                    "deployment_id": str(r.deployment_id) if r.deployment_id else None,
                    "provider": r.provider.value,
                    "machine_type": r.machine_type,
                    "started_at": r.started_at.isoformat(),
                    "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                    "minutes": r.minutes,
                    "cost_usd": float(r.cost_usd),
                }
                for r in records
            ]
        }

    @app.post("/api/user/usage/start")
    async def start_usage_tracking(
        deployment_id: str,
        machine_type: str = "default",
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Start tracking compute usage for a deployment"""
        record = UsageRecord(
            user_id=current_user.id,
            deployment_id=deployment_id if deployment_id != "none" else None,
            provider=ComputeProvider.VERDA,
            machine_type=machine_type,
            started_at=datetime.utcnow(),
            billing_month=datetime.now().strftime("%Y-%m"),
        )
        db.add(record)
        await db.commit()

        return {"success": True, "usage_record_id": str(record.id)}

    @app.post("/api/user/usage/stop/{record_id}")
    async def stop_usage_tracking(
        record_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Stop tracking compute usage and calculate cost"""
        from uuid import UUID as PyUUID

        try:
            rec_uuid = PyUUID(record_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid record ID")

        result = await db.execute(
            select(UsageRecord)
            .where(UsageRecord.id == rec_uuid)
            .where(UsageRecord.user_id == current_user.id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail="Usage record not found")

        if record.ended_at:
            raise HTTPException(status_code=400, detail="Usage already stopped")

        record.ended_at = datetime.utcnow()
        duration = (record.ended_at - record.started_at).total_seconds() / 60
        record.minutes = int(duration)

        # Calculate cost (simple rate: $0.10 per minute as placeholder)
        # In production, this would use actual provider rates
        rate_per_minute = Decimal("0.10")
        record.cost_usd = rate_per_minute * record.minutes

        # Update user's total compute minutes
        current_user.compute_minutes_used += record.minutes

        await db.commit()

        return {
            "success": True,
            "minutes": record.minutes,
            "cost_usd": float(record.cost_usd)
        }

    # ========================================================================
    # STORAGE ENDPOINTS
    # ========================================================================

    @app.get("/api/user/storage")
    async def get_user_storage(
        current_user: User = Depends(get_current_user)
    ):
        """Get storage usage and info for the current user"""
        if not storage_client or not storage_client.enabled:
            return {
                "enabled": False,
                "message": "Storage not configured",
                "size_bytes": 0,
                "limit_bytes": current_user.storage_bytes_limit
            }

        usage = await storage_client.get_storage_usage(current_user.id)

        return {
            "enabled": True,
            "size_bytes": usage.get("size_bytes", 0),
            "file_count": usage.get("file_count", 0),
            "limit_bytes": current_user.storage_bytes_limit,
            "bucket_name": usage.get("bucket_name"),
            "usage_percent": round(
                (usage.get("size_bytes", 0) / max(current_user.storage_bytes_limit, 1)) * 100, 2
            ) if current_user.storage_bytes_limit > 0 else 0
        }

    @app.get("/api/user/storage/files")
    async def list_user_files(
        template_id: Optional[str] = None,
        path: str = "",
        current_user: User = Depends(get_current_user)
    ):
        """List files in user's storage"""
        if not storage_client or not storage_client.enabled:
            return {"files": [], "error": "Storage not configured"}

        result = await storage_client.list_user_files(
            current_user.id,
            template_id=template_id,
            path=path
        )
        return result

    @app.get("/api/user/storage/download-url")
    async def get_download_url(
        file_path: str,
        current_user: User = Depends(get_current_user)
    ):
        """Get a presigned URL for downloading a file"""
        if not storage_client or not storage_client.enabled:
            raise HTTPException(status_code=503, detail="Storage not configured")

        url = await storage_client.get_download_url(current_user.id, file_path)
        if not url:
            raise HTTPException(status_code=404, detail="File not found")

        return {"url": url, "expires_in": 3600}

    @app.get("/api/user/storage/upload-url")
    async def get_upload_url(
        file_path: str,
        current_user: User = Depends(get_current_user)
    ):
        """Get a presigned URL for uploading a file"""
        if not storage_client or not storage_client.enabled:
            raise HTTPException(status_code=503, detail="Storage not configured")

        # Check storage limit
        if current_user.tier == UserTier.FREE:
            raise HTTPException(
                status_code=403,
                detail="Storage not available on free tier. Please upgrade."
            )

        url = await storage_client.get_upload_url(current_user.id, file_path)
        if not url:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

        return {"url": url, "expires_in": 3600}

    @app.post("/api/user/storage/sync/{deployment_id}")
    async def sync_deployment_storage(
        deployment_id: str,
        action: str = "backup",  # "backup" or "restore"
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """
        Sync storage for a deployment.
        - backup: Save deployment data to Storj
        - restore: Load data from Storj to deployment
        """
        if not storage_client or not storage_client.enabled:
            raise HTTPException(status_code=503, detail="Storage not configured")

        if current_user.tier == UserTier.FREE:
            raise HTTPException(
                status_code=403,
                detail="Storage sync not available on free tier"
            )

        from uuid import UUID as PyUUID
        try:
            dep_uuid = PyUUID(deployment_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deployment ID")

        result = await db.execute(
            select(Deployment)
            .where(Deployment.id == dep_uuid)
            .where(Deployment.user_id == current_user.id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Get storage path for template
        storage_path = get_template_storage_path(deployment.template_id)
        if not storage_path:
            raise HTTPException(
                status_code=400,
                detail=f"No storage configuration for template: {deployment.template_id}"
            )

        if action == "backup":
            sync_result = await storage_client.sync_to_storage(
                user_id=current_user.id,
                template_id=deployment.template_id,
                local_path=storage_path,
                host=deployment.host,
                ssh_user=TEMPLATE_SERVER_USER
            )
        elif action == "restore":
            sync_result = await storage_client.restore_from_storage(
                user_id=current_user.id,
                template_id=deployment.template_id,
                local_path=storage_path,
                host=deployment.host,
                ssh_user=TEMPLATE_SERVER_USER
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'backup' or 'restore'")

        return sync_result

    # ========================================================================
    # PREDICTIVE WARMING ENDPOINTS
    # ========================================================================

    @app.post("/api/user/warm/{template_id}")
    async def trigger_warming(
        template_id: str,
        signal: str = "click",
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """
        Trigger predictive warming for a template.
        Called when user shows intent to deploy (clicks app card, opens config, etc.)

        Args:
            template_id: Template to warm (e.g., "ollama", "jupyter")
            signal: What triggered the warming ("login", "click", "hover", "config")
        """
        if not warming_manager:
            return {"enabled": False, "message": "Warming not available"}

        if template_id not in TEMPLATE_REGISTRY:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

        result = await warming_manager.trigger_warming(
            user_id=current_user.id,
            template_id=template_id,
            db=db,
            signal=signal
        )

        return result

    @app.get("/api/user/warm")
    async def get_warm_slots(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Get all active warm slots for the current user"""
        if not warming_manager:
            return {"enabled": False, "slots": []}

        slots = await warming_manager.get_user_warm_slots(current_user.id, db)

        return {
            "enabled": True,
            "slots": slots,
            "max_slots": 2
        }

    @app.delete("/api/user/warm/{slot_id}")
    async def cancel_warm_slot(
        slot_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Cancel/expire a warm slot early"""
        from models import WarmSlot, WarmSlotStatus
        from uuid import UUID as PyUUID

        try:
            slot_uuid = PyUUID(slot_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid slot ID")

        result = await db.execute(
            select(WarmSlot)
            .where(WarmSlot.id == slot_uuid)
            .where(WarmSlot.user_id == current_user.id)
        )
        slot = result.scalar_one_or_none()

        if not slot:
            raise HTTPException(status_code=404, detail="Warm slot not found")

        if slot.status in [WarmSlotStatus.CLAIMED, WarmSlotStatus.EXPIRED]:
            return {"success": False, "message": "Slot already claimed or expired"}

        # Mark as expired (cleanup task will release resources)
        slot.status = WarmSlotStatus.EXPIRED
        await db.commit()

        return {"success": True, "message": "Warm slot cancelled"}

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "unavailable"
    if DB_AVAILABLE:
        try:
            from database import check_db_connection
            db_status = "connected" if await check_db_connection() else "disconnected"
        except Exception:
            db_status = "error"

    return {
        "status": "healthy",
        "service": "Polaris Computer",
        "version": "2.0.0",
        "demo_mode": DEMO_MODE,
        "database": db_status,
        "auth_enabled": DB_AVAILABLE
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("TTS_PORT", 8081))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║             💻  Computer - Cloud Console                     ║
║                                                              ║
║  Frontend:  http://localhost:{port}                            ║
║  API Docs:  http://localhost:{port}/docs                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
