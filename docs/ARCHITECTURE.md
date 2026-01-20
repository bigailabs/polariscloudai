# VoiceFlow Architecture Documentation

## Overview

VoiceFlow is a Voice AI platform consisting of three main systems:
1. **TTS API** - Text-to-speech generation service
2. **Console** - Management dashboard
3. **Voice Collection** - Contributor voice data platform

---

## System Architecture

```
                                   ┌─────────────────────┐
                                   │      Users          │
                                   │  Developers / Apps  │
                                   └──────────┬──────────┘
                                              │
                                              ▼
                               ┌──────────────────────────┐
                               │       API Gateway        │
                               │     (Rate Limiting)      │
                               └──────────────┬───────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
           ┌───────────────┐        ┌────────────────┐        ┌────────────────┐
           │   Console     │        │    TTS API     │        │ Voice Collect  │
           │   Backend     │        │    Workers     │        │    Backend     │
           │   (FastAPI)   │        │   (GPU Pods)   │        │   (FastAPI)    │
           └───────┬───────┘        └────────┬───────┘        └────────┬───────┘
                   │                         │                         │
                   └─────────────────────────┼─────────────────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │     Shared Services      │
                              │  ┌──────┐  ┌──────────┐  │
                              │  │Redis │  │PostgreSQL│  │
                              │  └──────┘  └──────────┘  │
                              │  ┌──────┐  ┌──────────┐  │
                              │  │ S3   │  │ Stripe   │  │
                              │  └──────┘  └──────────┘  │
                              └──────────────────────────┘
```

---

## Component Details

### 1. Console Backend (`app_server.py`)

**Purpose:** Management dashboard API for deployments, API keys, settings, and analytics.

**Technology:**
- FastAPI (Python 3.10+)
- Uvicorn ASGI server
- JSON file storage (to be migrated to PostgreSQL)

**Key Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/stats` | GET | Dashboard statistics |
| `/api/deployments` | GET/POST | Deployment management |
| `/api/gpus` | GET | Available GPU types |
| `/api/keys` | GET/POST/DELETE | API key management |
| `/api/usage` | GET | Usage analytics |
| `/api/settings` | GET/PUT | Account settings |
| `/api/webhooks` | GET/POST/DELETE | Webhook configuration |

**Data Flow:**
```
Browser → FastAPI → Verda API (GPU) → TTS Workers
                 ↘ JSON Files (local storage)
```

### 2. TTS API Workers

**Purpose:** GPU-accelerated text-to-speech generation.

**Technology:**
- PyTorch + CUDA
- Chatterbox TTS model
- FastAPI
- Docker with NVIDIA runtime

**Key Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/generate` | POST | Generate speech from text |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe |

**Deployment Options:**
1. **Serverless Containers** (Verda) - Auto-scaling, scale-to-zero
2. **Raw Compute** (Verda) - Dedicated GPU instances

**Docker Image:** `ghcr.io/wallscaler/chatterbox-tts:v1.1.0`

### 3. Verda Integration (`verda_deploy.py`)

**Purpose:** GPU infrastructure orchestration.

**Capabilities:**
- OAuth2 authentication
- Container deployment management
- Raw compute instance management
- GPU availability and pricing
- Health monitoring

**Key Classes:**
```python
class VerdaClient:
    def authenticate()
    def create_container_deployment()
    def create_instance()
    def get_available_gpus()
    def wait_for_healthy()
    def wait_for_application_ready()
```

---

## Data Storage

### Current (JSON Files)

| File | Purpose |
|------|---------|
| `api_keys.json` | API key storage |
| `settings.json` | User settings |
| `usage_stats.json` | Usage tracking |
| `deployment_metrics.json` | Metrics history |
| `usage_limits.json` | Rate limit config |
| `cost_tracking.json` | Cost data |

### Target (PostgreSQL)

See `docs/ISSUES.md` Issue #4 for migration plan.

---

## Authentication Flow

### Current: API Key Authentication

```
1. User generates API key in Console
2. Key stored in api_keys.json: {"id": "xxx", "key": "vf_live_xxx", ...}
3. Client sends request with X-API-Key header
4. Server validates key against stored keys
5. Request processed if valid
```

### Target: Multi-tier Authentication

```
1. User Auth (Console)
   - OAuth2 (Google, GitHub) via Auth0
   - JWT tokens for session management

2. API Auth (TTS API)
   - API keys for machine-to-machine
   - JWT tokens for user sessions
   - Webhook signature verification
```

---

