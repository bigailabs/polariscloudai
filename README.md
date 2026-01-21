# VoiceFlow

**Voice AI Console for Deploying TTS Services**

VoiceFlow is a management platform for deploying and operating text-to-speech services with voice cloning capabilities. Deploy GPU-powered TTS endpoints, manage API keys, monitor usage, and (coming soon) crowdsource voice data through our ethical voice collection marketplace.

---

## Features

### Current (MVP)

- **GPU Deployments** - Deploy TTS services on A100, H100, or L40S GPUs via Verda
- **Voice Cloning** - Create custom voices from audio samples
- **API Key Management** - Generate, rotate, and monitor API keys with usage tracking
- **Analytics Dashboard** - Real-time insights into API usage, latency, and costs
- **Usage Limits** - Set request limits and rate limiting per API key
- **Webhook Integrations** - Get notified on deployment events
- **Settings Management** - Configure billing alerts, security options, and notification preferences
- **Demo Mode** - Try everything without GPU credentials

### Coming Soon

- **Voice Collection Module** - Pay contributors for voice recordings
- **Voice Marketplace** - License voices from our diverse contributor pool
- **Billing Integration** - Usage-based billing with Stripe
- **Multi-region Deployments** - Deploy closer to your users
- **Official SDKs** - Python, Node.js, and Go clients

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (optional, for TTS workers)

### Installation

```bash
# Clone the repository
git clone https://github.com/wallscaler/voiceflow.git
cd voiceflow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the server (demo mode by default)
python app_server.py
```

Open `http://localhost:8080` in your browser.

### Demo Mode

By default, VoiceFlow runs in demo mode with simulated GPU deployments and mock data. This lets you explore all features without Verda credentials.

To use real GPU deployments:

1. Get credentials from [Verda](https://verda.io)
2. Update `.env` with your credentials:
   ```env
   VERDA_API_KEY=your_api_key
   VERDA_WORKSPACE_ID=your_workspace_id
   DEMO_MODE=false
   ```
3. Restart the server

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VoiceFlow Platform                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Web Console   │    │    REST API     │    │   TTS Workers   │  │
│  │   (app.html)    │───▶│  (app_server)   │───▶│   (Verda GPU)   │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                │                                      │
│                                ▼                                      │
│                         ┌─────────────────┐                          │
│                         │   Data Store    │                          │
│                         │   (JSON/DB)     │                          │
│                         └─────────────────┘                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | Description |
|-----------|------------|-------------|
| Web Console | HTML + Tailwind + Vanilla JS | Single-page management dashboard |
| REST API | FastAPI + Python | Backend API for all operations |
| TTS Workers | Docker + GPU | Voice synthesis and cloning |
| Data Store | JSON (MVP) / PostgreSQL (prod) | Persistent storage |

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/deployments` | GET/POST | List/create deployments |
| `/api/deployments/{id}` | GET/DELETE | Get/delete deployment |
| `/api/deployments/{id}/metrics` | GET | Real-time metrics |
| `/api/keys` | GET | List API keys |
| `/api/keys/generate` | POST | Generate new key |
| `/api/keys/{id}/rotate` | POST | Rotate key |
| `/api/analytics/overview` | GET | Usage analytics |
| `/api/limits` | GET/PUT | Usage limits |
| `/api/costs` | GET | Cost breakdown |
| `/health` | GET | Health check |

### TTS API (on deployed workers)

```bash
# Text to speech
curl -X POST https://your-deployment.voiceflow.app/tts \
  -H "Authorization: Bearer vf_live_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice_id": "default"}'

# Voice cloning
curl -X POST https://your-deployment.voiceflow.app/clone \
  -H "Authorization: Bearer vf_live_xxxxx" \
  -F "audio=@sample.wav" \
  -F "name=my-custom-voice"
```

See [docs/api_reference.md](docs/api_reference.md) for complete API documentation.

---

## Development

### Project Structure

```
voiceflow/
├── app_server.py       # FastAPI backend
├── app.html            # Single-file frontend (HTML + JS + CSS)
├── verda_deploy.py     # GPU deployment logic
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
├── tests/              # Test suite
└── docs/
    ├── api_reference.md     # API documentation
    ├── quickstart.md        # Getting started guide
    ├── ARCHITECTURE.md      # Technical architecture
    ├── ROADMAP.md           # Product roadmap
    └── specs/
        └── VOICE_COLLECTION_MODULE.md  # Voice collection spec
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Code Style

- Python: PEP 8 with 100 char line limit
- JavaScript: ES6+ with async/await
- Use `black` and `isort` for Python formatting

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guidelines.

---

## Roadmap

| Phase | Target | Focus |
|-------|--------|-------|
| 1. Foundation | Now | Core TTS, deployments, API keys |
| 2. Production | Q1 2026 | Auth, billing, monitoring |
| 3. Marketplace | Q2 2026 | Voice collection, marketplace |
| 4. Enterprise | Q3 2026 | SSO, private deployments, SLA |
| 5. Platform | Q4 2026 | STT, voice agents, workflows |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed roadmap.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Coding standards
- Pull request process
- Issue guidelines

### Current Issues

Check [ISSUES.md](ISSUES.md) for detailed, prioritized issues organized by milestone. Good first issues are tagged with labels.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/quickstart.md) | Get up and running |
| [API Reference](docs/api_reference.md) | Complete API documentation |
| [Architecture](docs/ARCHITECTURE.md) | Technical design |
| [Roadmap](docs/ROADMAP.md) | Product roadmap |
| [Voice Collection Spec](docs/specs/VOICE_COLLECTION_MODULE.md) | Voice crowdsourcing module |
| [Issues](ISSUES.md) | Detailed issue tracker |

---

## License

[MIT License](LICENSE)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/wallscaler/voiceflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wallscaler/voiceflow/discussions)
- **Email**: support@voiceflow.app

---

*Built with FastAPI, Tailwind CSS, and GPU power.*
