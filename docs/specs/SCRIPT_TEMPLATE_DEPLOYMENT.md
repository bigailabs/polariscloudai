# Script Template Deployment - Technical Specification

> Enable VoiceFlow users to deploy pre-built script templates (Ollama, Jupyter, Desktop, LLMs) on GPU instances with a magical, multi-step UI experience.

---

## Executive Summary

This specification outlines how to extend VoiceFlow's existing TTS deployment capabilities to support **script-based template deployments** - deployable environments like Ollama (LLM inference), Jupyter notebooks, remote desktops, and custom AI tools. The goal is to provide a "magical" one-click deployment experience with intelligent configuration wizards.

### Key Insights from Polaris Templates Analysis

The Polaris templates (`~/Documents/PROJECTS/polaris/cloudai/polariscloudai/templates/`) reveal a mature pattern:

1. **Template Types**:
   - **Ollama LLM** - Deploy LLM models with OpenAI-compatible APIs
   - **Jupyter Notebook** - GPU-accelerated data science environment
   - **Remote Desktop** - Full Ubuntu XFCE desktop via VNC
   - **Custom Docker Images** - Any containerized application

2. **Deployment Pattern**:
   - SSH into raw GPU instance
   - Execute shell scripts that set up Docker containers
   - Configure networking, ports, and environment
   - Return access credentials (URLs, tokens, passwords)

3. **Multi-Level UI Needs**:
   - Template selection (card gallery)
   - Model/variant selection (for LLMs)
   - Configuration wizard (ports, passwords, resources)
   - Real-time deployment progress
   - Post-deploy access panel (connection details)

---

## 1. Template Registry Architecture

### 1.1 Template Definition Schema

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class TemplateCategory(str, Enum):
    LLM = "llm"
    NOTEBOOK = "notebook"
    DESKTOP = "desktop"
    DEVELOPMENT = "development"
    TTS = "tts"
    MINING = "mining"
    CUSTOM = "custom"

class TemplatePort(BaseModel):
    name: str                    # "web", "ssh", "vnc", "api"
    internal: int                # Port inside container
    external: int | None = None  # Suggested external port (user can customize)
    protocol: str = "tcp"        # "tcp", "udp"
    description: str             # "Web interface", "SSH access"

class TemplateEnvVar(BaseModel):
    name: str
    description: str
    default: str | None = None
    required: bool = True
    secret: bool = False         # If true, mask in UI
    options: List[str] | None = None  # If provided, show dropdown

class TemplateConfig(BaseModel):
    # Identity
    id: str                      # "ollama-llm", "jupyter-gpu", "ubuntu-desktop"
    name: str                    # "Ollama LLM Server"
    version: str                 # "1.0.0"
    description: str
    category: TemplateCategory
    icon: str                    # URL or emoji

    # Deployment
    image: str | None = None     # Docker image (if container-based)
    script_url: str | None = None  # URL to deployment script
    script_content: str | None = None  # Inline script (for simple templates)

    # Requirements
    gpu_required: bool = False
    min_gpu_vram_gb: int = 0
    min_ram_gb: int = 8
    min_storage_gb: int = 20

    # Networking
    ports: List[TemplatePort] = []

    # Configuration
    env_vars: List[TemplateEnvVar] = []

    # UI Customization
    has_model_selector: bool = False  # For LLMs - show model picker
    model_options: List[Dict[str, Any]] = []  # Available models

    # Access
    access_type: str = "web"     # "web", "ssh", "vnc", "api"
    access_instructions: str = ""

    # Status
    is_active: bool = True
    is_premium: bool = False
    coming_soon: bool = False

    # Tags for filtering
    tags: List[str] = []


