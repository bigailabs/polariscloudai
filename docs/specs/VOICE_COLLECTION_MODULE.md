# Voice Collection Module - Technical Specification

## Executive Summary

The Voice Collection Module enables VoiceFlow to ethically collect diverse voice data from paid contributors, building a unique dataset to improve TTS quality and offer a voice marketplace. This document provides detailed specifications for implementation.

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Voice Collection Platform                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  Contributor │    │   Recording  │    │   Quality    │           │
│  │    Portal    │───▶│   Service    │───▶│   Pipeline   │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│         │                   │                   │                     │
│         ▼                   ▼                   ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │    Auth &    │    │    Audio     │    │   ML/AI      │           │
│  │   Consent    │    │   Storage    │    │   Services   │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│         │                   │                   │                     │
│         └───────────────────┼───────────────────┘                     │
│                             ▼                                         │
│                    ┌──────────────┐                                   │
│                    │   Database   │                                   │
│                    │  (PostgreSQL)│                                   │
│                    └──────────────┘                                   │
│                             │                                         │
│         ┌───────────────────┼───────────────────┐                     │
│         ▼                   ▼                   ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │   Payment    │    │   Analytics  │    │    Admin     │           │
│  │   Service    │    │   Service    │    │   Dashboard  │           │
│  │   (Stripe)   │    │              │    │              │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Breakdown

| Component | Technology | Purpose |
|-----------|------------|---------|
| Contributor Portal | React/Next.js | Web interface for contributors |
| Recording Service | FastAPI + WebSockets | Audio capture and upload |
| Quality Pipeline | Python + ML models | Audio analysis and scoring |
| Auth & Consent | Auth0 + Custom | Identity and legal consent |
| Audio Storage | AWS S3 + CloudFront | Secure audio file storage |
| ML/AI Services | PyTorch + FastAPI | Speaker verification, quality scoring |
| Database | PostgreSQL | Metadata and user data |
| Payment Service | Stripe Connect | Contributor payments |
| Analytics | ClickHouse | Usage and diversity analytics |
| Admin Dashboard | React + Tailwind | Internal management |

---

## 2. Data Models

### 2.1 Core Entities

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import uuid

class ContributorStatus(Enum):
    PENDING = "pending"           # Signed up, not verified
    CALIBRATING = "calibrating"   # Recording calibration samples
    ACTIVE = "active"             # Approved, can record
    SUSPENDED = "suspended"       # Temporarily disabled
    BANNED = "banned"             # Permanently removed

class ConsentType(Enum):
    TTS_TRAINING = "tts_training"         # Voice used for training
    VOICE_CLONING = "voice_cloning"       # Voice can be cloned
    MARKETPLACE = "marketplace"           # Voice sold in marketplace
    COMMERCIAL = "commercial"             # Full commercial rights

class RecordingStatus(Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    QUALITY_CHECK = "quality_check"
    HUMAN_REVIEW = "human_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class Contributor(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID              # Link to auth system
    email: str
    name: str
    status: ContributorStatus

    # Profile
    display_name: Optional[str]
    bio: Optional[str]
    profile_image_url: Optional[str]

    # Voice characteristics
    native_language: str
    additional_languages: List[str]
    accent: Optional[str]
    gender: Optional[str]           # Self-reported
    age_range: Optional[str]        # "18-25", "26-35", etc.

    # Consent
    consents: List[ConsentType]
    consent_version: str            # Version of terms accepted
    consent_date: datetime

    # Payment
    stripe_account_id: Optional[str]
    payment_method: Optional[str]
    tax_info_submitted: bool

    # Stats
    total_recordings: int
    approved_recordings: int
    total_earnings: float
    average_quality_score: float

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime


class Script(BaseModel):
    id: uuid.UUID
    title: str
    category: str                   # "general", "news", "conversation", etc.
    language: str
    text: str
    estimated_duration_seconds: int
    difficulty: str                 # "easy", "medium", "hard"
    tags: List[str]

    # Metadata
    phoneme_coverage: float         # % of language phonemes covered
    word_count: int
    unique_words: int

    # Status
    active: bool
    times_recorded: int


class Recording(BaseModel):
    id: uuid.UUID
    contributor_id: uuid.UUID
    script_id: uuid.UUID
    session_id: uuid.UUID           # Recording session

    # Audio
    audio_url: str                  # S3 URL
    audio_format: str               # "wav"
    sample_rate: int                # 44100
    duration_seconds: float
    file_size_bytes: int

    # Quality metrics
    status: RecordingStatus
    quality_score: Optional[float]  # 0-100
    snr_db: Optional[float]         # Signal-to-noise ratio
    clipping_detected: bool
    background_noise_level: Optional[float]

    # Transcription
    transcription: Optional[str]
    word_error_rate: Optional[float]

    # Speaker verification
    speaker_verified: bool
    speaker_confidence: Optional[float]

    # Review
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]

    # Payment
    compensation_amount: Optional[float]
    compensation_status: str        # "pending", "approved", "paid"

    # Timestamps
    created_at: datetime
    processed_at: Optional[datetime]


