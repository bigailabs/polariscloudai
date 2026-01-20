# VoiceFlow API Reference

Complete API documentation for the VoiceFlow Text-to-Speech API.

---

## Table of Contents

- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
  - [POST /generate](#post-generate)
  - [GET /health](#get-health)
  - [GET /ready](#get-ready)
- [Request Format](#request-format)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)
- [Best Practices](#best-practices)

---

## Authentication

VoiceFlow API uses API key authentication via the `X-API-Key` header.

### Getting an API Key

1. Open the [Management Console](http://localhost:7860)
2. Navigate to the **API Keys** tab
3. Click **Generate API Key**
4. Copy your key (format: `vf_live_xxxxx` or `vf_test_xxxxx`)

### Using Your API Key

Include your API key in the `X-API-Key` header:

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Hello world"
```

**Security Best Practices:**
- Store keys in environment variables, not in code
- Never commit keys to version control
- Use test keys (`vf_test_`) for development
- Rotate live keys (`vf_live_`) regularly
- Revoke compromised keys immediately

---

## Base URL

Your base URL is provided when you deploy a TTS server via the Management Console:

```
https://containers.datacrunch.io/voiceflow-xxxxx
```

**Example:**
```
https://containers.datacrunch.io/voiceflow-1234567890
```

All endpoints are relative to this base URL.

---

## Endpoints

### POST /generate

Generate speech from text using Chatterbox Turbo TTS.

#### Authentication
**Required:** Yes (X-API-Key header)

#### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Text to synthesize (max ~1000 characters) |
| `voice_ref` | file | No | Audio file for voice cloning (WAV, MP3, etc.) |

**Supported Text Tags:**
- `[laugh]` - Add laughter
- `[sigh]` - Add sighing
- `[whisper]` - Whisper mode
- `[shout]` - Emphatic speech
- `[music]` - Musical intonation

#### Response

**Success (200 OK):**

- **Content-Type:** `audio/wav`
- **Format:** 16-bit PCM WAV
- **Sample Rate:** 24,000 Hz
- **Channels:** Mono

**Example Request:**

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Hello, I am VoiceFlow! [laugh]" \
  --output speech.wav
```

**Example with Voice Cloning:**

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=This is my cloned voice speaking" \
  -F "voice_ref=@my_voice_sample.wav" \
  --output cloned_speech.wav
```

#### Error Responses

**401 Unauthorized - Missing API Key:**
```json
{
  "detail": {
    "error": "missing_api_key",
    "message": "API key required. Include 'X-API-Key' header in your request.",
    "docs": "https://docs.voiceflow.app/authentication"
  }
}
```

**401 Unauthorized - Invalid API Key:**
```json
{
  "detail": {
    "error": "invalid_api_key",
    "message": "Invalid API key. Check your key or generate a new one.",
    "docs": "https://docs.voiceflow.app/authentication"
  }
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error message describing the failure"
}
```

---

### GET /health

Check API server health and status.

#### Authentication
**Required:** No (public endpoint)

#### Response

**Success (200 OK):**

```json
{
  "status": "healthy",
  "model": "chatterbox-turbo",
  "device": "cuda",
  "ready": true,
  "loading_time_seconds": null,
  "loaded_at": "2026-01-03T10:30:45.123456",
  "uptime_seconds": 3600.5
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"healthy"` or `"loading"` |
| `model` | string | Model name (`"chatterbox-turbo"`) |
| `device` | string | Compute device (`"cuda"` or `"cpu"`) |
| `ready` | boolean | Whether model is ready to serve requests |
| `loading_time_seconds` | float/null | Time spent loading (null if loaded) |
| `loaded_at` | string/null | ISO timestamp when model finished loading |
| `uptime_seconds` | float/null | Seconds since model became ready |

**Example Request:**

```bash
curl https://your-endpoint/health
```

**Use Cases:**
- Monitoring and alerting
- Health checks in load balancers
- Verify server is running before sending requests

---

### GET /ready

Kubernetes-style readiness probe.

#### Authentication
**Required:** No (public endpoint)

#### Response

**Success (200 OK):**
```json
{
  "ready": true,
  "message": "Service ready"
}
```

**Service Unavailable (503):**
```json
{
  "detail": {
    "ready": false,
    "message": "Model still loading",
    "loading_time_seconds": 45.2
  }
}
```

**Example Request:**

```bash
curl https://your-endpoint/ready
```

**Use Cases:**
- Startup probes (wait for model to load)
- Deployment health checks
- Auto-scaling readiness signals

---

## Request Format

### Content Types

- **POST /generate:** `multipart/form-data` (for file uploads)
- **GET endpoints:** No body required

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes (for /generate) | Your API key |
| `Content-Type` | Auto-set | Set by client (multipart/form-data) |

### File Upload Requirements

**Voice Reference Audio:**
- **Formats:** WAV, MP3, FLAC, OGG
- **Recommended Length:** 10-30 seconds
- **Max Size:** 10 MB
- **Quality:** Higher quality = better cloning results

---

## Response Format

### Audio Response

**Format:** WAV (RIFF WAVE)
- **Encoding:** PCM_S (16-bit signed integer)
- **Sample Rate:** 24,000 Hz
- **Channels:** 1 (Mono)
- **Bit Depth:** 16 bits per sample

**File Size Estimation:**
- ~48 KB per second of audio
- ~2.88 MB per minute

### JSON Responses

All JSON responses follow this structure:

**Success:**
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

**Error:**
```json
{
  "detail": "Error message"
}
```

Or:
```json
{
  "detail": {
    "error": "error_code",
    "message": "Human-readable error",
    "docs": "https://docs.voiceflow.app/errors"
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 401 | Unauthorized | Missing or invalid API key |
| 500 | Internal Server Error | Model error, server issue |
| 503 | Service Unavailable | Model still loading (only /ready) |

### Error Response Format

```json
{
  "detail": {
    "error": "error_code",
    "message": "Human-readable description",
    "docs": "https://docs.voiceflow.app/errors"
  }
}
```

### Common Errors

**Missing API Key:**
```bash
# Error
curl -X POST https://your-endpoint/generate \
  -F "text=Hello"

# Fix
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Hello"
```

**Invalid API Key:**
- Verify key format: `vf_live_` or `vf_test_`
- Check for typos
- Ensure key hasn't been revoked
- Generate new key if needed

**Model Not Ready:**
```bash
# Check if model is ready first
curl https://your-endpoint/ready

# Wait for 200 OK before sending generate requests
```

---

## Rate Limits

**Current Rate Limits:**
- **None enforced** (usage-based pricing applies)

**Auto-Scaling Behavior:**
- **Concurrent requests per replica:** 1
- **Max replicas:** 3
- **Queue timeout:** 1 hour

**What This Means:**
- 1st request: Processed immediately (if replica running)
- 2nd-3rd requests: Trigger scale-up (30s delay)
- 4th+ requests: Queued (max 1 hour wait)

**Best Practices:**
- Don't send more than 3 concurrent requests
- Implement client-side queuing for bulk jobs
- Add retry logic for failed requests

---

## Best Practices

### Authentication

```python
# Good - API key in environment variable
import os
import requests

API_KEY = os.getenv("VOICEFLOW_API_KEY")
headers = {"X-API-Key": API_KEY}

response = requests.post(
    "https://your-endpoint/generate",
    headers=headers,
    files={"text": (None, "Hello world")}
)
```

```python
# Bad - API key hardcoded
API_KEY = "vf_live_xxxxx"  # Never do this!
```

### Request Handling

```python
# Good - Error handling with retries
import time

def generate_speech(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://your-endpoint/generate",
                headers={"X-API-Key": API_KEY},
                files={"text": (None, text)},
                timeout=30
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Voice Cloning

```python
# Good - Voice cloning with quality audio
with open("voice_sample.wav", "rb") as voice_file:
    response = requests.post(
        "https://your-endpoint/generate",
        headers={"X-API-Key": API_KEY},
        files={
            "text": (None, "This is my cloned voice"),
            "voice_ref": ("voice.wav", voice_file, "audio/wav")
        }
    )
```

**Tips for Best Voice Cloning Results:**
- Use 15-30 second samples
- Clean audio (no background noise)
- Clear speech (not mumbled)
- Natural speaking pace
- Single speaker only

### Health Monitoring

```python
# Good - Wait for server ready before use
import time
import requests

def wait_for_ready(endpoint, timeout=300):
    """Wait for server to be ready"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{endpoint}/ready", timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    return False

# Usage
if wait_for_ready("https://your-endpoint"):
    # Server is ready, send requests
    generate_speech("Hello world")
```

### Batching Requests

```python
# Good - Sequential processing with progress
texts = ["Text 1", "Text 2", "Text 3"]

for i, text in enumerate(texts):
    print(f"Processing {i+1}/{len(texts)}...")
    audio = generate_speech(text)
    with open(f"output_{i}.wav", "wb") as f:
        f.write(audio)
```

**Note:** API doesn't support batch endpoints. Process sequentially or use multiple API endpoints.

---

## Code Examples

### Python

```python
import os
import requests

# Configuration
API_KEY = os.getenv("VOICEFLOW_API_KEY")
ENDPOINT = "https://your-endpoint"

# Simple generation
def generate_speech(text):
    response = requests.post(
        f"{ENDPOINT}/generate",
        headers={"X-API-Key": API_KEY},
        files={"text": (None, text)}
    )
    response.raise_for_status()
    return response.content

# Save to file
audio = generate_speech("Hello, I am VoiceFlow!")
with open("output.wav", "wb") as f:
    f.write(audio)
```

### Node.js

```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

const API_KEY = process.env.VOICEFLOW_API_KEY;
const ENDPOINT = 'https://your-endpoint';

async function generateSpeech(text) {
    const form = new FormData();
    form.append('text', text);

    const response = await axios.post(
        `${ENDPOINT}/generate`,
        form,
        {
            headers: {
                'X-API-Key': API_KEY,
                ...form.getHeaders()
            },
            responseType: 'arraybuffer'
        }
    );

    return response.data;
}

// Usage
generateSpeech('Hello world')
    .then(audio => fs.writeFileSync('output.wav', audio))
    .catch(err => console.error(err));
```

### cURL

```bash
#!/bin/bash

API_KEY="vf_live_xxxxx"
ENDPOINT="https://your-endpoint"

# Simple generation
curl -X POST "$ENDPOINT/generate" \
  -H "X-API-Key: $API_KEY" \
  -F "text=Hello, I am VoiceFlow!" \
  --output speech.wav

# With voice cloning
curl -X POST "$ENDPOINT/generate" \
  -H "X-API-Key: $API_KEY" \
  -F "text=This is my cloned voice" \
  -F "voice_ref=@voice_sample.wav" \
  --output cloned_speech.wav

# Check health
curl "$ENDPOINT/health"
```

---

## Support

**Issues or Questions?**
- GitHub: [github.com/wallscaler/violetmvp](https://github.com/wallscaler/violetmvp)
- Email: support@voiceflow.app
- Management Console: [localhost:7860](http://localhost:7860)

**Additional Resources:**
- [Quick Start Guide](quickstart.md)
- [Voice Cloning Tutorial](voice_cloning.md)
- [Management Console Guide](management_console.md)

---

*Last Updated: 2026-01-03*