# Example: Ollama Template
OLLAMA_TEMPLATE = TemplateConfig(
    id="ollama-llm",
    name="Ollama LLM Server",
    version="1.0.0",
    description="Deploy any LLM with OpenAI-compatible API. Supports Llama, Qwen, DeepSeek, Mistral, and 300+ models.",
    category=TemplateCategory.LLM,
    icon="🦙",

    script_url="https://raw.githubusercontent.com/PolarisCloudAI/polaris_templates/main/ollama/deploy.sh",

    gpu_required=True,
    min_gpu_vram_gb=8,
    min_ram_gb=16,
    min_storage_gb=50,

    ports=[
        TemplatePort(name="api", internal=11434, external=11434, description="Ollama API"),
        TemplatePort(name="web", internal=8000, external=8000, description="Web Chat Interface"),
    ],

    env_vars=[
        TemplateEnvVar(name="MODEL_NAME", description="Model to deploy", default="llama3.2:3b", required=True),
        TemplateEnvVar(name="OLLAMA_KEEP_ALIVE", description="Model keep-alive time", default="30m"),
    ],

    has_model_selector=True,
    model_options=[
        {"id": "llama3.2:3b", "name": "Llama 3.2 3B", "vram": 4, "size": "2GB"},
        {"id": "llama3.2:8b", "name": "Llama 3.2 8B", "vram": 8, "size": "4.7GB"},
        {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "vram": 8, "size": "4.4GB"},
        {"id": "deepseek-r1:7b", "name": "DeepSeek R1 7B", "vram": 8, "size": "4.7GB"},
        {"id": "mistral:7b", "name": "Mistral 7B", "vram": 8, "size": "4.1GB"},
        {"id": "codellama:7b", "name": "Code Llama 7B", "vram": 8, "size": "3.8GB"},
    ],

    access_type="api",
    access_instructions="API available at http://{ip}:11434. Web chat at http://{ip}:8000",

    tags=["llm", "inference", "openai-compatible", "ollama"]
)


# Example: Jupyter Notebook Template
JUPYTER_TEMPLATE = TemplateConfig(
    id="jupyter-gpu",
    name="Jupyter Notebook (GPU)",
    version="1.0.0",
    description="GPU-accelerated Jupyter Lab with PyTorch, TensorFlow, and essential data science libraries pre-installed.",
    category=TemplateCategory.NOTEBOOK,
    icon="📓",

    image="tensorflow/tensorflow:latest-gpu-jupyter",

    gpu_required=True,
    min_gpu_vram_gb=4,
    min_ram_gb=8,
    min_storage_gb=20,

    ports=[
        TemplatePort(name="jupyter", internal=8888, external=8888, description="Jupyter Lab"),
    ],

    env_vars=[
        TemplateEnvVar(name="JUPYTER_PASSWORD", description="Notebook password", default="jupyter123", secret=True),
        TemplateEnvVar(name="JUPYTER_ENABLE_LAB", description="Enable JupyterLab", default="yes"),
    ],

    access_type="web",
    access_instructions="Open http://{ip}:8888 in your browser. Token: {token}",

    tags=["jupyter", "notebook", "tensorflow", "pytorch", "data-science"]
)


# Example: Ubuntu Desktop Template
DESKTOP_TEMPLATE = TemplateConfig(
    id="ubuntu-desktop",
    name="Ubuntu Desktop (VNC)",
    version="1.0.0",
    description="Full Ubuntu XFCE desktop accessible via browser. Includes Firefox, file manager, and terminal.",
    category=TemplateCategory.DESKTOP,
    icon="🖥️",

    image="consol/ubuntu-xfce-vnc",

    gpu_required=False,
    min_ram_gb=4,
    min_storage_gb=10,

    ports=[
        TemplatePort(name="vnc-web", internal=6901, external=6901, description="Web VNC (noVNC)"),
        TemplatePort(name="vnc", internal=5901, external=5901, description="VNC Client"),
    ],

    env_vars=[
        TemplateEnvVar(name="VNC_PASSWORD", description="VNC password", default="ubuntu123", secret=True),
        TemplateEnvVar(name="VNC_RESOLUTION", description="Screen resolution", default="1920x1080",
                       options=["1920x1080", "1280x720", "2560x1440"]),
    ],

    access_type="vnc",
    access_instructions="Open http://{ip}:6901/vnc.html?autoconnect=true. Password: {vnc_password}",

    tags=["desktop", "ubuntu", "vnc", "gui"]
)
```

### 1.2 Database Schema

```sql
-- Templates table
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,  -- "ollama-llm"
    name VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    icon VARCHAR(100),

    -- Deployment config (JSON)
    config JSONB NOT NULL,

    -- Requirements
    gpu_required BOOLEAN DEFAULT FALSE,
    min_gpu_vram_gb INTEGER DEFAULT 0,
    min_ram_gb INTEGER DEFAULT 8,
    min_storage_gb INTEGER DEFAULT 20,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_premium BOOLEAN DEFAULT FALSE,
    coming_soon BOOLEAN DEFAULT FALSE,

    -- Metrics
    deploy_count INTEGER DEFAULT 0,
    avg_deploy_time_seconds INTEGER,
    success_rate DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Template deployments
