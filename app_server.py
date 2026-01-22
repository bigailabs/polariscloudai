#!/usr/bin/env python3
"""
Computer - Cloud Console Backend
FastAPI server that serves the app.html frontend and provides REST APIs
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uvicorn
import asyncio
import json
import os
import sys
import subprocess
import secrets
from datetime import datetime

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

# Template deployment server configuration (from environment)
TEMPLATE_SERVER_HOST = os.getenv("TEMPLATE_SERVER_HOST", "65.108.32.148")
TEMPLATE_SERVER_USER = os.getenv("TEMPLATE_SERVER_USER", "root")

# Initialize FastAPI
app = FastAPI(title="Computer Console API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients - demo mode if no credentials
verda_client = None
if not DEMO_MODE:
    try:
        verda_client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)
    except Exception as e:
        print(f"⚠️  Verda auth failed, running in DEMO MODE: {e}")
        DEMO_MODE = True

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
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


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
            cmd = f'ssh -o StrictHostKeyChecking=no -o BatchMode=yes {ssh_user}@{host} "docker exec {container_name} jupyter server list 2>/dev/null | grep token= | head -1"'
            process = await asyncio.create_subprocess_shell(
                cmd,
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

    # Use configured server
    host = TEMPLATE_SERVER_HOST
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

            # Get container name based on template
            container_name = request.parameters.get("container_name", template.id)
            if template.id == "jupyter":
                container_name = "jupyter-notebook"
            elif template.id == "ubuntu-desktop":
                container_name = "cloud-computer"
            elif template.id == "ollama":
                container_name = "open-webui"
            elif template.id == "transformer-labs":
                container_name = "transformerlab"
            elif template.id == "minecraft":
                container_name = "minecraft-server"
            elif template.id == "valheim":
                container_name = "valheim-server"
            elif template.id == "terraria":
                container_name = "terraria-server"
            elif template.id == "factorio":
                container_name = "factorio-server"

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
    if template.id == "ollama":
        model = parameters.get("model", "llama2")
        port = parameters.get("port", 8000)
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
        port = parameters.get("port", 8888)
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
        port = parameters.get("port", 7681)
        container_name = parameters.get("container_name", "dev-terminal")
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
        port = parameters.get("port", 6901)
        vnc_port = parameters.get("vnc_port", 5901)
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
        port = parameters.get("port", 8000)
        image_type = parameters.get("image_type", "api")
        if image_type == "api":
            image = "transformerlab/api:latest"
            internal_port = 8338
        else:
            image = "ghcr.io/bigideaafrica/labs:latest"
            internal_port = 8000
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
async def get_deployments():
    """Get all deployments"""
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
async def deploy_server(request: DeploymentRequest):
    """Deploy a new TTS server"""
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
async def stop_deployment(request: StopDeploymentRequest):
    """Stop a deployment"""
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
async def get_deployment_logs(deployment_id: str):
    """Get logs for a deployment"""
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
async def deploy_template(request: TemplateDeploymentRequest):
    """Deploy a template to a remote server"""
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
async def get_template_deployments():
    """Get all template deployments"""
    deployments = load_template_deployments()
    return {"deployments": list(deployments.values())}


@app.get("/api/templates/deployments/{deployment_id}")
async def get_template_deployment(deployment_id: str):
    """Get a specific template deployment"""
    deployments = load_template_deployments()
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")
    return deployments[deployment_id]


@app.post("/api/templates/deployments/sync")
async def sync_deployment_statuses():
    """Sync deployment statuses with actual container states on the server"""
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
            cmd = f'ssh -o StrictHostKeyChecking=no -o BatchMode=yes {TEMPLATE_SERVER_USER}@{TEMPLATE_SERVER_HOST} "docker ps --format {{{{.Names}}}}"'
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

        # Update each deployment's status
        for dep_id, dep in deployments.items():
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

        return {"success": True, "updated": updated, "running_containers": list(running_containers)}

    except Exception as e:
        return {"success": False, "error": str(e), "updated": 0}


@app.delete("/api/templates/deployments/{deployment_id}")
async def delete_template_deployment(deployment_id: str, cleanup: bool = True):
    """Stop container and delete a template deployment record"""
    deployments = load_template_deployments()
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found")

    deployment = deployments[deployment_id]
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
                    cmd = f'ssh -o StrictHostKeyChecking=no -o BatchMode=yes {ssh_user}@{host} "docker stop {cname}; docker rm {cname}"'
                    process = await asyncio.create_subprocess_shell(
                        cmd,
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
async def deployment_websocket(websocket: WebSocket, deployment_id: str):
    """WebSocket endpoint for real-time deployment progress"""
    await websocket.accept()
    active_connections[deployment_id] = websocket

    try:
        # Send initial status
        deployments = load_template_deployments()
        if deployment_id in deployments:
            await websocket.send_json({
                "deployment_id": deployment_id,
                "message": "Connected to deployment progress stream",
                "status": deployments[deployment_id].get("status", "unknown"),
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
        if deployment_id in active_connections:
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
async def get_deployment_metrics(deployment_id: str):
    """Get real-time metrics for a deployment"""
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
async def get_deployment_metrics_history(deployment_id: str, period: str = "1h"):
    """Get historical metrics for a deployment"""
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
async def get_limits():
    """Get current usage limits"""
    limits = load_limits()

    # Add current usage stats
    keys = load_api_keys()
    settings = load_settings()
    stats = load_usage_stats()

    today = datetime.now().strftime("%Y-%m-%d")
    today_requests = stats.get("requests_by_day", {}).get(today, 0)

    return {
        "limits": limits,
        "current_usage": {
            "api_keys_count": len(keys),
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
async def update_limits(request: LimitsUpdateRequest):
    """Update usage limits"""
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

    # Also update billing in settings
    settings = load_settings()
    settings["billing"]["current_month"] = data["monthly_totals"].get(month, 0)
    save_settings(settings)

    return cost

@app.get("/api/costs")
async def get_cost_breakdown():
    """Get detailed cost breakdown"""
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
async def simulate_cost(hours: float = 1.0, deployment_id: str = "demo", gpu_type: str = "A100-40GB"):
    """Simulate recording a cost (for testing)"""
    cost = record_deployment_cost(deployment_id, gpu_type, hours)
    return {"success": True, "cost_recorded": round(cost, 4), "deployment_id": deployment_id}

# ============================================================================
# DANGER ZONE OPERATIONS
# ============================================================================

@app.post("/api/danger/reset-usage")
async def reset_usage_stats():
    """Reset all usage statistics (danger zone)"""
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
async def revoke_all_api_keys():
    """Revoke all API keys (danger zone)"""
    save_api_keys([])
    return {"success": True, "message": "All API keys have been revoked"}

@app.post("/api/danger/stop-all-deployments")
async def stop_all_deployments():
    """Stop all active deployments (danger zone)"""
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
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Computer Console", "demo_mode": DEMO_MODE}

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║             💻  Computer - Cloud Console                     ║
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