class RecordingSession(BaseModel):
    id: uuid.UUID
    contributor_id: uuid.UUID
    device_info: dict               # Browser, OS, mic info
    started_at: datetime
    ended_at: Optional[datetime]
    recordings_count: int
    total_duration_seconds: float


class Payment(BaseModel):
    id: uuid.UUID
    contributor_id: uuid.UUID
    amount: float
    currency: str                   # "USD"
    status: str                     # "pending", "processing", "completed", "failed"
    stripe_transfer_id: Optional[str]
    period_start: datetime
    period_end: datetime
    recordings_count: int
    created_at: datetime
    completed_at: Optional[datetime]


class VoiceProfile(BaseModel):
    """Derived profile for a contributor's voice characteristics"""
    id: uuid.UUID
    contributor_id: uuid.UUID

    # Audio fingerprint
    embedding_vector: List[float]   # Speaker embedding (d-vector)
    embedding_model: str            # Model used to generate embedding

    # Characteristics
    pitch_mean: float
    pitch_std: float
    speaking_rate_wpm: float
    energy_mean: float

    # Calibration
    calibration_recordings: List[uuid.UUID]
    calibration_score: float
    calibration_date: datetime

    # Marketplace
    marketplace_enabled: bool
    marketplace_price: Optional[float]
    marketplace_downloads: int
```

### 2.2 Database Schema (PostgreSQL)

```sql
-- Contributors
CREATE TABLE contributors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',

    -- Profile
    display_name VARCHAR(255),
    bio TEXT,
    profile_image_url VARCHAR(500),

    -- Voice info
    native_language VARCHAR(50) NOT NULL,
    additional_languages JSONB DEFAULT '[]',
    accent VARCHAR(100),
    gender VARCHAR(50),
    age_range VARCHAR(20),

    -- Payment
    stripe_account_id VARCHAR(255),
    payment_method VARCHAR(50),
    tax_info_submitted BOOLEAN DEFAULT FALSE,

    -- Stats (denormalized for performance)
    total_recordings INTEGER DEFAULT 0,
    approved_recordings INTEGER DEFAULT 0,
    total_earnings DECIMAL(12,2) DEFAULT 0,
    average_quality_score DECIMAL(5,2),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP

    CONSTRAINT unique_contributor_user UNIQUE (user_id)
);

-- Consents
CREATE TABLE contributor_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID NOT NULL REFERENCES contributors(id),
    consent_type VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP,
    consent_version VARCHAR(20) NOT NULL,
    ip_address INET,
    user_agent TEXT,

    CONSTRAINT unique_consent UNIQUE (contributor_id, consent_type)
);