CREATE TABLE template_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    template_id UUID REFERENCES templates(id),

    -- Instance info
    instance_id VARCHAR(255),  -- Verda instance ID
    instance_ip VARCHAR(45),
    instance_hostname VARCHAR(255),

    -- Configuration used
    config_snapshot JSONB,  -- Captured at deploy time
    env_vars JSONB,  -- User-provided values (secrets encrypted)
    ports_mapping JSONB,

    -- Access credentials
    access_url TEXT,
    access_token TEXT,  -- Encrypted
    ssh_command TEXT,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, deploying, running, failed, stopped
    deploy_started_at TIMESTAMP,
    deploy_completed_at TIMESTAMP,
    last_health_check TIMESTAMP,
    health_status VARCHAR(50),

    -- Logs
    deploy_logs TEXT,
    error_message TEXT,

    -- Cost tracking
    hourly_rate DECIMAL(10,4),
    total_cost DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployments_user ON template_deployments(user_id);
CREATE INDEX idx_deployments_status ON template_deployments(status);
```

---

## 2. Multi-Step Deployment UI

### 2.1 Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Template Deployment Wizard                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Step 1: Template Selection                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ 🦙 Ollama   │ │ 📓 Jupyter │ │ 🖥️ Desktop │ │ 🎙️ TTS     │   │
│  │    LLM     │ │  Notebook  │ │   Ubuntu   │ │  Server    │   │
│  │  ★★★★★     │ │   ★★★★☆    │ │   ★★★★☆    │ │   ★★★★★     │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  Step 2: Model/Variant Selection (if applicable)                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Select Model                                          [▼]   │   │
│  │ ┌───────────────────────────────────────────────────────┐   │   │
│  │ │ ⭐ Llama 3.2 8B          8GB VRAM • 4.7GB download   │   │   │
│  │ │    Qwen 2.5 7B          8GB VRAM • 4.4GB download   │   │   │
│  │ │    DeepSeek R1 7B       8GB VRAM • 4.7GB download   │   │   │
│  │ │    Mistral 7B           8GB VRAM • 4.1GB download   │   │   │
│  │ │    Code Llama 7B        8GB VRAM • 3.8GB download   │   │   │
│  │ └───────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  Step 3: GPU Selection                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ GPU Type                                                     │   │
│  │ ○ Tesla V100 16GB    $0.08/hr  ⚠️ Low VRAM for this model   │   │
│  │ ● RTX A6000 48GB     $0.16/hr  ✓ Recommended                │   │
│  │ ○ A100 SXM4 40GB     $0.24/hr  ✓ Fast inference             │   │
│  │ ○ H100 SXM5 80GB     $1.10/hr  ✓ Maximum performance        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  Step 4: Configuration                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Deployment Name      [my-llama-server________________]      │   │
│  │ API Port             [11434_________________________]      │   │
│  │ Web UI Port          [8000__________________________]      │   │
│  │                                                              │   │
│  │ ☐ Use spot instances (cheaper, may be interrupted)         │   │
│  │ ☐ Enable auto-scaling                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│                       [Cancel]  [← Back]  [Deploy →]                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment Progress

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Deploying Ollama LLM Server                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │  ✓ Creating GPU instance...                    2s            │   │
│  │  ✓ Instance ready: 192.168.1.100              15s            │   │
│  │  ✓ Installing Docker and dependencies...      45s            │   │
│  │  ● Pulling Ollama container...                 ████████░░    │   │
│  │  ○ Downloading model: llama3.2:8b                            │   │
│  │  ○ Starting FastAPI wrapper...                               │   │
│  │  ○ Running health checks...                                  │   │
│  │                                                               │   │
│  │                                                               │   │
│  │  Elapsed: 1m 42s • Estimated remaining: 3m 15s               │   │
│  │                                                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Live Logs                                         [Expand]  │   │
│  │  ───────────────────────────────────────────────────────────  │   │
│  │  [REMOTE] Starting deployment...                             │   │
│  │  [REMOTE] NVIDIA GPU detected: RTX A6000 48GB               │   │
│  │  [REMOTE] Pulling ollama/ollama:latest...                    │   │
│  │  [REMOTE] latest: Pulling from ollama/ollama                 │   │
│  │  [REMOTE] ████████████████████ 100% 2.1GB/2.1GB             │   │
│  │  ▌                                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│                              [Cancel Deployment]                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Post-Deployment Access Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│  ✓ Deployment Successful!                             [Minimize]    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  🦙 Ollama LLM Server                                               │
│  Model: llama3.2:8b • GPU: RTX A6000 48GB • $0.16/hr               │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  Quick Access                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🌐 Web Chat    http://192.168.1.100:8000       [Open →]     │   │
│  │ 🔌 API Base    http://192.168.1.100:11434      [Copy]       │   │
│  │ 📄 API Docs    http://192.168.1.100:8000/docs  [Open →]     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  API Usage                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ curl http://192.168.1.100:11434/api/chat \                  │   │
│  │   -d '{"model": "llama3.2:8b",                              │   │
│  │        "messages": [{"role": "user",                         │   │
│  │                      "content": "Hello!"}]}'                 │   │
│  │                                                     [Copy]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  OpenAI-Compatible Endpoint                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ from openai import OpenAI                                    │   │
│  │                                                               │   │
│  │ client = OpenAI(                                             │   │
│  │     base_url="http://192.168.1.100:8000/v1",                │   │
│  │     api_key="not-needed"                                     │   │
│  │ )                                                             │   │
│  │                                                               │   │
│  │ response = client.chat.completions.create(                   │   │
│  │     model="llama3.2:8b",                                     │   │
│  │     messages=[{"role": "user", "content": "Hi!"}]           │   │
│  │ )                                                  [Copy]    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                       │
│  Status: Running • Uptime: 5m 23s • Requests: 0                     │
│                                                                       │
│  [View Logs]  [Metrics]  [Settings]              [Stop Deployment]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Backend Implementation

### 3.1 API Endpoints

```yaml
# Template Management
GET    /api/templates                    # List all templates
GET    /api/templates/{slug}             # Get template details
GET    /api/templates/categories         # List categories

