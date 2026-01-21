# VoiceFlow - Product Market Fit Issues

> Comprehensive issue tracker for getting VoiceFlow to PMF
> Last Updated: January 20, 2026

---

## Overview

This document contains **50+ detailed issues** organized by priority and milestone to transform VoiceFlow from a demo into a production-ready Voice AI platform.

**Target:** Launch public beta in 8 weeks

---

## Milestone 1: Foundation (Week 1-2)
*Critical infrastructure that blocks everything else*

### Issue #1: Implement User Authentication System
**Priority:** P0 - Critical
**Effort:** 5 days
**Labels:** `security`, `backend`, `critical`

**Description:**
Currently VoiceFlow has no authentication. Anyone can access all endpoints, manage deployments, and delete API keys. This is a critical security vulnerability.

**Requirements:**
- [ ] User registration with email/password
- [ ] Email verification flow
- [ ] Login endpoint returning JWT tokens
- [ ] Token refresh mechanism
- [ ] Password reset flow
- [ ] Session management (logout, revoke all sessions)

**Technical Spec:**
```python
# New endpoints needed:
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/forgot-password
POST /api/auth/reset-password
POST /api/auth/verify-email
GET  /api/auth/me

# User model:
class User(BaseModel):
    id: str
    email: str
    password_hash: str  # bcrypt
    name: str
    company: Optional[str]
    plan: str  # free, pro, enterprise
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

# JWT payload:
{
    "sub": "user_id",
    "email": "user@example.com",
    "plan": "pro",
    "exp": 1706000000,
    "iat": 1705900000
}
```

**Acceptance Criteria:**
- Users can register with email/password
- JWT tokens expire after 24 hours
- Refresh tokens expire after 7 days
- All existing endpoints require authentication
- Demo mode works without auth for local development

---

### Issue #2: Add Authentication Middleware
**Priority:** P0 - Critical
**Effort:** 2 days
**Labels:** `security`, `backend`
**Depends on:** #1

**Description:**
Create FastAPI middleware that validates JWT tokens on all protected routes.

**Technical Spec:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Usage:
@app.get("/api/deployments")
async def get_deployments(user: User = Depends(get_current_user)):
    # user is now available
    pass