-- Scripts
CREATE TABLE scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    language VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    estimated_duration_seconds INTEGER,
    difficulty VARCHAR(20) DEFAULT 'medium',
    tags JSONB DEFAULT '[]',

    -- Coverage metrics
    phoneme_coverage DECIMAL(5,2),
    word_count INTEGER,
    unique_words INTEGER,

    -- Status
    active BOOLEAN DEFAULT TRUE,
    times_recorded INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Recordings
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID NOT NULL REFERENCES contributors(id),
    script_id UUID NOT NULL REFERENCES scripts(id),
    session_id UUID NOT NULL,

    -- Audio
    audio_url VARCHAR(500) NOT NULL,
    audio_format VARCHAR(20) DEFAULT 'wav',
    sample_rate INTEGER DEFAULT 44100,
    duration_seconds DECIMAL(10,3),
    file_size_bytes BIGINT,

    -- Quality
    status VARCHAR(50) DEFAULT 'uploaded',
    quality_score DECIMAL(5,2),
    snr_db DECIMAL(6,2),
    clipping_detected BOOLEAN DEFAULT FALSE,
    background_noise_level DECIMAL(6,2),

    -- Transcription
    transcription TEXT,
    word_error_rate DECIMAL(5,4),

    -- Speaker verification
    speaker_verified BOOLEAN DEFAULT FALSE,
    speaker_confidence DECIMAL(5,4),

    -- Review
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,

    -- Payment
    compensation_amount DECIMAL(10,4),
    compensation_status VARCHAR(50) DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_recordings_contributor ON recordings(contributor_id),
    INDEX idx_recordings_status ON recordings(status),
    INDEX idx_recordings_created ON recordings(created_at)
);

-- Recording sessions
CREATE TABLE recording_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID NOT NULL REFERENCES contributors(id),
    device_info JSONB,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    recordings_count INTEGER DEFAULT 0,
    total_duration_seconds DECIMAL(10,2) DEFAULT 0
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID NOT NULL REFERENCES contributors(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',
    stripe_transfer_id VARCHAR(255),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    recordings_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    INDEX idx_payments_contributor ON payments(contributor_id),
    INDEX idx_payments_status ON payments(status)
);

-- Voice profiles
CREATE TABLE voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_id UUID NOT NULL REFERENCES contributors(id),

    -- Embedding
    embedding_vector VECTOR(256),  -- Using pgvector extension
    embedding_model VARCHAR(100),

    -- Characteristics
    pitch_mean DECIMAL(6,2),
    pitch_std DECIMAL(6,2),
    speaking_rate_wpm DECIMAL(6,2),
    energy_mean DECIMAL(6,2),

    -- Calibration
    calibration_recordings JSONB DEFAULT '[]',
    calibration_score DECIMAL(5,2),
    calibration_date TIMESTAMP,

    -- Marketplace
    marketplace_enabled BOOLEAN DEFAULT FALSE,
    marketplace_price DECIMAL(10,2),
    marketplace_downloads INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_voice_profile UNIQUE (contributor_id)
);

-- Diversity tracking (aggregated, anonymized)
CREATE TABLE diversity_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    dimension VARCHAR(50) NOT NULL,  -- 'gender', 'age', 'language', 'accent'
    value VARCHAR(100) NOT NULL,
    contributor_count INTEGER,
    recording_count INTEGER,
    recording_hours DECIMAL(10,2),

    UNIQUE (metric_date, dimension, value)
);
```

---

## 3. API Endpoints

### 3.1 Contributor Management

```yaml
# Registration and Onboarding
POST   /api/v1/contributors/register
  Request:
    email: string
    name: string
    native_language: string
    consent_to_terms: boolean
  Response:
    contributor_id: uuid
    status: "pending"
    next_step: "verify_email"

POST   /api/v1/contributors/verify-email
  Request:
    token: string
  Response:
    verified: boolean

POST   /api/v1/contributors/profile
  Request:
    display_name: string
    bio: string
    additional_languages: string[]
    accent: string
    gender: string  # optional
    age_range: string  # optional
  Response:
    profile: ContributorProfile

POST   /api/v1/contributors/consent
  Request:
    consent_types: ConsentType[]
  Response:
    consents_granted: ConsentType[]
    consent_document_url: string

GET    /api/v1/contributors/me
  Response:
    contributor: Contributor

PUT    /api/v1/contributors/me
  Request:
    display_name?: string
    bio?: string
    # ... other updatable fields
  Response:
    contributor: Contributor

DELETE /api/v1/contributors/me
  # Account deletion with data export
  Response:
    deletion_scheduled: datetime
    data_export_url: string
```

### 3.2 Recording

```yaml
# Script Management
GET    /api/v1/scripts
  Query:
    language: string
    category: string
    difficulty: string
    limit: int (default 10)
  Response:
    scripts: Script[]
    total: int

GET    /api/v1/scripts/{id}
  Response:
    script: Script

GET    /api/v1/scripts/next
  # Get next recommended script for contributor
  Response:
    script: Script
    reason: string  # "completes phoneme coverage", "matches your profile"

