# Contributing to VoiceFlow

Thank you for your interest in contributing to VoiceFlow! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- **Be respectful** - Treat everyone with respect and kindness
- **Be inclusive** - Welcome contributions from everyone
- **Be constructive** - Provide helpful feedback
- **Be professional** - Keep discussions focused on the project

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ (for frontend work)
- Docker (for running TTS workers)
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/voiceflow.git
   cd voiceflow
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/wallscaler/voiceflow.git
   ```

---

## Development Setup

### Backend (Console Server)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run in demo mode (no Verda credentials needed)
python app_server.py
```

The server will start at `http://localhost:8080`.

### Frontend (Dashboard)

The frontend is a single HTML file (`app.html`) with embedded JavaScript and Tailwind CSS. No build step required.

To work on the frontend:
1. Start the backend server
2. Open `http://localhost:8080` in your browser
3. Edit `app.html` and refresh

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

---

## Making Changes

### Branching Strategy

- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation changes

### Creating a Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-new-feature
```

### Commit Messages

Follow the conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (formatting, semicolons, etc.)
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**
```
feat(api): add voice cloning endpoint

fix(console): fix deployment status not updating

docs(readme): add installation instructions

refactor(auth): simplify API key validation
```

---

## Coding Standards

### Python

We follow PEP 8 with some modifications:

```python
# Line length: 100 characters max

# Imports: grouped and sorted
import os
import sys
from datetime import datetime
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import Deployment
from .utils import validate_key

# Classes: Use docstrings
class DeploymentService:
    """
    Manages GPU deployments via Verda API.

    Attributes:
        client: VerdaClient instance
    """

    def create_deployment(self, name: str, gpu_type: str) -> dict:
        """
        Create a new deployment.

        Args:
            name: Deployment name
            gpu_type: GPU type (e.g., "A100-40GB")

        Returns:
            Deployment details dict

        Raises:
            HTTPException: If deployment fails
        """
        pass

# Functions: Type hints
def calculate_cost(hours: float, rate: float) -> float:
    """Calculate deployment cost."""
    return hours * rate

# Variables: snake_case
deployment_count = 0
api_key_prefix = "vf_live_"

# Constants: UPPER_CASE
MAX_DEPLOYMENTS = 10
DEFAULT_GPU = "A100-40GB"
```

### JavaScript (in app.html)

```javascript
// Use modern ES6+ features
const API_BASE = '/api';

// Async/await for API calls
async function loadDeployments() {
    try {
        const response = await fetch(`${API_BASE}/deployments`);
        const data = await response.json();
        return data.deployments;
    } catch (error) {
        console.error('Error loading deployments:', error);
        return [];
    }
}

// Template literals for HTML
function createCard(deployment) {
    return `
        <div class="card">
            <h3>${deployment.name}</h3>
            <p>Status: ${deployment.status}</p>
        </div>
    `;
}

// Error handling
function handleError(error, context) {
    console.error(`Error in ${context}:`, error);
    toastManager.error('Error', error.message);
}
```

### CSS (Tailwind)

```html
<!-- Use Tailwind classes consistently -->
<div class="card bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition">
    <h3 class="text-lg font-semibold mb-2">Title</h3>
    <p class="text-sm text-gray-600">Description</p>
</div>

<!-- Custom classes in <style> section -->
<style>
    .tab-active {
        border-bottom: 2px solid #f06820;
        color: #f06820;
    }
</style>
```

---

## Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_api.py          # API endpoint tests
├── test_auth.py         # Authentication tests
├── test_deployments.py  # Deployment tests
└── test_billing.py      # Billing tests
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from app_server import app

client = TestClient(app)

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_returns_200(self):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_format(self):
        """Health endpoint should return correct format."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"


class TestAPIKeys:
    """Tests for API key management."""

    @pytest.fixture
    def api_key(self):
        """Create a test API key."""
        response = client.post(
            "/api/keys/generate",
            json={"name": "Test Key"}
        )
        return response.json()["key"]

    def test_generate_key_returns_valid_format(self, api_key):
        """Generated key should have correct prefix."""
        assert api_key["key"].startswith("vf_live_")
```

### Test Coverage Goals

- Unit tests: 80%+ coverage
- Integration tests: All API endpoints
- E2E tests: Critical user flows

---

## Pull Request Process

### Before Submitting

1. **Update from main:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Check code style:**
   ```bash
   # Python
   pip install black isort flake8
   black .
   isort .
   flake8 .
   ```

4. **Update documentation** if needed

### PR Template

When creating a PR, include:

```markdown
## Summary
Brief description of changes.

## Changes
- Added X feature
- Fixed Y bug
- Updated Z documentation

## Testing
- [ ] All existing tests pass
- [ ] Added new tests for changes
- [ ] Manually tested in browser

## Screenshots
(If UI changes)

## Related Issues
Closes #123
```

### Review Process

1. Create PR against `main`
2. Automated checks run (tests, linting)
3. Code review by maintainers
4. Address feedback
5. Squash and merge

---

## Issue Guidelines

### Bug Reports

Use this template:

```markdown
**Describe the bug**
Clear description of the issue.

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen.

**Screenshots**
If applicable.

**Environment:**
- OS: [e.g., macOS 14]
- Browser: [e.g., Chrome 120]
- Python version: [e.g., 3.10]

**Additional context**
Any other information.
```

### Feature Requests

Use this template:

```markdown
**Is your feature request related to a problem?**
Description of the problem.

**Describe the solution you'd like**
Clear description of desired outcome.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Mockups, examples, etc.
```

---

## Getting Help

- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to VoiceFlow! 🎙️