# Template Deployment
POST   /api/templates/{slug}/deploy      # Start deployment
GET    /api/templates/deployments        # List user's deployments
GET    /api/templates/deployments/{id}   # Get deployment details
GET    /api/templates/deployments/{id}/logs    # Stream deployment logs
GET    /api/templates/deployments/{id}/status  # Health check
DELETE /api/templates/deployments/{id}   # Stop and delete deployment

# Model Selection (for LLM templates)
GET    /api/templates/ollama-llm/models  # List available Ollama models
```

### 3.2 Deployment Service

```python
import asyncio
import asyncssh
from typing import AsyncGenerator

class TemplateDeploymentService:
    """Handles script-based template deployments to GPU instances."""

    def __init__(self, verda_client: VerdaClient):
        self.verda = verda_client

    async def deploy(
        self,
        template: TemplateConfig,
        gpu_type: str,
        env_vars: Dict[str, str],
        user_id: str,
    ) -> AsyncGenerator[DeploymentEvent, None]:
        """
        Deploy a template to a new GPU instance.
        Yields progress events for real-time UI updates.
        """
        deployment_id = str(uuid.uuid4())

        # Step 1: Create instance
        yield DeploymentEvent(
            step="creating_instance",
            status="in_progress",
            message=f"Creating {gpu_type} instance..."
        )

        instance = await self.verda.create_instance(
            name=f"template-{template.id}-{deployment_id[:8]}",
            gpu_name=gpu_type,
            use_spot=env_vars.get("use_spot", False)
        )

        if not instance:
            yield DeploymentEvent(
                step="creating_instance",
                status="failed",
                message="Failed to create GPU instance"
            )
            return

        yield DeploymentEvent(
            step="creating_instance",
            status="completed",
            message=f"Instance created: {instance['ip']}"
        )

        # Step 2: Wait for SSH access
        yield DeploymentEvent(
            step="waiting_for_ssh",
            status="in_progress",
            message="Waiting for SSH access..."
        )

        ssh_ready = await self._wait_for_ssh(instance["ip"], timeout=120)
        if not ssh_ready:
            yield DeploymentEvent(
                step="waiting_for_ssh",
                status="failed",
                message="SSH not available after 2 minutes"
            )
            return

        yield DeploymentEvent(
            step="waiting_for_ssh",
            status="completed",
            message="SSH connection established"
        )

        # Step 3: Execute deployment script
        yield DeploymentEvent(
            step="running_script",
            status="in_progress",
            message="Running deployment script..."
        )

        async for log_line in self._run_deployment_script(
            instance["ip"],
            template,
            env_vars
        ):
            yield DeploymentEvent(
                step="running_script",
                status="in_progress",
                message=log_line,
                is_log=True
            )

        yield DeploymentEvent(
            step="running_script",
            status="completed",
            message="Deployment script completed"
        )

        # Step 4: Health check
        yield DeploymentEvent(
            step="health_check",
            status="in_progress",
            message="Running health checks..."
        )

        health_ok = await self._health_check(
            instance["ip"],
            template.ports[0].external
        )

        if health_ok:
            yield DeploymentEvent(
                step="health_check",
                status="completed",
                message="Service is healthy!"
            )

            # Final success
            yield DeploymentEvent(
                step="complete",
                status="completed",
                message="Deployment successful!",
                result={
                    "deployment_id": deployment_id,
                    "instance_ip": instance["ip"],
                    "access_url": f"http://{instance['ip']}:{template.ports[0].external}",
                    "ports": {p.name: p.external for p in template.ports}
                }
            )
        else:
            yield DeploymentEvent(
                step="health_check",
                status="warning",
                message="Service may still be starting. Check logs for details."
            )

    async def _run_deployment_script(
        self,
        ip: str,
        template: TemplateConfig,
        env_vars: Dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """Execute deployment script over SSH, streaming output."""

        # Build environment string
        env_export = "\n".join([
            f"export {k}={shlex.quote(v)}"
            for k, v in env_vars.items()
        ])

        # Get script content
        if template.script_url:
            script = f"curl -fsSL {template.script_url} | bash"
        elif template.script_content:
            script = template.script_content
        elif template.image:
            # Generate Docker run command for simple container deployments
            ports = " ".join([f"-p {p.external}:{p.internal}" for p in template.ports])
            envs = " ".join([f"-e {k}={shlex.quote(v)}" for k, v in env_vars.items()])
            gpu = "--gpus all" if template.gpu_required else ""

            script = f"""
docker pull {template.image}
docker run -d --name {template.id} {gpu} {ports} {envs} --restart unless-stopped {template.image}
"""

        full_script = f"""
#!/bin/bash
set -e
{env_export}

{script}
"""

        # Execute via SSH and stream output
        async with asyncssh.connect(ip, username="root", known_hosts=None) as conn:
            async with conn.create_process(full_script) as process:
                async for line in process.stdout:
                    yield line.strip()
                async for line in process.stderr:
                    yield f"[stderr] {line.strip()}"

    async def _wait_for_ssh(self, ip: str, timeout: int = 120) -> bool:
        """Wait for SSH to become available."""
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                async with asyncssh.connect(
                    ip,
                    username="root",
                    known_hosts=None,
                    connect_timeout=5
                ) as conn:
                    result = await conn.run("echo ok", check=True)
                    return True
            except:
                await asyncio.sleep(5)

        return False

    async def _health_check(self, ip: str, port: int, timeout: int = 60) -> bool:
        """Check if service is responding."""
        import httpx

        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://{ip}:{port}/health",
                        timeout=5
                    )
                    if response.status_code == 200:
                        return True
            except:
                pass

            await asyncio.sleep(5)

        return False