# Recording Sessions
POST   /api/v1/sessions/start
  Request:
    device_info: {
      browser: string
      os: string
      microphone: string
    }
  Response:
    session_id: uuid
    expires_at: datetime

POST   /api/v1/sessions/{id}/end
  Response:
    session: RecordingSession

# Recording Upload
POST   /api/v1/recordings
  Content-Type: multipart/form-data
  Request:
    session_id: uuid
    script_id: uuid
    audio: File (WAV)
  Response:
    recording_id: uuid
    status: "uploaded"
    quality_check_eta: int (seconds)

GET    /api/v1/recordings/{id}
  Response:
    recording: Recording

GET    /api/v1/recordings/{id}/status
  Response:
    status: RecordingStatus
    quality_score?: float
    issues?: string[]

GET    /api/v1/recordings
  Query:
    status: RecordingStatus
    limit: int
    offset: int
  Response:
    recordings: Recording[]
    total: int

DELETE /api/v1/recordings/{id}
  # Delete before approval
  Response:
    deleted: boolean
```

### 3.3 Quality Pipeline

```yaml
# Internal endpoints for quality processing

POST   /api/v1/internal/quality/analyze
  Request:
    recording_id: uuid
  Response:
    job_id: uuid

GET    /api/v1/internal/quality/jobs/{id}
  Response:
    status: "pending" | "processing" | "completed" | "failed"
    result?: QualityResult

# Human review queue
GET    /api/v1/internal/review/queue
  Query:
    limit: int
  Response:
    recordings: Recording[]

POST   /api/v1/internal/review/{recording_id}/approve
  Response:
    recording: Recording

POST   /api/v1/internal/review/{recording_id}/reject
  Request:
    reason: string
  Response:
    recording: Recording
```

### 3.4 Payments

```yaml
# Stripe Connect onboarding
POST   /api/v1/payments/connect/start
  Response:
    onboarding_url: string
    expires_at: datetime

GET    /api/v1/payments/connect/status
  Response:
    connected: boolean
    account_status: string
    payouts_enabled: boolean

# Earnings
GET    /api/v1/payments/earnings
  Query:
    period: "week" | "month" | "year" | "all"
  Response:
    total_earned: float
    pending: float
    available: float
    breakdown: {
      recordings_approved: int
      base_compensation: float
      bonuses: float
    }

GET    /api/v1/payments/history
  Query:
    limit: int
    offset: int
  Response:
    payments: Payment[]
    total: int

POST   /api/v1/payments/request-payout
  # Manual payout request (if above threshold)
  Response:
    payout_id: uuid
    amount: float
    estimated_arrival: date
```

### 3.5 Analytics (Contributor Dashboard)

```yaml
GET    /api/v1/analytics/dashboard
  Response:
    recordings_this_week: int
    earnings_this_week: float
    average_quality_score: float
    quality_trend: float[]  # Last 7 days
    next_milestone: {
      type: string
      current: int
      target: int
      reward: float
    }

GET    /api/v1/analytics/recordings
  Query:
    period: "week" | "month" | "year"
  Response:
    daily_counts: { date: string, count: int }[]
    status_breakdown: { status: string, count: int }[]