```

**Acceptance Criteria:**
- All `/api/*` routes (except auth) require valid JWT
- Invalid tokens return 401 Unauthorized
- Expired tokens return 401 with "Token expired" message
- Public routes (`/`, `/health`, `/api/auth/*`) work without auth

---

### Issue #3: Migrate from JSON to PostgreSQL
**Priority:** P0 - Critical
**Effort:** 5 days
**Labels:** `backend`, `database`, `critical`

**Description:**
Replace JSON file storage with PostgreSQL for reliability, performance, and data integrity.

**Current State:**
- `api_keys.json` - API keys (plaintext!)
- `settings.json` - User settings
- `usage_stats.json` - Usage analytics
- `deployment_metrics.json` - Metrics history
- `usage_limits.json` - Rate limit config
- `cost_tracking.json` - Billing data

**Database Schema:**
```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    settings JSONB DEFAULT '{}'
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    key_hash VARCHAR(255) NOT NULL,  -- bcrypt hash, NOT plaintext!
    key_prefix VARCHAR(20) NOT NULL,  -- "vf_live_abc..." for display
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    revoked_at TIMESTAMP,
    request_count INTEGER DEFAULT 0
);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

-- Deployments
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    external_id VARCHAR(255),  -- Verda deployment ID
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    deployment_type VARCHAR(50),  -- serverless, raw_compute
    gpu_type VARCHAR(100),
    endpoint VARCHAR(500),
    hourly_cost DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);
CREATE INDEX idx_deployments_user ON deployments(user_id);
CREATE INDEX idx_deployments_status ON deployments(status);

-- Usage Events
CREATE TABLE usage_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    deployment_id UUID REFERENCES deployments(id),
    event_type VARCHAR(50),  -- api_request, deployment_start, etc.
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_usage_events_user_date ON usage_events(user_id, created_at);
CREATE INDEX idx_usage_events_key ON usage_events(api_key_id);

-- Webhooks
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    url VARCHAR(500) NOT NULL,
    events TEXT[] NOT NULL,
    secret VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_triggered TIMESTAMP
);

-- Audit Log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user ON audit_log(user_id, created_at);
```

**Migration Script:**
```python
# migrate_json_to_postgres.py
import json
import asyncpg
import bcrypt

async def migrate():
    conn = await asyncpg.connect(DATABASE_URL)

    # Migrate API keys (hash them!)
    with open('api_keys.json') as f:
        keys = json.load(f)

    for key in keys:
        key_hash = bcrypt.hashpw(key['key'].encode(), bcrypt.gensalt())
        key_prefix = key['key'][:15] + '...'
        await conn.execute('''
            INSERT INTO api_keys (id, name, description, key_hash, key_prefix, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', key['id'], key['name'], key.get('description'),
            key_hash.decode(), key_prefix, key['created_at'])

    # Similar for other JSON files...
```

**Acceptance Criteria:**
- All data stored in PostgreSQL
- Existing JSON data migrated
- API keys hashed with bcrypt
- Connection pooling configured (asyncpg)
- Database transactions for multi-step operations

---

### Issue #4: Hash API Keys with bcrypt
**Priority:** P0 - Critical
**Effort:** 1 day
**Labels:** `security`, `backend`
**Depends on:** #3

**Description:**
API keys are currently stored in plaintext. If the database is compromised, all keys are exposed.

**Current (INSECURE):**
```python
new_key = {
    "key": "vf_live_abc123...",  # Plaintext!
}
```

**Required:**
```python
import bcrypt
import secrets

def generate_api_key():
    # Generate key
    raw_key = f"vf_live_{secrets.token_urlsafe(32)}"

    # Hash for storage
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt())

    # Prefix for display (user can identify key without seeing full value)
    key_prefix = raw_key[:15] + "..."

    return {
        "raw_key": raw_key,      # Return ONCE to user, never store
        "key_hash": key_hash,    # Store this
        "key_prefix": key_prefix # Store this for UI display
    }

def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(provided_key.encode(), stored_hash.encode())
```

**Acceptance Criteria:**
- New API keys hashed before storage
- Raw key shown only once at creation
- Key prefix shown in dashboard for identification
- Existing keys migrated (re-hash or force regeneration)

---

### Issue #5: Implement Role-Based Access Control (RBAC)
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `security`, `backend`
**Depends on:** #1, #2

**Description:**
Add role-based permissions for team collaboration.

**Roles:**
| Role | Permissions |
|------|-------------|
| `owner` | Full access, billing, delete account |
| `admin` | Manage deployments, keys, team members |
| `developer` | Create deployments, use API keys |
| `viewer` | Read-only access to dashboard |

**Database:**
```sql
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES users(id),  -- Owner's user ID
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) NOT NULL,
    invited_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP
);
```

**Middleware:**
```python
def require_role(allowed_roles: List[str]):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# Usage:
@app.delete("/api/deployments/{id}")
async def delete_deployment(
    id: str,
    user: User = Depends(require_role(["owner", "admin"]))
):
    pass
```

**Acceptance Criteria:**
- Users can invite team members
- Roles enforced on all endpoints
- Audit log tracks who did what
- Team members can be removed

---

### Issue #6: Secure CORS Configuration
**Priority:** P0 - Critical
**Effort:** 0.5 days
**Labels:** `security`, `backend`

**Description:**
Current CORS allows all origins with credentials, enabling XSS and CSRF attacks.

**Current (INSECURE):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Anyone!
    allow_credentials=True,  # With cookies!
)
```

**Required:**
```python
ALLOWED_ORIGINS = [
    "https://voiceflow.ai",
    "https://console.voiceflow.ai",
    "https://api.voiceflow.ai",
]

if os.getenv("ENVIRONMENT") == "development":
    ALLOWED_ORIGINS.extend([
        "http://localhost:3000",
        "http://localhost:8080",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=86400,  # Cache preflight for 24 hours
)
```

**Acceptance Criteria:**
- Production only allows specific domains
- Development allows localhost
- Credentials only sent to trusted origins
- Preflight requests cached

---

### Issue #7: Add Input Validation & Sanitization
**Priority:** P0 - Critical
**Effort:** 2 days
**Labels:** `security`, `backend`

**Description:**
No input validation exists. Users can submit malicious data.

**Vulnerabilities:**
- SQL injection (when we add database)
- XSS via stored data
- Path traversal in file operations
- Command injection in deployment names

**Required:**
```python
from pydantic import BaseModel, validator, EmailStr
import re

class CreateDeploymentRequest(BaseModel):
    name: str
    gpu_type: str

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{2,62}$', v):
            raise ValueError('Name must be 3-63 chars, alphanumeric and hyphens only')
        return v.lower()

    @validator('gpu_type')
    def validate_gpu(cls, v):
        allowed = ['Tesla-V100-16GB', 'A100-40GB', 'A100-80GB', 'H100', 'L40S']
        if v not in allowed:
            raise ValueError(f'GPU must be one of: {allowed}')
        return v

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain number')
        return v

    @validator('name')
    def validate_name(cls, v):
        # Prevent XSS
        v = v.strip()
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Name must be 1-100 characters')
        # Remove HTML tags
        v = re.sub(r'<[^>]*>', '', v)
        return v
```

**Acceptance Criteria:**
- All Pydantic models have validators
- Deployment names are DNS-safe
- Emails validated with EmailStr
- Passwords meet complexity requirements
- HTML stripped from text inputs

---

### Issue #8: Implement Rate Limiting
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `security`, `backend`

**Description:**
No rate limiting allows abuse (DoS, brute force, cost exploitation).

**Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Global rate limit
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Check rate limit from Redis/memory
    pass

# Per-endpoint limits
@app.post("/api/auth/login")
@limiter.limit("5/minute")  # Prevent brute force
async def login():
    pass

@app.post("/api/deployments/deploy")
@limiter.limit("10/hour")  # Prevent cost abuse
async def deploy():
    pass

@app.post("/api/keys/generate")
@limiter.limit("5/hour")  # Limit key creation
async def generate_key():
    pass
```

**Rate Limits:**
| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/auth/login` | 5/min | Prevent brute force |
| `/api/auth/register` | 3/hour | Prevent spam accounts |
| `/api/deployments/deploy` | 10/hour | Prevent cost abuse |
| `/api/keys/generate` | 5/hour | Limit key creation |
| `/api/*` (general) | 100/min | Prevent DoS |

**Acceptance Criteria:**
- Rate limits enforced via Redis (production) or memory (dev)
- 429 Too Many Requests returned when exceeded
- Retry-After header included
- Different limits per endpoint
- Authenticated users get higher limits

---

## Milestone 2: Billing & Monetization (Week 3-4)
*Revenue infrastructure*

### Issue #9: Stripe Integration - Subscriptions
**Priority:** P0 - Critical
**Effort:** 5 days
**Labels:** `billing`, `backend`
**Depends on:** #1, #3

**Description:**
Implement subscription billing with Stripe.

**Plans:**
| Plan | Price | Included | Overage |
|------|-------|----------|---------|
| Free | $0/mo | 1 deployment, 10K requests | N/A |
| Pro | $49/mo | 5 deployments, 100K requests | $0.001/req |
| Enterprise | $299/mo | Unlimited deployments, 1M requests | $0.0005/req |

**Endpoints:**
```python
POST /api/billing/checkout          # Create Stripe checkout session
POST /api/billing/portal            # Customer portal link
GET  /api/billing/subscription      # Current subscription status
POST /api/billing/webhook           # Stripe webhook handler
GET  /api/billing/invoices          # Invoice history
GET  /api/billing/usage             # Current usage vs limits
```

**Stripe Integration:**
```python
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

async def create_checkout_session(user: User, plan: str):
    prices = {
        "pro": "price_xxx",
        "enterprise": "price_yyy",
    }

    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=["card"],
        line_items=[{"price": prices[plan], "quantity": 1}],
        mode="subscription",
        success_url="https://console.voiceflow.ai/billing?success=true",
        cancel_url="https://console.voiceflow.ai/billing?canceled=true",
        metadata={"user_id": user.id},
    )
    return session.url

async def handle_webhook(payload: bytes, signature: str):
    event = stripe.Webhook.construct_event(
        payload, signature, os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    if event.type == "checkout.session.completed":
        # Upgrade user plan
        pass
    elif event.type == "invoice.paid":
        # Record payment
        pass
    elif event.type == "customer.subscription.deleted":
        # Downgrade to free
        pass
```

**Database:**
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    plan VARCHAR(50),
    status VARCHAR(50),  -- active, past_due, canceled
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    stripe_invoice_id VARCHAR(255),
    amount_cents INTEGER,
    status VARCHAR(50),
    pdf_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Acceptance Criteria:**
- Users can subscribe to Pro/Enterprise
- Stripe webhook handles all events
- Subscription status synced to database
- Invoice history available
- Downgrade to free when subscription canceled

---

### Issue #10: Usage Metering & Overage Billing
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `billing`, `backend`
**Depends on:** #9

**Description:**
Track usage and bill for overages.

**Metered Items:**
- API requests (per 1K)
- GPU hours
- Storage (future)
- Bandwidth (future)

**Implementation:**
```python
async def record_usage(user_id: str, metric: str, quantity: int):
    """Record usage for billing"""
    # Store locally
    await db.execute('''
        INSERT INTO usage_events (user_id, event_type, quantity, created_at)
        VALUES ($1, $2, $3, NOW())
    ''', user_id, metric, quantity)

    # Report to Stripe (daily batch)
    # stripe.SubscriptionItem.create_usage_record(...)

async def check_usage_limits(user_id: str) -> bool:
    """Check if user has exceeded plan limits"""
    user = await get_user(user_id)
    usage = await get_current_month_usage(user_id)

    limits = {
        "free": {"requests": 10_000, "deployments": 1},
        "pro": {"requests": 100_000, "deployments": 5},
        "enterprise": {"requests": 1_000_000, "deployments": -1},  # unlimited
    }

    plan_limits = limits[user.plan]

    if usage["requests"] >= plan_limits["requests"]:
        if user.plan == "free":
            raise HTTPException(402, "Upgrade to Pro for more requests")
        # Pro/Enterprise: allow overage, bill later

    return True
```

**Acceptance Criteria:**
- All API requests counted
- GPU hours tracked per deployment
- Usage dashboard shows current vs limit
- Overage automatically billed
- Alerts sent at 80% and 100% of limits

---

### Issue #11: Billing Dashboard UI
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `billing`, `frontend`
**Depends on:** #9, #10

**Description:**
Add billing management to the console UI.

**Features:**
- Current plan display
- Usage meters (requests, deployments, GPU hours)
- Upgrade/downgrade buttons
- Invoice history
- Payment method management (Stripe portal)
- Cost projections

**Wireframe:**
```
+------------------------------------------+
| Billing                                   |
+------------------------------------------+
| Current Plan: Pro ($49/mo)    [Manage]   |
+------------------------------------------+
| Usage This Month                         |
| +----------------+  +----------------+   |
| | API Requests   |  | Deployments    |   |
| | 45,231/100,000 |  | 3/5            |   |
| | [====------]   |  | [======----]   |   |
| +----------------+  +----------------+   |
|                                          |
| +----------------+  +----------------+   |
| | GPU Hours      |  | Est. Bill      |   |
| | 127.5 hrs      |  | $49.00 + $12   |   |
| | $0.24/hr avg   |  | (overage)      |   |
| +----------------+  +----------------+   |
+------------------------------------------+
| Invoices                                 |
| +--------------------------------------+ |
| | Jan 2026 | $49.00 | Paid | [PDF]    | |
| | Dec 2025 | $61.00 | Paid | [PDF]    | |
| | Nov 2025 | $49.00 | Paid | [PDF]    | |
| +--------------------------------------+ |
+------------------------------------------+
```

**Acceptance Criteria:**
- Users can view current plan and usage
- Upgrade flow opens Stripe Checkout
- Invoice PDFs downloadable
- Payment method editable via Stripe Portal

---

## Milestone 3: Voice Collection Module (Week 5-6)
*New revenue stream and data moat*

### Issue #12: Voice Collection - Database Schema
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `voice-collection`, `database`
**Depends on:** #3

**Description:**
Design database schema for voice collection marketplace.

**Schema:**
```sql
-- Voice Contributors (people who submit voices)
CREATE TABLE contributors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(2),  -- ISO country code
    languages TEXT[],    -- ["en-US", "es-ES"]
    voice_profile JSONB, -- age, gender, accent, etc.
    stripe_account_id VARCHAR(255),  -- For payouts
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    total_earnings_cents INTEGER DEFAULT 0
);

-- Voice Recordings
CREATE TABLE voice_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID REFERENCES contributors(id),

    -- Recording metadata
    audio_url VARCHAR(500) NOT NULL,
    audio_duration_seconds DECIMAL(10, 2),
    transcript TEXT NOT NULL,
    language VARCHAR(10),

    -- Quality metrics (from AI analysis)
    quality_score DECIMAL(3, 2),  -- 0.00 - 1.00
    noise_level DECIMAL(3, 2),
    clarity_score DECIMAL(3, 2),

    -- Review status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected
    rejection_reason TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,

    -- Payment
    payment_cents INTEGER,
    paid_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_recordings_contributor ON voice_recordings(contributor_id);
CREATE INDEX idx_recordings_status ON voice_recordings(status);
CREATE INDEX idx_recordings_language ON voice_recordings(language);

-- Recording Prompts (text for contributors to read)
CREATE TABLE recording_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    language VARCHAR(10),
    category VARCHAR(50),  -- conversational, news, technical
    difficulty VARCHAR(20),  -- easy, medium, hard
    target_duration_seconds INTEGER,
    times_recorded INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE
);

-- Payout History
CREATE TABLE contributor_payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID REFERENCES contributors(id),
    amount_cents INTEGER NOT NULL,
    stripe_transfer_id VARCHAR(255),
    status VARCHAR(50),  -- pending, processing, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**Acceptance Criteria:**
- Schema supports contributor registration
- Recordings linked to contributors
- Quality metrics stored
- Payment tracking integrated

---

### Issue #13: Voice Collection - Contributor Portal
**Priority:** P1 - High
**Effort:** 5 days
**Labels:** `voice-collection`, `frontend`
**Depends on:** #12

**Description:**
Build web portal for voice contributors to record and get paid.

**Pages:**
1. **Landing/Registration** - Sign up to contribute
2. **Dashboard** - Earnings, recording stats, pending payments
3. **Record** - Recording interface with prompts
4. **Earnings** - Payment history, payout settings
5. **Profile** - Voice profile, languages, preferences

**Recording Interface:**
```html
+------------------------------------------+
| Record Your Voice                         |
+------------------------------------------+
| Prompt #1 of 10                          |
|                                          |
| "The quick brown fox jumps over the      |
|  lazy dog near the riverbank."           |
|                                          |
| [====================] 0:00 / 0:05       |
|                                          |
|        [ Start Recording ]               |
|                                          |
| Tips:                                    |
| - Speak clearly at normal pace           |
| - Minimize background noise              |
| - Keep consistent distance from mic      |
+------------------------------------------+
| Earnings: $0.10 per approved recording   |
| Quality Bonus: +$0.05 for 95%+ score     |
+------------------------------------------+
```

**Technical Requirements:**
- WebRTC/MediaRecorder for browser recording
- Audio level visualization
- Playback before submission
- Background noise detection
- Automatic quality scoring

**Acceptance Criteria:**
- Contributors can register and record
- Real-time audio visualization
- Quality feedback before submission
- Earnings displayed in dashboard

---

### Issue #14: Voice Collection - Recording API
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `voice-collection`, `backend`
**Depends on:** #12

**Description:**
API endpoints for voice recording submission and management.

**Endpoints:**
```python
# Contributor Auth
POST /api/contributors/register
POST /api/contributors/login
GET  /api/contributors/me

# Recording
GET  /api/contributors/prompts          # Get next prompts to record
POST /api/contributors/recordings       # Submit recording
GET  /api/contributors/recordings       # List my recordings
GET  /api/contributors/recordings/{id}  # Recording details

# Earnings
GET  /api/contributors/earnings         # Earnings summary
GET  /api/contributors/payouts          # Payout history
POST /api/contributors/payouts/request  # Request payout

# Admin (internal)
GET  /api/admin/recordings/pending      # Review queue
POST /api/admin/recordings/{id}/approve
POST /api/admin/recordings/{id}/reject
```

**Recording Submission:**
```python
@app.post("/api/contributors/recordings")
async def submit_recording(
    audio: UploadFile,
    prompt_id: str,
    contributor: Contributor = Depends(get_current_contributor)
):
    # 1. Validate audio format (WAV, 16kHz, mono)
    # 2. Upload to S3/GCS
    # 3. Queue for quality analysis
    # 4. Create database record
    # 5. Return recording ID

    audio_bytes = await audio.read()

    # Validate format
    if not is_valid_audio(audio_bytes):
        raise HTTPException(400, "Invalid audio format")

    # Upload to cloud storage
    audio_url = await upload_to_storage(audio_bytes, f"{contributor.id}/{uuid4()}.wav")

    # Get prompt
    prompt = await get_prompt(prompt_id)

    # Create record
    recording = await db.execute('''
        INSERT INTO voice_recordings
        (contributor_id, audio_url, transcript, language, status)
        VALUES ($1, $2, $3, $4, 'pending')
        RETURNING id
    ''', contributor.id, audio_url, prompt.text, prompt.language)

    # Queue quality analysis
    await queue_quality_analysis(recording.id)

    return {"id": recording.id, "status": "pending"}
```

**Acceptance Criteria:**
- Audio upload to cloud storage
- Automatic quality analysis queued
- CRUD operations for recordings
- Payout request flow

---

### Issue #15: Voice Collection - Quality Analysis Pipeline
**Priority:** P1 - High
**Effort:** 4 days
**Labels:** `voice-collection`, `backend`, `ml`
**Depends on:** #14

**Description:**
Automated quality analysis for submitted recordings.

**Quality Metrics:**
| Metric | Weight | Description |
|--------|--------|-------------|
| SNR (Signal-to-Noise) | 25% | Background noise level |
| Clarity | 25% | Speech intelligibility |
| Transcript Match | 30% | ASR accuracy vs prompt |
| Audio Quality | 20% | Clipping, distortion, etc. |

**Pipeline:**
```python
# quality_pipeline.py
import librosa
import numpy as np
from faster_whisper import WhisperModel

class QualityAnalyzer:
    def __init__(self):
        self.whisper = WhisperModel("base")

    async def analyze(self, audio_path: str, expected_transcript: str) -> dict:
        # Load audio
        y, sr = librosa.load(audio_path, sr=16000)

        # 1. Signal-to-Noise Ratio
        snr = self.calculate_snr(y)

        # 2. Clarity (spectral centroid variance)
        clarity = self.calculate_clarity(y, sr)

        # 3. Transcript accuracy
        segments, _ = self.whisper.transcribe(audio_path)
        transcript = " ".join([s.text for s in segments])
        transcript_score = self.calculate_wer(transcript, expected_transcript)

        # 4. Audio quality (clipping, distortion)
        audio_quality = self.check_audio_quality(y)

        # Weighted score
        final_score = (
            snr * 0.25 +
            clarity * 0.25 +
            transcript_score * 0.30 +
            audio_quality * 0.20
        )

        return {
            "snr": snr,
            "clarity": clarity,
            "transcript_accuracy": transcript_score,
            "audio_quality": audio_quality,
            "final_score": final_score,
            "transcribed_text": transcript
        }

    def calculate_snr(self, y):
        # Estimate noise from silent portions
        # Return normalized 0-1 score
        pass

    def calculate_clarity(self, y, sr):
        # Spectral analysis
        pass

    def calculate_wer(self, hypothesis, reference):
        # Word Error Rate
        # Return 1 - WER (so higher is better)
        pass

    def check_audio_quality(self, y):
        # Check for clipping, DC offset, etc.
        pass

# Background worker
async def process_quality_queue():
    while True:
        recording_id = await queue.get()
        recording = await get_recording(recording_id)

        # Download audio
        audio_path = await download_audio(recording.audio_url)

        # Analyze
        metrics = await analyzer.analyze(audio_path, recording.transcript)

        # Update database
        await db.execute('''
            UPDATE voice_recordings
            SET quality_score = $1, noise_level = $2, clarity_score = $3
            WHERE id = $4
        ''', metrics['final_score'], 1 - metrics['snr'], metrics['clarity'], recording_id)

        # Auto-approve if score > 0.85
        if metrics['final_score'] >= 0.85:
            await approve_recording(recording_id)
        elif metrics['final_score'] < 0.5:
            await reject_recording(recording_id, "Quality below threshold")
        # Otherwise: manual review
```

**Acceptance Criteria:**
- Recordings analyzed within 5 minutes
- Quality score 0-100
- Auto-approve high quality (>85%)
- Auto-reject low quality (<50%)
- Manual review for middle range

---

### Issue #16: Voice Collection - Contributor Payouts
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `voice-collection`, `billing`
**Depends on:** #12, #14

**Description:**
Pay contributors via Stripe Connect.

**Payout Rules:**
- Minimum payout: $10
- Payment per approved recording: $0.10 - $0.25 (based on quality)
- Quality bonus: +$0.05 for 95%+ score
- Weekly automatic payouts (Fridays)
- Instant payout available for $1 fee

**Stripe Connect Setup:**
```python
import stripe

async def create_contributor_account(contributor: Contributor):
    """Create Stripe Connect Express account"""
    account = stripe.Account.create(
        type="express",
        country=contributor.country,
        email=contributor.email,
        capabilities={
            "transfers": {"requested": True},
        },
    )

    # Save account ID
    await db.execute(
        "UPDATE contributors SET stripe_account_id = $1 WHERE id = $2",
        account.id, contributor.id
    )

    # Return onboarding link
    link = stripe.AccountLink.create(
        account=account.id,
        refresh_url="https://voices.voiceflow.ai/connect/refresh",
        return_url="https://voices.voiceflow.ai/connect/complete",
        type="account_onboarding",
    )
    return link.url

async def process_payout(contributor_id: str):
    """Process pending earnings as payout"""
    contributor = await get_contributor(contributor_id)

    # Calculate pending earnings
    pending = await db.fetchval('''
        SELECT SUM(payment_cents)
        FROM voice_recordings
        WHERE contributor_id = $1 AND status = 'approved' AND paid_at IS NULL
    ''', contributor_id)

    if pending < 1000:  # $10 minimum
        raise HTTPException(400, "Minimum payout is $10")

    # Create Stripe transfer
    transfer = stripe.Transfer.create(
        amount=pending,
        currency="usd",
        destination=contributor.stripe_account_id,
        description=f"VoiceFlow payout - {contributor_id}",
    )

    # Mark recordings as paid
    await db.execute('''
        UPDATE voice_recordings
        SET paid_at = NOW()
        WHERE contributor_id = $1 AND status = 'approved' AND paid_at IS NULL
    ''', contributor_id)

    # Record payout
    await db.execute('''
        INSERT INTO contributor_payouts
        (contributor_id, amount_cents, stripe_transfer_id, status)
        VALUES ($1, $2, $3, 'completed')
    ''', contributor_id, pending, transfer.id)

    return {"amount": pending / 100, "transfer_id": transfer.id}
```

**Acceptance Criteria:**
- Contributors onboard to Stripe Connect
- Automatic weekly payouts
- Payout history visible
- Minimum $10 threshold
- Instant payout option

---

## Milestone 4: Production Infrastructure (Week 7-8)
*Reliability and observability*

### Issue #17: Implement Prometheus Metrics
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `monitoring`, `backend`

**Description:**
Add real metrics collection with Prometheus.

**Metrics to Track:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'voiceflow_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'voiceflow_request_latency_seconds',
    'Request latency',
    ['endpoint']
)

# Business metrics
ACTIVE_DEPLOYMENTS = Gauge(
    'voiceflow_active_deployments',
    'Number of active deployments',
    ['gpu_type']
)

API_KEYS_TOTAL = Gauge(
    'voiceflow_api_keys_total',
    'Total API keys'
)

# Voice collection metrics
RECORDINGS_PENDING = Gauge(
    'voiceflow_recordings_pending',
    'Recordings awaiting review'
)

RECORDINGS_PROCESSED = Counter(
    'voiceflow_recordings_processed_total',
    'Recordings processed',
    ['status']  # approved, rejected
)

# Middleware to track requests
@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)

    return response

# Expose metrics endpoint
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Acceptance Criteria:**
- `/metrics` endpoint returns Prometheus format
- Request count, latency, error rate tracked
- Business metrics (deployments, keys) tracked
- Voice collection metrics tracked

---

### Issue #18: Grafana Dashboard Templates
**Priority:** P2 - Medium
**Effort:** 2 days
**Labels:** `monitoring`, `devops`
**Depends on:** #17

**Description:**
Create Grafana dashboards for monitoring.

**Dashboards:**
1. **Overview** - High-level health
2. **API Performance** - Request latency, error rates
3. **Business Metrics** - Deployments, API keys, revenue
4. **Voice Collection** - Recordings, quality, payouts
5. **Infrastructure** - CPU, memory, database

**Overview Dashboard Panels:**
```json
{
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [{
        "expr": "rate(voiceflow_requests_total[5m])"
      }]
    },
    {
      "title": "Error Rate",
      "type": "stat",
      "targets": [{
        "expr": "sum(rate(voiceflow_requests_total{status=~\"5..\"}[5m])) / sum(rate(voiceflow_requests_total[5m])) * 100"
      }]
    },
    {
      "title": "P95 Latency",
      "type": "gauge",
      "targets": [{
        "expr": "histogram_quantile(0.95, rate(voiceflow_request_latency_seconds_bucket[5m]))"
      }]
    },
    {
      "title": "Active Deployments",
      "type": "stat",
      "targets": [{
        "expr": "sum(voiceflow_active_deployments)"
      }]
    }
  ]
}
```

**Acceptance Criteria:**
- Dashboard JSON exportable
- All key metrics visualized
- Alerts configured for critical thresholds
- Dashboard loads in < 2 seconds

---

### Issue #19: Alerting Rules
**Priority:** P1 - High
**Effort:** 1 day
**Labels:** `monitoring`, `devops`
**Depends on:** #17

**Description:**
Configure alerts for critical issues.

**Alert Rules:**
```yaml
# alerts.yml
groups:
  - name: voiceflow
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: sum(rate(voiceflow_requests_total{status=~"5.."}[5m])) / sum(rate(voiceflow_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate (> 5%)"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(voiceflow_request_latency_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency > 2 seconds"

      # Database connection issues
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"

      # Voice collection backlog
      - alert: RecordingBacklog
        expr: voiceflow_recordings_pending > 1000
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Over 1000 recordings pending review"
```

**Acceptance Criteria:**
- Alerts fire to Slack/PagerDuty
- Critical alerts page on-call
- Warning alerts create tickets
- Alert fatigue minimized

---

### Issue #20: CI/CD Pipeline
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `devops`, `testing`

**Description:**
Automated testing and deployment pipeline.

**GitHub Actions Workflow:**
```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          ruff check .
          black --check .

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/test
        run: |
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t voiceflow:${{ github.sha }} .

      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push voiceflow:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to production
        run: |
          # Trigger deployment (Kubernetes, Railway, etc.)
          curl -X POST ${{ secrets.DEPLOY_WEBHOOK }}
```

**Acceptance Criteria:**
- Tests run on every PR
- Linting enforced (ruff, black)
- Coverage reported to Codecov
- Auto-deploy to production on main merge
- Rollback capability

---

### Issue #21: Error Tracking with Sentry
**Priority:** P2 - Medium
**Effort:** 1 day
**Labels:** `monitoring`, `backend`

**Description:**
Integrate Sentry for error tracking and debugging.

**Implementation:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,  # 10% of requests traced
    environment=os.getenv("ENVIRONMENT", "development"),
    release=os.getenv("GIT_SHA", "unknown"),
)

# Add user context
@app.middleware("http")
async def sentry_context(request: Request, call_next):
    if hasattr(request.state, "user"):
        sentry_sdk.set_user({
            "id": request.state.user.id,
            "email": request.state.user.email,
        })
    return await call_next(request)
```

**Acceptance Criteria:**
- All unhandled exceptions sent to Sentry
- User context attached to errors
- Release tracking enabled
- Source maps uploaded for frontend

---

## Milestone 5: Documentation & SDKs (Week 9-10)
*Developer experience*

### Issue #22: API Documentation Site
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `documentation`, `frontend`

**Description:**
Create comprehensive API documentation.

**Structure:**
```
docs/
├── index.md              # Introduction
├── quickstart.md         # Getting started
├── authentication.md     # Auth guide
├── api-reference/
│   ├── deployments.md    # Deployment endpoints
│   ├── api-keys.md       # API key management
│   ├── analytics.md      # Usage analytics
│   └── webhooks.md       # Webhook setup
├── sdks/
│   ├── python.md         # Python SDK
│   ├── nodejs.md         # Node.js SDK
│   └── cli.md            # CLI tool
├── guides/
│   ├── voice-cloning.md  # Voice cloning tutorial
│   ├── scaling.md        # Scaling guide
│   └── security.md       # Security best practices
└── changelog.md          # API changelog
```

**Tools:**
- Docusaurus or Mintlify for docs site
- OpenAPI/Swagger for API reference
- Code examples in multiple languages

**Acceptance Criteria:**
- All endpoints documented
- Code examples for Python, Node.js, cURL
- Interactive API playground
- Search functionality
- Versioned documentation

---

### Issue #23: Python SDK
**Priority:** P2 - Medium
**Effort:** 4 days
**Labels:** `sdk`, `python`

**Description:**
Official Python SDK for VoiceFlow API.

**Usage:**
```python
from voiceflow import VoiceFlow

client = VoiceFlow(api_key="vf_live_xxx")

# Deploy a TTS server
deployment = client.deployments.create(
    name="my-tts-server",
    gpu_type="A100-40GB",
    deployment_type="serverless"
)

print(f"Deployed: {deployment.endpoint}")

# Generate speech
audio = client.tts.generate(
    text="Hello world!",
    voice="alloy",
    deployment_id=deployment.id
)
audio.save("output.wav")

# List deployments
for d in client.deployments.list():
    print(f"{d.name}: {d.status}")

# Usage analytics
usage = client.usage.get_current_month()
print(f"Requests: {usage.requests}")
print(f"Cost: ${usage.cost}")
```

**Package Structure:**
```
voiceflow/
├── __init__.py
├── client.py           # Main client
├── resources/
│   ├── deployments.py  # Deployment operations
│   ├── api_keys.py     # API key management
│   ├── tts.py          # TTS generation
│   └── usage.py        # Analytics
├── models.py           # Pydantic models
├── exceptions.py       # Custom exceptions
└── utils.py            # Helpers
```

**Acceptance Criteria:**
- Published to PyPI
- Type hints throughout
- Async support (voiceflow[async])
- Comprehensive error handling
- 90%+ test coverage
- Documentation in README

---

### Issue #24: Node.js SDK
**Priority:** P2 - Medium
**Effort:** 4 days
**Labels:** `sdk`, `nodejs`

**Description:**
Official Node.js SDK for VoiceFlow API.

**Usage:**
```typescript
import VoiceFlow from 'voiceflow';

const client = new VoiceFlow({ apiKey: 'vf_live_xxx' });

// Deploy a TTS server
const deployment = await client.deployments.create({
  name: 'my-tts-server',
  gpuType: 'A100-40GB',
  deploymentType: 'serverless'
});

console.log(`Deployed: ${deployment.endpoint}`);

// Generate speech
const audio = await client.tts.generate({
  text: 'Hello world!',
  voice: 'alloy',
  deploymentId: deployment.id
});
await audio.save('output.wav');

// Stream audio
const stream = await client.tts.stream({
  text: 'Hello world!',
  voice: 'alloy'
});
stream.pipe(fs.createWriteStream('output.wav'));
```

**Acceptance Criteria:**
- Published to npm
- TypeScript definitions
- ESM and CommonJS support
- Streaming support
- Browser compatible (for non-Node features)
- Comprehensive error handling

---

### Issue #25: CLI Tool
**Priority:** P3 - Low
**Effort:** 3 days
**Labels:** `sdk`, `cli`

**Description:**
Command-line tool for VoiceFlow.

**Commands:**
```bash
# Authentication
voiceflow login
voiceflow logout
voiceflow whoami

# Deployments
voiceflow deploy create --name my-server --gpu A100-40GB
voiceflow deploy list
voiceflow deploy logs my-server
voiceflow deploy stop my-server

# TTS Generation
voiceflow tts "Hello world" --voice alloy --output hello.wav
voiceflow tts --file input.txt --voice nova --output speech.wav

# API Keys
voiceflow keys create --name "Production"
voiceflow keys list
voiceflow keys revoke key_xxx

# Usage
voiceflow usage
voiceflow usage --month 2026-01
```

**Implementation:**
```python
# cli.py
import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
@click.option('--api-key', envvar='VOICEFLOW_API_KEY')
@click.pass_context
def cli(ctx, api_key):
    ctx.obj = VoiceFlow(api_key=api_key)

@cli.group()
def deploy():
    """Manage deployments"""
    pass

@deploy.command('list')
@click.pass_obj
def deploy_list(client):
    """List all deployments"""
    deployments = client.deployments.list()

    table = Table(title="Deployments")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("GPU")
    table.add_column("Endpoint")

    for d in deployments:
        table.add_row(d.name, d.status, d.gpu_type, d.endpoint)

    console.print(table)

@cli.command()
@click.argument('text')
@click.option('--voice', default='alloy')
@click.option('--output', '-o', default='output.wav')
@click.pass_obj
def tts(client, text, voice, output):
    """Generate speech from text"""
    with console.status("Generating..."):
        audio = client.tts.generate(text=text, voice=voice)
        audio.save(output)
    console.print(f"[green]Saved to {output}[/green]")
```

**Acceptance Criteria:**
- Published to PyPI (voiceflow-cli)
- Colorful output with Rich
- Config file support (~/.voiceflow/config)
- Shell completion (bash, zsh, fish)

---

## Milestone 6: Polish & Launch (Week 11-12)
*Final touches before public launch*

### Issue #26: Landing Page
**Priority:** P1 - High
**Effort:** 3 days
**Labels:** `frontend`, `marketing`

**Description:**
Create marketing landing page for VoiceFlow.

**Sections:**
1. Hero - Value proposition, CTA
2. Features - Key capabilities
3. Pricing - Plan comparison
4. Demo - Interactive TTS demo
5. Testimonials - Customer quotes
6. FAQ - Common questions
7. Footer - Links, legal

**Design Requirements:**
- Mobile-first responsive
- Fast (< 2s load time)
- SEO optimized
- Analytics integrated (Plausible/Fathom)

---

### Issue #27: Onboarding Flow
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `frontend`, `ux`

**Description:**
Guide new users through first deployment.

**Steps:**
1. Welcome + account setup
2. Create first API key
3. Deploy first TTS server
4. Make first API call
5. Celebrate success!

**Implementation:**
```javascript
const onboardingSteps = [
  {
    id: 'welcome',
    title: 'Welcome to VoiceFlow',
    description: 'Let\'s get you set up in 2 minutes',
    action: null
  },
  {
    id: 'api-key',
    title: 'Create Your API Key',
    description: 'You\'ll need this to authenticate requests',
    action: () => showAPIKeyModal()
  },
  {
    id: 'deploy',
    title: 'Deploy Your First Server',
    description: 'Choose a GPU and deploy a TTS server',
    action: () => navigateTo('/deploy')
  },
  {
    id: 'test',
    title: 'Make Your First Request',
    description: 'Try the API with cURL or our playground',
    action: () => showPlayground()
  },
  {
    id: 'complete',
    title: 'You\'re All Set!',
    description: 'Start building amazing voice experiences',
    confetti: true
  }
];
```

**Acceptance Criteria:**
- New users see onboarding automatically
- Progress saved (can continue later)
- Skip option available
- Completion tracked in analytics

---

### Issue #28: Email Templates
**Priority:** P2 - Medium
**Effort:** 2 days
**Labels:** `backend`, `email`

**Description:**
Design and implement transactional emails.

**Templates:**
| Template | Trigger |
|----------|---------|
| Welcome | Registration |
| Email Verification | Registration |
| Password Reset | Forgot password |
| Deployment Started | New deployment |
| Deployment Failed | Deployment error |
| Usage Alert | 80% of limit |
| Invoice | Monthly billing |
| Payout (Contributors) | Payment sent |

**Implementation:**
```python
# emails.py
from jinja2 import Environment, FileSystemLoader
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

env = Environment(loader=FileSystemLoader('templates/emails'))

async def send_welcome_email(user: User):
    template = env.get_template('welcome.html')
    html = template.render(name=user.name)

    resend.Emails.send({
        "from": "VoiceFlow <hello@voiceflow.ai>",
        "to": user.email,
        "subject": "Welcome to VoiceFlow!",
        "html": html
    })

async def send_usage_alert(user: User, usage_percent: int):
    template = env.get_template('usage_alert.html')
    html = template.render(
        name=user.name,
        usage_percent=usage_percent,
        upgrade_url="https://console.voiceflow.ai/billing"
    )

    resend.Emails.send({
        "from": "VoiceFlow <alerts@voiceflow.ai>",
        "to": user.email,
        "subject": f"You've used {usage_percent}% of your plan",
        "html": html
    })
```

**Acceptance Criteria:**
- All templates styled consistently
- Unsubscribe link in marketing emails
- Plain text fallback
- Preview in browser during development

---

### Issue #29: Security Audit
**Priority:** P0 - Critical
**Effort:** 3 days
**Labels:** `security`

**Description:**
Comprehensive security review before launch.

**Checklist:**
- [ ] Authentication flows secure
- [ ] JWT implementation correct
- [ ] API keys properly hashed
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] CSRF protection
- [ ] Rate limiting working
- [ ] CORS properly configured
- [ ] Secrets not in code/logs
- [ ] HTTPS enforced
- [ ] Security headers set
- [ ] Dependencies audited (npm audit, pip-audit)
- [ ] Penetration testing passed

**Tools:**
- OWASP ZAP for automated scanning
- Manual review of auth flows
- Dependency scanning with Snyk

---

### Issue #30: Load Testing
**Priority:** P1 - High
**Effort:** 2 days
**Labels:** `testing`, `performance`

**Description:**
Verify system handles expected load.

**Targets:**
- 1000 concurrent users
- 100 requests/second
- P95 latency < 500ms
- Zero errors under normal load

**Implementation:**
```python
# locustfile.py
from locust import HttpUser, task, between

class VoiceFlowUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login and get token
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def get_deployments(self):
        self.client.get("/api/deployments", headers=self.headers)

    @task(5)
    def get_stats(self):
        self.client.get("/api/stats", headers=self.headers)

    @task(2)
    def get_usage(self):
        self.client.get("/api/usage", headers=self.headers)

    @task(1)
    def create_api_key(self):
        self.client.post("/api/keys/generate",
            headers=self.headers,
            json={"name": "Load Test Key"}
        )
```

**Acceptance Criteria:**
- System handles 1000 concurrent users
- No errors under normal load
- Graceful degradation under overload
- Bottlenecks identified and documented

---

## Additional Issues (Backlog)

### Issue #31: OAuth2 Providers (Google, GitHub)
**Priority:** P3
**Effort:** 3 days

### Issue #32: Two-Factor Authentication
**Priority:** P2
**Effort:** 3 days

### Issue #33: Team Invitations via Email
**Priority:** P2
**Effort:** 2 days

### Issue #34: Deployment Templates
**Priority:** P3
**Effort:** 2 days

### Issue #35: Custom Domains for Endpoints
**Priority:** P3
**Effort:** 3 days

### Issue #36: Webhook Signature Verification
**Priority:** P2
**Effort:** 1 day

### Issue #37: API Versioning
**Priority:** P2
**Effort:** 2 days

### Issue #38: Request Signing for Enterprise
**Priority:** P3
**Effort:** 3 days

### Issue #39: Audit Log UI
**Priority:** P2
**Effort:** 2 days

### Issue #40: Dark Mode
**Priority:** P3
**Effort:** 1 day

### Issue #41: Keyboard Shortcuts
**Priority:** P3
**Effort:** 1 day

### Issue #42: Real-time WebSocket Updates
**Priority:** P2
**Effort:** 3 days

### Issue #43: Voice Cloning Feature
**Priority:** P2
**Effort:** 5 days

### Issue #44: Multi-language TTS Support
**Priority:** P2
**Effort:** 3 days

### Issue #45: Custom Voice Training
**Priority:** P3
**Effort:** 10 days

### Issue #46: API Playground in Docs
**Priority:** P2
**Effort:** 2 days

### Issue #47: Status Page
**Priority:** P2
**Effort:** 2 days

### Issue #48: Mobile App (React Native)
**Priority:** P4
**Effort:** 20 days

### Issue #49: White-label Solution
**Priority:** P4
**Effort:** 15 days

### Issue #50: SOC2 Compliance
**Priority:** P3
**Effort:** 30 days

---

## Priority Legend

| Priority | Meaning | Timeline |
|----------|---------|----------|
| P0 | Critical blocker | This week |
| P1 | High priority | Next 2 weeks |
| P2 | Medium priority | This month |
| P3 | Low priority | This quarter |
| P4 | Nice to have | Someday |

---

## Effort Legend

| Effort | Meaning |
|--------|---------|
| 0.5 days | Few hours |
| 1 day | Full day |
| 2 days | 2 days |
| 3 days | Half week |
| 5 days | Full week |
| 10+ days | Multi-week project |

---

## Milestone Summary

| Milestone | Issues | Effort | Focus |
|-----------|--------|--------|-------|
| M1: Foundation | #1-8 | 2 weeks | Auth, DB, Security |
| M2: Billing | #9-11 | 1.5 weeks | Stripe, Metering |
| M3: Voice Collection | #12-16 | 2 weeks | Recording, Payouts |
| M4: Infrastructure | #17-21 | 1.5 weeks | Monitoring, CI/CD |
| M5: Documentation | #22-25 | 2 weeks | Docs, SDKs |
| M6: Launch | #26-30 | 1.5 weeks | Polish, Testing |

**Total Estimated Effort:** 10-12 weeks with 2-3 engineers

---

*Document maintained by the VoiceFlow team*
*Last updated: January 20, 2026*