```

### 3.3 WebSocket for Real-Time Updates

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/deployments/{deployment_id}")
async def deployment_websocket(websocket: WebSocket, deployment_id: str):
    """Stream deployment progress to frontend."""
    await websocket.accept()

    try:
        # Subscribe to deployment events
        async for event in deployment_service.subscribe(deployment_id):
            await websocket.send_json(event.dict())

            if event.status in ["completed", "failed"]:
                break

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
```

---

## 4. Frontend Components

### 4.1 Template Gallery Component

```tsx
interface TemplateCardProps {
  template: Template;
  onSelect: (template: Template) => void;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ template, onSelect }) => {
  const canDeploy = !template.coming_soon && template.is_active;

  return (
    <div
      className={`template-card ${canDeploy ? 'cursor-pointer hover:border-green-500' : 'opacity-60'}`}
      onClick={() => canDeploy && onSelect(template)}
    >
      <div className="template-icon text-4xl mb-2">{template.icon}</div>
      <h3 className="font-semibold">{template.name}</h3>
      <p className="text-sm text-gray-500">{template.description}</p>

      <div className="template-badges mt-3">
        {template.gpu_required && (
          <span className="badge badge-gpu">GPU Required</span>
        )}
        {template.coming_soon && (
          <span className="badge badge-coming-soon">Coming Soon</span>
        )}
        {template.is_premium && (
          <span className="badge badge-premium">Premium</span>
        )}
      </div>

      <div className="template-requirements mt-2 text-xs text-gray-400">
        {template.min_gpu_vram_gb > 0 && (
          <span>{template.min_gpu_vram_gb}GB+ VRAM</span>
        )}
        <span>{template.min_ram_gb}GB RAM</span>
      </div>
    </div>
  );
};
```