```

---

## 4. Quality Assessment Pipeline

### 4.1 Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Quality Assessment Pipeline                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Stage 1: Format Validation                                          │
│  ├── File format check (WAV, 44.1kHz, 16-bit)                       │
│  ├── Duration check (2-30 seconds)                                   │
│  └── File integrity                                                  │
│                                                                       │
│  Stage 2: Audio Quality Analysis                                     │
│  ├── Signal-to-Noise Ratio (SNR)                                    │
│  │   └── Threshold: > 20 dB                                         │
│  ├── Clipping Detection                                              │
│  │   └── Threshold: < 0.1% samples                                  │
│  ├── Background Noise Analysis                                       │
│  │   └── Threshold: < -40 dB during silence                         │
│  └── Volume Normalization Check                                      │
│      └── Range: -30 dB to -6 dB RMS                                 │
│                                                                       │
│  Stage 3: Speech Analysis                                            │
│  ├── Speech Detection (VAD)                                          │
│  │   └── Threshold: > 80% speech content                            │
│  ├── Transcription (Whisper)                                         │
│  └── Word Error Rate (WER)                                           │
│      └── Threshold: < 10%                                            │
│                                                                       │
│  Stage 4: Speaker Verification                                       │
│  ├── Extract speaker embedding                                       │
│  ├── Compare to calibration embeddings                               │
│  └── Confidence threshold: > 0.85                                    │
│                                                                       │
│  Stage 5: Quality Scoring                                            │
│  ├── Weighted score calculation                                      │
│  ├── Auto-approve threshold: > 80                                    │
│  ├── Human review threshold: 60-80                                   │
│  └── Auto-reject threshold: < 60                                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Quality Score Calculation

```python
def calculate_quality_score(analysis: dict) -> float:
    """
    Calculate overall quality score (0-100)

    Weights:
    - Audio quality: 30%
    - Transcription accuracy: 30%
    - Speaker verification: 20%
    - Completeness: 20%
    """
    weights = {
        'audio_quality': 0.30,
        'transcription_accuracy': 0.30,
        'speaker_verification': 0.20,
        'completeness': 0.20
    }

    # Audio quality score (0-100)
    # Based on SNR, clipping, noise floor
    audio_score = 0
    if analysis['snr_db'] >= 30:
        audio_score += 40
    elif analysis['snr_db'] >= 20:
        audio_score += 30
    elif analysis['snr_db'] >= 15:
        audio_score += 20

    if not analysis['clipping_detected']:
        audio_score += 30

    if analysis['background_noise_db'] < -50:
        audio_score += 30
    elif analysis['background_noise_db'] < -40:
        audio_score += 20

    # Transcription accuracy (0-100)
    wer = analysis['word_error_rate']
    transcription_score = max(0, 100 - (wer * 500))  # 0.1 WER = 50 score

    # Speaker verification (0-100)
    speaker_score = analysis['speaker_confidence'] * 100

    # Completeness (0-100)
    # All words spoken, correct duration
    completeness_score = 100
    if wer > 0.05:
        completeness_score -= (wer - 0.05) * 200
    if analysis['duration_ratio'] < 0.9 or analysis['duration_ratio'] > 1.3:
        completeness_score -= 20

    # Weighted total
    total = (
        audio_score * weights['audio_quality'] +
        transcription_score * weights['transcription_accuracy'] +
        speaker_score * weights['speaker_verification'] +
        max(0, completeness_score) * weights['completeness']
    )

    return round(total, 2)


# Thresholds
AUTO_APPROVE_THRESHOLD = 80
HUMAN_REVIEW_THRESHOLD = 60
AUTO_REJECT_THRESHOLD = 60
```

### 4.3 ML Models Used

| Model | Purpose | Implementation |
|-------|---------|----------------|
| Silero VAD | Voice Activity Detection | `silero-vad` |
| Whisper | Transcription | `openai-whisper` or `faster-whisper` |
| ECAPA-TDNN | Speaker Embedding | `speechbrain` |
| Resemblyzer | Speaker Verification | `resemblyzer` |
| Custom CNN | Audio Quality Classification | PyTorch (trained on internal data) |

---

## 5. Compensation System

### 5.1 Compensation Model

```yaml
Base Rates:
  standard_recording: $0.10        # 5-15 second recording
  long_recording: $0.20            # 15-30 second recording

Quality Bonuses:
  excellent_quality: +25%          # Score > 95
  high_quality: +10%               # Score 85-95

Language Bonuses:
  rare_language: +50%              # Languages with < 1000 hours data
  endangered_language: +100%       # UNESCO endangered languages

Demographic Bonuses:
  underrepresented_group: +25%     # Based on diversity metrics

Completion Bonuses:
  script_set_complete: $5.00       # Complete all scripts in a category
  weekly_goal_met: $10.00          # 100+ approved recordings in week
  monthly_milestone: $25.00        # 500+ approved recordings in month

Referral Program:
  referrer_bonus: $10.00           # When referee reaches 50 recordings
  referee_bonus: $5.00             # After 50 approved recordings

Minimums:
  minimum_payout: $25.00
  payout_frequency: weekly         # If threshold met