## Request Flow: TTS Generation

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /generate
       │ X-API-Key: vf_live_xxx
       │ {text: "Hello"}
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        TTS Worker                                │
├─────────────────────────────────────────────────────────────────┤
│ 1. Validate API Key                                              │
│    ├── Check format (vf_live_* or vf_test_*)                    │
│    └── Validate against database                                 │
├─────────────────────────────────────────────────────────────────┤
│ 2. Preprocess Text                                               │
│    ├── Parse expression tags ([laugh], [sigh], etc.)            │
│    ├── Normalize text (numbers, abbreviations)                   │
│    └── Split into sentences if needed                            │
├─────────────────────────────────────────────────────────────────┤
│ 3. Generate Audio                                                │
│    ├── Load voice reference (if provided)                        │
│    ├── Run TTS model (Chatterbox)                               │
│    └── Post-process audio                                        │
├─────────────────────────────────────────────────────────────────┤
│ 4. Return Response                                               │
│    ├── Content-Type: audio/wav                                   │
│    └── 16-bit PCM, 24kHz, mono                                  │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Client    │
│ (WAV file)  │
└─────────────┘
```

---

## GPU Infrastructure

### Available GPUs (via Verda)

| GPU | Memory | Spot Price | Best For |
|-----|--------|------------|----------|
| Tesla V100 | 16GB | $0.076/hr | Development |
| RTX A6000 | 48GB | $0.125/hr | Production (budget) |
| A100 40GB | 40GB | $0.238/hr | Production (standard) |
| A100 80GB | 80GB | $0.425/hr | Heavy workloads |
| H100 | 80GB | $0.850/hr | Maximum performance |

### Scaling Configuration

**Serverless Containers:**
```yaml
scaling:
  min_replicas: 0        # Scale to zero
  max_replicas: 3        # Max concurrent
  scale_up_delay: 30s    # Wait before adding
  scale_down_delay: 15m  # Wait before removing
  concurrent_per_replica: 1  # One request at a time
```

---

## Monitoring & Observability

### Current

- Basic health endpoints (`/health`, `/ready`)
- Mock metrics in Console
- File-based logging

### Target

| Layer | Tool | Purpose |
|-------|------|---------|
| Metrics | Prometheus | Time-series metrics |
| Dashboards | Grafana | Visualization |
| Logging | Loki | Log aggregation |
| Tracing | Jaeger | Distributed tracing |
| Alerting | AlertManager | Incident response |

### Key Metrics to Track

**API Metrics:**
- `tts_requests_total` - Total requests by status
- `tts_request_duration_seconds` - Latency histogram
- `tts_audio_duration_seconds` - Generated audio length
- `tts_active_connections` - Current connections

**GPU Metrics:**
- `gpu_utilization_percent` - GPU usage
- `gpu_memory_used_bytes` - VRAM usage
- `gpu_temperature_celsius` - Temperature

**Business Metrics:**
- `deployments_active` - Running deployments
- `cost_per_hour_usd` - Current spend rate
- `api_keys_active` - Valid API keys

---

## Security Model

### API Security

```yaml
Authentication:
  - API keys (X-API-Key header)
  - JWT tokens (future)

Authorization:
  - Key validation
  - Rate limiting (per key)
  - Usage quotas

Encryption:
  - TLS 1.3 for all traffic
  - API keys hashed at rest (planned)

Input Validation:
  - Text length limits
  - File size limits
  - Content type validation
```

### Infrastructure Security

```yaml
Network:
  - Private VPC for workers
  - Load balancer with WAF
  - No direct GPU access

Secrets:
  - Environment variables for credentials
  - No secrets in code/logs

Access:
  - Principle of least privilege
  - Audit logging (planned)
```

---

## Development Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# Node.js 18+ (for frontend development)
node --version

# Docker (for running TTS workers locally)
docker --version
```

### Local Development

```bash
# Clone repository
git clone https://github.com/wallscaler/voiceflow.git
cd voiceflow

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Run Console server (demo mode)
python app_server.py

# Server runs at http://localhost:8080
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VERDA_CLIENT_ID` | No* | Verda API client ID |
| `VERDA_CLIENT_SECRET` | No* | Verda API secret |
| `HF_TOKEN` | No | Hugging Face token for models |
| `API_KEY` | No | Default API key for testing |

*Without Verda credentials, runs in demo mode.

---

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t voiceflow-console .

# Run container
docker run -p 8080:8080 \
  -e VERDA_CLIENT_ID=xxx \
  -e VERDA_CLIENT_SECRET=xxx \
  voiceflow-console
```

### Kubernetes (Future)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voiceflow-console
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: console
        image: ghcr.io/wallscaler/voiceflow-console:latest
        ports:
        - containerPort: 8080
        env:
        - name: VERDA_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: verda-credentials
              key: client_id
```

---

## Future Architecture

### Microservices Migration

```
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway (Kong/Envoy)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Auth      │     │   Console   │     │   Voice     │
│   Service   │     │   Service   │     │   Collect   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    Message Queue       │
              │    (Redis Streams)     │
              └────────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   TTS       │   │   Quality   │   │   Payment   │
│   Workers   │   │   Pipeline  │   │   Service   │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

*Architecture Version: 1.0*
*Last Updated: January 2026*