### 4.2 Deployment Wizard Component

```tsx
interface DeploymentWizardProps {
  template: Template;
  onDeploy: (config: DeploymentConfig) => void;
  onCancel: () => void;
}

const DeploymentWizard: React.FC<DeploymentWizardProps> = ({ template, onDeploy, onCancel }) => {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<Partial<DeploymentConfig>>({});

  const steps = [
    { id: 1, name: 'Template', component: TemplateInfo },
    template.has_model_selector && { id: 2, name: 'Model', component: ModelSelector },
    { id: 3, name: 'GPU', component: GPUSelector },
    { id: 4, name: 'Configure', component: ConfigurationForm },
  ].filter(Boolean);

  const currentStep = steps.find(s => s.id === step);

  return (
    <div className="deployment-wizard">
      {/* Step indicator */}
      <div className="wizard-steps">
        {steps.map((s, i) => (
          <div key={s.id} className={`step ${step >= s.id ? 'active' : ''}`}>
            <div className="step-number">{i + 1}</div>
            <div className="step-name">{s.name}</div>
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="wizard-content">
        <currentStep.component
          template={template}
          config={config}
          onChange={setConfig}
        />
      </div>

      {/* Navigation */}
      <div className="wizard-actions">
        <button onClick={onCancel}>Cancel</button>
        {step > 1 && (
          <button onClick={() => setStep(step - 1)}>← Back</button>
        )}
        {step < steps.length ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!isStepValid(step, config)}
          >
            Next →
          </button>
        ) : (
          <button
            onClick={() => onDeploy(config as DeploymentConfig)}
            className="btn-primary"
          >
            Deploy 🚀
          </button>
        )}
      </div>
    </div>
  );
};
```