```

### 5.2 Payment Processing

```python
async def process_weekly_payments():
    """
    Run weekly to process contributor payments
    """
    # Get all contributors with unpaid approved recordings
    contributors = await db.get_contributors_with_pending_earnings(
        min_amount=25.00  # Minimum payout threshold
    )

    for contributor in contributors:
        # Calculate earnings
        recordings = await db.get_approved_recordings(
            contributor_id=contributor.id,
            compensation_status='pending'
        )

        total_earnings = sum(r.compensation_amount for r in recordings)

        if total_earnings < 25.00:
            continue  # Below threshold

        # Create Stripe transfer
        try:
            transfer = stripe.Transfer.create(
                amount=int(total_earnings * 100),  # cents
                currency='usd',
                destination=contributor.stripe_account_id,
                description=f"VoiceFlow earnings - Week of {date.today()}",
                metadata={
                    'contributor_id': str(contributor.id),
                    'recordings_count': len(recordings),
                    'period': f"{week_start} to {week_end}"
                }
            )

            # Record payment
            payment = await db.create_payment(
                contributor_id=contributor.id,
                amount=total_earnings,
                stripe_transfer_id=transfer.id,
                recordings_count=len(recordings)
            )

            # Update recordings
            await db.mark_recordings_paid(
                recording_ids=[r.id for r in recordings],
                payment_id=payment.id
            )

            # Send notification
            await notifications.send_payment_notification(
                contributor_id=contributor.id,
                amount=total_earnings,
                payment_id=payment.id
            )

        except stripe.error.StripeError as e:
            logger.error(f"Payment failed for {contributor.id}: {e}")
            await db.record_payment_failure(
                contributor_id=contributor.id,
                error=str(e)
            )
```

---

## 6. Frontend Specifications

### 6.1 Contributor Portal Pages

```
/contribute
├── /                       # Landing page
├── /signup                 # Registration
├── /verify                 # Email verification
├── /onboarding
│   ├── /profile           # Profile setup
│   ├── /consent           # Legal agreements
│   ├── /payment           # Stripe Connect setup
│   └── /calibration       # Voice calibration
├── /dashboard             # Main dashboard
├── /record
│   ├── /                  # Script selection
│   └── /{script_id}       # Recording interface
├── /recordings            # Recording history
├── /earnings              # Earnings dashboard
├── /settings
│   ├── /profile           # Profile settings
│   ├── /payment           # Payment settings
│   ├── /consent           # Manage consents
│   └── /account           # Account settings
└── /help                  # Help center
```

### 6.2 Recording Interface Component

```tsx
// components/VoiceRecorder.tsx

interface VoiceRecorderProps {
  script: Script;
  onRecordingComplete: (blob: Blob) => void;
}

const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ script, onRecordingComplete }) => {
  const [status, setStatus] = useState<'idle' | 'recording' | 'reviewing'>('idle');
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetrics | null>(null);

  // Real-time audio analysis
  const analyzeAudio = useCallback((analyser: AnalyserNode) => {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);

    // Calculate volume level
    const volume = dataArray.reduce((a, b) => a + b) / dataArray.length;

    // Detect clipping
    const clipping = dataArray.some(v => v > 250);

    // Estimate background noise (during silence)
    const noiseFloor = /* calculate from low-energy frames */;

    setQualityMetrics({
      volume,
      clipping,
      noiseFloor,
      duration: /* current duration */
    });
  }, []);

  return (
    <div className="voice-recorder">
      {/* Script display */}
      <ScriptReader
        text={script.text}
        highlightPosition={/* sync with recording */}
      />

      {/* Audio waveform */}
      <AudioWaveform
        audioContext={audioContext}
        isRecording={status === 'recording'}
      />

      {/* Quality indicators */}
      <QualityIndicators metrics={qualityMetrics} />

      {/* Controls */}
      <RecordingControls
        status={status}
        onStart={startRecording}
        onStop={stopRecording}
        onRetry={retryRecording}
        onSubmit={() => onRecordingComplete(audioBlob!)}
      />

      {/* Review panel */}
      {status === 'reviewing' && (
        <ReviewPanel
          audioBlob={audioBlob}
          qualityMetrics={qualityMetrics}
          onAccept={() => onRecordingComplete(audioBlob!)}
          onRetry={retryRecording}
        />
      )}
    </div>
  );
};
```

### 6.3 Quality Indicator Component

```tsx
// components/QualityIndicators.tsx

