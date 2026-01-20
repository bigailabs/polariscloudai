# VoiceFlow API - Quick Start Guide

Get up and running with VoiceFlow TTS API in under 5 minutes.

---

## Overview

VoiceFlow API provides enterprise-grade text-to-speech with:
- **Auto-scaling GPU infrastructure** (scale to zero when idle)
- **Voice cloning** (clone any voice from a 30s sample)
- **Low latency** (<3s response time)
- **Simple REST API** (just curl commands!)

---

## Prerequisites

- **Management Console Access**: [http://localhost:7860](http://localhost:7860)
- **Command line** (Terminal on Mac/Linux, PowerShell on Windows)
- **cURL** (pre-installed on most systems)

Optional:
- Python 3.7+ for advanced examples
- Audio player for testing WAV files

---

## Step 1: Deploy Your TTS Server

1. **Open the Management Console**
   ```
   http://localhost:7860
   ```

2. **Navigate to the Deploy tab**

3. **Configure deployment:**
   - **GPU Type:** A100 40GB (recommended)
   - **Spot Instances:** Enabled (60-75% cheaper!)

4. **Click "Deploy Server"**

5. **Wait for deployment** (~2-5 minutes)
   - Container status: healthy
   - Application status: ready
   - You'll receive your endpoint URL

**Your endpoint will look like:**
```
https://containers.datacrunch.io/voiceflow-1234567890
```

Tip: Copy this URL - you'll need it for all API requests!

---

## Step 2: Generate Your First API Key

1. **In the Management Console, go to the "API Keys" tab**

2. **Fill in the form:**
   - **Key Name:** "My First Key" (or leave blank)
   - **Key Type:** Live

3. **Click "Generate API Key"**

4. **Copy your API key immediately!**
   ```
   vf_live_AbCdEf123456...
   ```

Important: You won't be able to see this key again! Store it securely.

**Add to your environment:**
```bash
# Mac/Linux
export VOICEFLOW_API_KEY="vf_live_xxxxx"

# Windows PowerShell
$env:VOICEFLOW_API_KEY="vf_live_xxxxx"
```

---

## Step 3: Make Your First Request

### Check Server Health

First, verify your server is ready:

```bash
curl https://your-endpoint/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "model": "chatterbox-turbo",
  "device": "cuda",
  "ready": true
}
```

### Generate Speech

Now generate your first audio:

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Hello, I am VoiceFlow! Welcome to neural text-to-speech." \
  --output hello.wav
```

**Play your audio:**
```bash
# Mac
afplay hello.wav

# Linux
aplay hello.wav

# Windows
start hello.wav
```

Congratulations! You just generated your first AI voice!

---

## Step 4: Try Voice Cloning

Voice cloning lets you replicate any voice from a short audio sample.

### Prepare Voice Sample

1. **Record or find a voice sample** (10-30 seconds ideal)
2. **Save as:** `voice_sample.wav`

**Tips for best results:**
- Clear audio (no background noise)
- Natural speaking pace
- Single speaker only
- WAV, MP3, or FLAC format

### Generate with Cloned Voice

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=This is my cloned voice speaking!" \
  -F "voice_ref=@voice_sample.wav" \
  --output cloned_voice.wav
```

Listen to the result:
```bash
afplay cloned_voice.wav  # Mac
aplay cloned_voice.wav   # Linux
```

---

## Step 5: Add Expressive Speech

VoiceFlow supports expressive tags for more natural speech:

### Available Tags

- `[laugh]` - Add laughter
- `[sigh]` - Add sighing
- `[whisper]` - Whisper mode
- `[shout]` - Emphatic speech
- `[music]` - Musical intonation

### Example with Expression

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Oh wow, that's amazing! [laugh] I can't believe it worked!" \
  --output expressive.wav
```

### Multiple Expressions

```bash
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=[whisper]Let me tell you a secret...[whisper] [sigh]It's quite remarkable.[sigh]" \
  --output multi_expression.wav
```

---

## Common Use Cases

### 1. AI Assistant Voice

```bash
# Friendly greeting
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=Hello! How can I help you today?" \
  --output assistant_greeting.wav

# Helpful response
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=I'd be happy to help with that! Let me look into it for you." \
  --output assistant_response.wav
```

### 2. Content Narration

```bash
# Podcast intro
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=Welcome to Tech Talk, the podcast where we explore the latest in AI and technology." \
  --output podcast_intro.wav

# Video narration
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=In this tutorial, we'll learn how to build a neural network from scratch." \
  --output tutorial_narration.wav
```

### 3. Audiobook Production

```bash
# Chapter reading
TEXT="Chapter One. It was a bright cold day in April, and the clocks were striking thirteen."

curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=$TEXT" \
  --output chapter_1.wav
```

### 4. Accessibility

```bash
# Screen reader
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=Button clicked. Settings menu opened." \
  --output screen_reader.wav
```

---

## Python Integration

### Basic Example

```python
import os
import requests

# Configuration
API_KEY = os.getenv("VOICEFLOW_API_KEY")
ENDPOINT = "https://your-endpoint"

def generate_speech(text, output_file="output.wav"):
    """Generate speech from text"""
    response = requests.post(
        f"{ENDPOINT}/generate",
        headers={"X-API-Key": API_KEY},
        files={"text": (None, text)}
    )

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Generated: {output_file}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

# Usage
generate_speech("Hello from Python!")
```

### Voice Cloning Example

```python
def generate_with_voice(text, voice_file, output_file="cloned.wav"):
    """Generate speech with voice cloning"""
    with open(voice_file, "rb") as voice:
        response = requests.post(
            f"{ENDPOINT}/generate",
            headers={"X-API-Key": API_KEY},
            files={
                "text": (None, text),
                "voice_ref": (voice_file, voice, "audio/wav")
            }
        )

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Generated with cloned voice: {output_file}")
    else:
        print(f"Error: {response.status_code}")

# Usage
generate_with_voice(
    "This is my cloned voice!",
    "voice_sample.wav",
    "cloned_output.wav"
)
```

### Batch Processing

```python
def batch_generate(texts, prefix="output"):
    """Generate multiple audio files"""
    for i, text in enumerate(texts):
        print(f"Processing {i+1}/{len(texts)}...")
        generate_speech(text, f"{prefix}_{i}.wav")
    print("Batch complete!")

# Usage
scripts = [
    "Welcome to our podcast!",
    "Today we're discussing AI.",
    "Thanks for listening!"
]

batch_generate(scripts, prefix="podcast")
```

---

## Troubleshooting

### Error: "missing_api_key"

**Problem:** No API key in request

**Solution:**
```bash
# Add X-API-Key header
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: vf_live_xxxxx" \
  -F "text=Hello"
```

### Error: "invalid_api_key"

**Problem:** API key is invalid or revoked

**Solutions:**
1. Check for typos in API key
2. Verify key format: `vf_live_xxxxx` or `vf_test_xxxxx`
3. Generate a new key in Management Console
4. Check that key hasn't been revoked

### Error: 503 Service Unavailable

**Problem:** Server is still loading the model

**Solution:**
```bash
# Check readiness
curl https://your-endpoint/ready

# Wait for 200 OK response before sending generate requests
```

**Typical loading time:** 1-3 minutes for cold start

### Slow Response Times

**Problem:** Request takes >10 seconds

**Possible causes:**
1. **Cold start:** First request after idle period (scale-up delay)
2. **Long text:** Very long input text takes longer
3. **Network latency:** Check your internet connection

**Solutions:**
- Keep server warm with periodic health checks
- Break long texts into shorter chunks
- Use closer geographic region if available

### Audio Quality Issues

**Problem:** Generated audio sounds distorted or unclear

**Solutions:**
1. **For voice cloning:** Use higher quality voice samples
   - 15-30 seconds optimal
   - No background noise
   - Clear speech, natural pace

2. **For regular TTS:** Text may have problematic characters
   - Remove special characters
   - Spell out numbers/abbreviations
   - Use proper punctuation

---

## Quick Reference

### Essential Commands

```bash
# Check health
curl https://your-endpoint/health

# Check readiness
curl https://your-endpoint/ready

# Generate speech
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=Your text here" \
  --output output.wav

# Voice cloning
curl -X POST https://your-endpoint/generate \
  -H "X-API-Key: $VOICEFLOW_API_KEY" \
  -F "text=Your text" \
  -F "voice_ref=@voice.wav" \
  --output cloned.wav
```

---

**Ready to build something amazing? Start generating voices now!**

*Last Updated: 2026-01-03*