### 4.3 Deployment Progress Component

```tsx
interface DeploymentProgressProps {
  deploymentId: string;
  onComplete: (result: DeploymentResult) => void;
  onCancel: () => void;
}

const DeploymentProgress: React.FC<DeploymentProgressProps> = ({
  deploymentId,
  onComplete,
  onCancel
}) => {
  const [events, setEvents] = useState<DeploymentEvent[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`/ws/deployments/${deploymentId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.is_log) {
        setLogs(prev => [...prev, data.message]);
      } else {
        setEvents(prev => [...prev, data]);

        if (data.status === 'completed' && data.result) {
          onComplete(data.result);
        }
      }
    };

    return () => ws.close();
  }, [deploymentId]);

  const currentStep = events[events.length - 1];

  return (
    <div className="deployment-progress">
      <div className="progress-header">
        <h3>Deploying...</h3>
        <span className="elapsed-time">{formatDuration(elapsed)}</span>
      </div>

      <div className="progress-steps">
        {DEPLOYMENT_STEPS.map(step => {
          const event = events.find(e => e.step === step.id);
          const status = event?.status || 'pending';

          return (
            <div key={step.id} className={`progress-step status-${status}`}>
              <div className="step-icon">
                {status === 'completed' && '✓'}
                {status === 'in_progress' && <Spinner />}
                {status === 'pending' && '○'}
                {status === 'failed' && '✗'}
              </div>
              <div className="step-label">{step.label}</div>
              {event?.message && (
                <div className="step-message">{event.message}</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Collapsible logs */}
      <div className="logs-section">
        <button onClick={() => setShowLogs(!showLogs)}>
          {showLogs ? 'Hide' : 'Show'} Logs
        </button>
        {showLogs && (
          <pre className="logs-output">
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </pre>
        )}
      </div>

      <button onClick={onCancel} className="btn-danger">
        Cancel Deployment
      </button>
    </div>
  );
};
```

---

## 5. Template Library

### 5.1 Initial Templates

| Template | Category | GPU Required | Description |
|----------|----------|--------------|-------------|
| Ollama LLM | LLM | Yes (8GB+) | Deploy 300+ LLMs with OpenAI-compatible API |
| Jupyter GPU | Notebook | Yes (4GB+) | GPU-accelerated data science environment |
| Ubuntu Desktop | Desktop | No | Full XFCE desktop via browser VNC |
| VS Code Server | Development | No | Browser-based VS Code |
| Chatterbox TTS | TTS | Yes (16GB+) | Voice synthesis and cloning (current VoiceFlow) |
| ComfyUI | Image | Yes (8GB+) | Stable Diffusion workflow editor |
| Automatic1111 | Image | Yes (8GB+) | Stable Diffusion WebUI |

### 5.2 Model Library (for Ollama)

```typescript
const OLLAMA_MODELS = [
  // Chat/Instruction Models
  { id: "llama3.2:3b", name: "Llama 3.2 3B", vram: 4, size: "2GB", category: "chat" },
  { id: "llama3.2:8b", name: "Llama 3.2 8B", vram: 8, size: "4.7GB", category: "chat" },
  { id: "llama3.3:70b", name: "Llama 3.3 70B", vram: 48, size: "43GB", category: "chat" },
  { id: "qwen2.5:7b", name: "Qwen 2.5 7B", vram: 8, size: "4.4GB", category: "chat" },
  { id: "qwen2.5:72b", name: "Qwen 2.5 72B", vram: 48, size: "47GB", category: "chat" },
  { id: "deepseek-r1:7b", name: "DeepSeek R1 7B", vram: 8, size: "4.7GB", category: "reasoning" },
  { id: "deepseek-r1:70b", name: "DeepSeek R1 70B", vram: 48, size: "43GB", category: "reasoning" },
  { id: "mistral:7b", name: "Mistral 7B", vram: 8, size: "4.1GB", category: "chat" },
  { id: "mixtral:8x7b", name: "Mixtral 8x7B", vram: 32, size: "26GB", category: "chat" },

  // Code Models
  { id: "codellama:7b", name: "Code Llama 7B", vram: 8, size: "3.8GB", category: "code" },
  { id: "codellama:34b", name: "Code Llama 34B", vram: 24, size: "19GB", category: "code" },
  { id: "deepseek-coder:6.7b", name: "DeepSeek Coder 6.7B", vram: 8, size: "3.8GB", category: "code" },
  { id: "starcoder2:7b", name: "StarCoder2 7B", vram: 8, size: "4GB", category: "code" },

  // Vision Models
  { id: "llava:7b", name: "LLaVA 7B", vram: 8, size: "4.5GB", category: "vision" },
  { id: "llava:13b", name: "LLaVA 13B", vram: 16, size: "8GB", category: "vision" },
];
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Template registry data model
- [ ] Database schema for templates and deployments
- [ ] API endpoints for template listing
- [ ] Basic template gallery UI
- [ ] Integration with existing Verda deployment

### Phase 2: Deployment Engine (Week 2-3)
- [ ] SSH-based script execution
- [ ] WebSocket for real-time progress
- [ ] Docker container deployment via scripts
- [ ] Health checking system
- [ ] Deployment logs storage

### Phase 3: Multi-Step Wizard UI (Week 3-4)
- [ ] Step-by-step wizard component
- [ ] Model selector for LLM templates
- [ ] GPU recommendation engine
- [ ] Configuration form builder
- [ ] Deployment progress visualization

### Phase 4: Post-Deploy Experience (Week 4-5)
- [ ] Access panel with connection details
- [ ] Code snippets for API usage
- [ ] Deployment metrics and monitoring
- [ ] Start/stop/restart controls
- [ ] Cost tracking

### Phase 5: Template Expansion (Week 5-6)
- [ ] Ollama LLM template
- [ ] Jupyter notebook template
- [ ] Ubuntu desktop template
- [ ] VS Code server template
- [ ] Custom template upload (admin)

---

## 7. Success Metrics

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Template deployments | 100 | 1,000 |
| Deployment success rate | 90% | 95% |
| Average deploy time | < 5 min | < 3 min |
| Active templates | 5 | 15 |
| User satisfaction (NPS) | 40 | 60 |

---

## 8. Recommendations

### 8.1 Prioritized Implementation Order

1. **Start with Ollama** - Highest value, clear use case, proven scripts
2. **Add Jupyter** - Popular with data scientists, straightforward deployment
3. **Enable Desktop** - Useful for GUI-based workflows
4. **Integrate ComfyUI/A1111** - Strong demand for image generation

### 8.2 UX Principles for "Magic" Feel

1. **Smart Defaults** - Pre-select best options based on template requirements
2. **GPU Recommendations** - Highlight which GPUs work best for each model
3. **One-Click Deploy** - Allow skipping wizard for simple templates
4. **Copy-Paste Snippets** - Ready-to-use code for every deployment
5. **Instant Access Links** - Open in new tab with one click
6. **Real-Time Feedback** - Show every step of deployment with logs

### 8.3 Technical Considerations

1. **Script Security** - Validate and sandbox deployment scripts
2. **Error Recovery** - Automatic rollback on deployment failure
3. **Cost Visibility** - Show estimated costs before deployment
4. **Resource Cleanup** - Auto-terminate orphaned deployments
5. **SSH Key Management** - Secure storage and rotation

---

*Specification Version: 1.0*
*Last Updated: January 2026*