interface QualityIndicatorsProps {
  metrics: {
    volume: number;      // 0-100
    noiseLevel: number;  // dB
    clipping: boolean;
    duration: number;    // seconds
  };
  thresholds: {
    minVolume: number;
    maxVolume: number;
    maxNoise: number;
    minDuration: number;
    maxDuration: number;
  };
}

const QualityIndicators: React.FC<QualityIndicatorsProps> = ({ metrics, thresholds }) => {
  const getVolumeStatus = () => {
    if (metrics.volume < thresholds.minVolume) return 'too-quiet';
    if (metrics.volume > thresholds.maxVolume) return 'too-loud';
    return 'good';
  };

  return (
    <div className="quality-indicators">
      {/* Volume meter */}
      <div className="indicator volume">
        <label>Volume</label>
        <div className={`meter ${getVolumeStatus()}`}>
          <div className="bar" style={{ width: `${metrics.volume}%` }} />
        </div>
        {metrics.clipping && <span className="warning">Clipping detected!</span>}
      </div>

      {/* Noise level */}
      <div className="indicator noise">
        <label>Background Noise</label>
        <div className={`status ${metrics.noiseLevel < thresholds.maxNoise ? 'good' : 'bad'}`}>
          {metrics.noiseLevel < thresholds.maxNoise ? '✓ Quiet' : '⚠ Noisy'}
        </div>
      </div>

      {/* Duration */}
      <div className="indicator duration">
        <label>Duration</label>
        <span>{metrics.duration.toFixed(1)}s</span>
        <span className="range">
          ({thresholds.minDuration}-{thresholds.maxDuration}s)
        </span>
      </div>
    </div>
  );
};
```

---

## 7. Security & Privacy

### 7.1 Data Protection

```yaml
Encryption:
  at_rest: AES-256
  in_transit: TLS 1.3
  audio_files: Encrypted with contributor-specific key

Access Control:
  contributor_data: Only accessible by contributor + admins
  audio_files: Signed URLs with 15-minute expiry
  embeddings: Anonymized, stored separately from PII

Data Retention:
  rejected_recordings: Deleted within 30 days
  approved_recordings: Retained per consent agreement
  contributor_data: Retained until account deletion
  analytics_data: Anonymized after 90 days

Right to Deletion:
  request_processing: Within 30 days
  complete_deletion: Audio files + embeddings
  retained: Anonymized analytics only
```

### 7.2 Consent Management

```yaml
Consent Versioning:
  current_version: "2026-01"
  require_re_consent: On major version change
  grace_period: 30 days to accept new terms

Consent Granularity:
  tts_training:
    description: "Voice used to improve TTS models"
    revocable: Yes (future recordings only)

  voice_cloning:
    description: "Voice may be used for voice cloning features"
    revocable: Yes (removes from cloning dataset)

  marketplace:
    description: "Voice available in public marketplace"
    revocable: Yes (removes from marketplace)

  commercial:
    description: "Full commercial rights granted"
    revocable: No (perpetual license for past recordings)
```

---

## 8. Implementation Phases

### Phase 1: MVP (4 weeks)
- [ ] Contributor registration and profile
- [ ] Basic consent management
- [ ] Web recording interface
- [ ] Manual quality review
- [ ] PayPal payments (before Stripe Connect)

### Phase 2: Automation (4 weeks)
- [ ] Automated quality pipeline
- [ ] Speaker verification
- [ ] Stripe Connect integration
- [ ] Earnings dashboard

### Phase 3: Scale (4 weeks)
- [ ] Mobile recording app (PWA)
- [ ] Batch upload
- [ ] Diversity tracking
- [ ] Advanced analytics

### Phase 4: Marketplace (4 weeks)
- [ ] Voice marketplace listing
- [ ] Voice preview generation
- [ ] Licensing tiers
- [ ] Revenue sharing

---

## 9. Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Active contributors | 1,000 |
| Monthly recordings | 100,000 |
| Total recording hours | 5,000 |
| Average quality score | > 85 |
| Contributor retention (90 day) | > 60% |
| Languages covered | 25 |
| Average contributor earnings | $100/month |
| Auto-approval rate | > 70% |

---

*Specification Version: 1.0*
*Last Updated: January 2026*
