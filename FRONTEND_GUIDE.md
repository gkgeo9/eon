# Fintel Web UI Development Guide

## For Frontend Developers

This document provides everything you need to build a web UI for Fintel. It includes all data models, required backend changes, and complete API specifications.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Current Architecture](#current-architecture)
3. [Required Backend Changes](#required-backend-changes)
4. [Proposed REST API](#proposed-rest-api)
5. [Data Models Reference](#data-models-reference)
6. [User Workflows](#user-workflows)
7. [UI Component Requirements](#ui-component-requirements)
8. [Real-Time Updates](#real-time-updates)
9. [Authentication & Authorization](#authentication--authorization)
10. [Deployment Considerations](#deployment-considerations)

---

## 1. System Overview

### What Fintel Does

Fintel analyzes companies' SEC 10-K filings (annual reports) using AI to provide:

1. **Fundamental Analysis** - Business model, financials, risks, competitive position
2. **Multi-Year Success Factors** - What made successful companies succeed over 10+ years
3. **Multi-Perspective Analysis** - Warren Buffett, Nassim Taleb, and Contrarian investment lenses
4. **Comparative Benchmarking** - Compare companies against top 50 performers (0-100 Compounder DNA score)
5. **Contrarian Scanning** - Find hidden gem opportunities (0-600 Alpha score across 6 dimensions)

### Current State: CLI Only

Users must run Python commands to analyze companies. There's no web interface.

### Goal: User-Friendly Web UI

Enable non-technical users to:
- Upload ticker lists
- Configure analyses
- Monitor progress in real-time
- View results with visualizations
- Export data in multiple formats

---

## 2. Current Architecture

### Technology Stack

**Backend:**
- Python 3.12
- Pydantic for data validation
- Google Gemini AI (GPT alternative)
- SEC Edgar API for data downloads
- Selenium for HTML→PDF conversion
- PyPDF2 for text extraction
- Parallel processing with ProcessPoolExecutor

**Data Storage:**
- JSON files (current)
- Parquet files (columnar format)
- **NO DATABASE** (must be added)

**Configuration:**
- Environment variables (.env file)
- Pydantic Settings

### How It Works Now

```
User runs CLI command
    ↓
Download 10-K HTML from SEC Edgar
    ↓
Convert HTML → PDF (Selenium + Chrome)
    ↓
Extract text from PDF
    ↓
Send to AI with structured prompt
    ↓
Get back validated JSON (Pydantic models)
    ↓
Save results to files
    ↓
User manually opens JSON files to view results
```

**Problems:**
- Must understand CLI commands
- No visibility into progress
- Results hard to interpret (raw JSON)
- Can't compare companies easily
- No tracking of past analyses

---

## 3. Required Backend Changes

### CRITICAL: Add These Before Building Frontend

#### A. Database Layer (PostgreSQL)

**Current:** Results saved to JSON files scattered across directories
**Must Change To:** Relational database for querying and persistence

**Required Tables:**

```sql
-- Core Analysis Results
CREATE TABLE analyses (
    id UUID PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    fiscal_year INTEGER,
    analysis_type VARCHAR(50),  -- fundamental, perspectives, contrarian
    analysis_path VARCHAR(50),  -- excellent, objective
    status VARCHAR(20),  -- queued, processing, completed, failed
    result_json JSONB,  -- Full Pydantic model as JSON
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    created_by VARCHAR(255),
    INDEX idx_ticker (ticker),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Batch Jobs
CREATE TABLE batch_jobs (
    id UUID PRIMARY KEY,
    job_name VARCHAR(255),
    tickers TEXT[],  -- Array of tickers
    analysis_type VARCHAR(50),
    analysis_path VARCHAR(50),
    num_workers INTEGER,
    status VARCHAR(20),  -- queued, processing, paused, completed, failed
    progress_json JSONB,  -- {total, completed, pending, failed}
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- API Key Usage Tracking
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    api_key_hash VARCHAR(64),  -- SHA-256 hash
    date DATE NOT NULL,
    request_count INTEGER DEFAULT 0,
    last_request_at TIMESTAMP,
    UNIQUE(api_key_hash, date)
);

-- Baselines (Top 50 meta-analyses)
CREATE TABLE baselines (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    companies TEXT[],
    meta_analysis_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- User Sessions / Auth
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50),  -- admin, analyst, viewer
    api_key_quota INTEGER DEFAULT 100,  -- Requests per day
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

**Why This Matters:**
- Enable filtering: "Show me all analyses for AAPL with Compounder score > 75"
- Track history: "What analyses did I run last week?"
- User management: "John can run 100 analyses/day"
- Progress monitoring: Real-time batch job status

#### B. Task Queue (Celery or RQ)

**Current:** Blocks while processing (synchronous)
**Must Change To:** Asynchronous task queue

**Why:**
- Analyses take 30+ seconds per company (65s rate limit)
- Batch jobs can run for hours
- Frontend needs immediate response, not blocking

**Implementation:**

```python
# NEW: tasks.py
from celery import Celery

celery = Celery('fintel', broker='redis://localhost:6379')

@celery.task(bind=True)
def analyze_company_task(self, ticker, analysis_type, analysis_path, user_id):
    """Background task for single company analysis."""
    try:
        # Update status: processing
        update_analysis_status(self.request.id, 'processing')

        # Run analysis (existing code)
        result = run_fintel_analysis(ticker, analysis_type, analysis_path)

        # Save to database
        save_analysis_to_db(ticker, result, user_id)

        # Update status: completed
        update_analysis_status(self.request.id, 'completed')

        return {"status": "success", "ticker": ticker}
    except Exception as e:
        update_analysis_status(self.request.id, 'failed', error=str(e))
        raise

@celery.task(bind=True)
def batch_analysis_task(self, job_id, tickers, analysis_type, user_id):
    """Background task for batch processing."""
    for i, ticker in enumerate(tickers):
        # Process ticker
        analyze_company_task.delay(ticker, analysis_type, 'objective', user_id)

        # Update progress
        update_batch_progress(job_id, completed=i+1, total=len(tickers))

    return {"status": "success", "job_id": job_id}
```

**Why This Matters:**
- User submits analysis, gets immediate response with job ID
- Analysis runs in background
- User can check status anytime
- Multiple users can submit jobs simultaneously

#### C. WebSocket Support (For Real-Time Updates)

**Current:** No real-time updates
**Must Add:** WebSocket server for live progress

**Implementation:**

```python
# NEW: websocket.py
from fastapi import WebSocket
import json

active_connections = {}

async def connect_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    active_connections[job_id] = websocket

async def broadcast_progress(job_id: str, progress_data: dict):
    """Send progress update to connected clients."""
    if job_id in active_connections:
        await active_connections[job_id].send_text(json.dumps(progress_data))

# In analysis code:
async def update_progress(job_id, ticker, status):
    await broadcast_progress(job_id, {
        "type": "ticker_completed",
        "ticker": ticker,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })
```

**Why This Matters:**
- Users see live updates: "Analyzing AAPL... 25% complete"
- No polling needed (more efficient)
- Better UX: feels responsive

#### D. REST API Layer (FastAPI)

**Current:** CLI commands only
**Must Add:** RESTful HTTP API

```python
# NEW: api/main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uuid

app = FastAPI(title="Fintel API", version="1.0")

# Request Models
class AnalysisRequest(BaseModel):
    ticker: str
    analysis_type: str = "fundamental"  # fundamental, perspectives, both, contrarian
    analysis_path: str = "objective"   # excellent, objective
    num_years: int = 10

class BatchJobRequest(BaseModel):
    tickers: list[str]
    analysis_type: str = "fundamental"
    analysis_path: str = "objective"
    num_workers: int = 10
    job_name: str = None

# Endpoints
@app.post("/api/v1/analyses", status_code=202)
async def create_analysis(request: AnalysisRequest, user=Depends(get_current_user)):
    """Submit a single company analysis."""
    analysis_id = str(uuid.uuid4())

    # Save to database with status=queued
    save_analysis(analysis_id, request, user.id, status='queued')

    # Submit to task queue
    analyze_company_task.delay(
        request.ticker,
        request.analysis_type,
        request.analysis_path,
        user.id
    )

    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "message": f"Analysis for {request.ticker} submitted successfully"
    }

@app.get("/api/v1/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get analysis result."""
    result = get_analysis_from_db(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result

@app.post("/api/v1/batch-jobs", status_code=202)
async def create_batch_job(request: BatchJobRequest, user=Depends(get_current_user)):
    """Submit a batch analysis job."""
    job_id = str(uuid.uuid4())

    # Save to database
    save_batch_job(job_id, request, user.id, status='queued')

    # Submit to task queue
    batch_analysis_task.delay(job_id, request.tickers, request.analysis_type, user.id)

    return {
        "job_id": job_id,
        "status": "queued",
        "total_tickers": len(request.tickers)
    }

@app.get("/api/v1/batch-jobs/{job_id}")
async def get_batch_job_status(job_id: str):
    """Get batch job status and progress."""
    job = get_batch_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

#### E. Configuration Management

**Current:** .env file with 25 individual API keys
**Must Change To:** Web-based configuration UI with database storage

```python
# NEW: config management
class ConfigManager:
    def add_api_key(self, key: str, label: str):
        """Add API key to rotation pool."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        save_to_db(key_hash=key_hash, label=label, is_active=True)

    def get_all_keys_status(self):
        """Get usage stats for all keys."""
        return db.query("""
            SELECT label, request_count, last_request_at
            FROM api_usage
            WHERE date = CURRENT_DATE
        """)

    def set_rate_limit(self, requests_per_day: int):
        """Update rate limit configuration."""
        update_config('max_requests_per_day', requests_per_day)
```

**Why This Matters:**
- Admins can add/remove API keys via UI
- Monitor which keys are exhausted
- Adjust rate limits without restarting

#### F. Result Caching

**Current:** No caching (re-analyzes if you ask twice)
**Must Add:** Redis caching layer

```python
import redis

cache = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_analysis(ticker, year):
    key = f"analysis:{ticker}:{year}"
    cached = cache.get(key)
    if cached:
        return json.loads(cached)
    return None

def cache_analysis(ticker, year, result, ttl=86400*7):  # 7 days
    key = f"analysis:{ticker}:{year}"
    cache.setex(key, ttl, json.dumps(result))
```

**Why This Matters:**
- Instant results for previously analyzed companies
- Reduce API costs
- Better UX (no waiting for repeat requests)

---

## 4. Proposed REST API

### Complete API Specification

#### Authentication

All requests except login require JWT token in Authorization header:
```
Authorization: Bearer <jwt_token>
```

#### Endpoints

**POST /api/v1/auth/login**
```json
Request:
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "analyst"
  }
}
```

**POST /api/v1/analyses**
```json
Request:
{
  "ticker": "AAPL",
  "analysis_type": "fundamental",  // fundamental|perspectives|both|contrarian
  "analysis_path": "excellent",   // excellent|objective (for multi-year)
  "num_years": 10
}

Response (202 Accepted):
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "ticker": "AAPL",
  "estimated_completion": "2024-12-06T15:30:00Z"
}
```

**GET /api/v1/analyses/{analysis_id}**
```json
Response:
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "fiscal_year": 2023,
  "analysis_type": "fundamental",
  "analysis_path": "excellent",
  "status": "completed",  // queued|processing|completed|failed
  "progress": 100,  // 0-100
  "created_at": "2024-12-06T14:00:00Z",
  "completed_at": "2024-12-06T14:05:30Z",
  "result": {
    // Full TenKAnalysis or other Pydantic model as JSON
    "business_model": "...",
    "financial_highlights": {...},
    "key_takeaways": [...]
  },
  "error_message": null
}
```

**GET /api/v1/analyses?ticker=AAPL&status=completed&type=fundamental**
```json
Response:
{
  "total": 15,
  "page": 1,
  "per_page": 10,
  "analyses": [
    {
      "analysis_id": "...",
      "ticker": "AAPL",
      "fiscal_year": 2023,
      "status": "completed",
      "created_at": "...",
      "preview": {
        "compounder_score": 92,  // If benchmark analysis
        "alpha_score": 450,      // If contrarian analysis
        "buffett_verdict": "BUY" // If perspectives analysis
      }
    },
    ...
  ]
}
```

**POST /api/v1/batch-jobs**
```json
Request:
{
  "job_name": "Tech Giants Analysis",
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
  "analysis_type": "fundamental",
  "analysis_path": "excellent",
  "num_workers": 5,
  "num_years": 10
}

Response (202 Accepted):
{
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "job_name": "Tech Giants Analysis",
  "status": "queued",
  "total_tickers": 5,
  "estimated_completion": "2024-12-06T16:00:00Z"
}
```

**GET /api/v1/batch-jobs/{job_id}**
```json
Response:
{
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "job_name": "Tech Giants Analysis",
  "status": "processing",  // queued|processing|paused|completed|failed
  "progress": {
    "total": 5,
    "completed": 3,
    "pending": 2,
    "failed": 0,
    "current_ticker": "GOOGL"
  },
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
  "results": [
    {
      "ticker": "AAPL",
      "status": "completed",
      "analysis_id": "...",
      "completed_at": "2024-12-06T14:15:00Z"
    },
    {
      "ticker": "MSFT",
      "status": "completed",
      "analysis_id": "...",
      "completed_at": "2024-12-06T14:20:00Z"
    },
    {
      "ticker": "GOOGL",
      "status": "processing",
      "analysis_id": "...",
      "started_at": "2024-12-06T14:25:00Z"
    },
    {
      "ticker": "AMZN",
      "status": "queued",
      "analysis_id": null
    },
    {
      "ticker": "META",
      "status": "queued",
      "analysis_id": null
    }
  ],
  "created_at": "2024-12-06T14:00:00Z",
  "started_at": "2024-12-06T14:05:00Z",
  "estimated_completion": "2024-12-06T15:30:00Z"
}
```

**PATCH /api/v1/batch-jobs/{job_id}**
```json
Request:
{
  "action": "pause"  // pause|resume|cancel
}

Response:
{
  "job_id": "...",
  "status": "paused",
  "message": "Job paused successfully"
}
```

**GET /api/v1/batch-jobs/{job_id}/results**
```json
Response:
{
  "job_id": "...",
  "total_results": 3,
  "results": [
    {
      "ticker": "AAPL",
      "analysis_id": "...",
      "preview": {
        "compounder_score": 92,
        "business_model": "...",
        "key_strength": "Ecosystem lock-in"
      }
    },
    ...
  ]
}
```

**GET /api/v1/config**
```json
Response:
{
  "api_keys": {
    "total": 25,
    "available_today": 18,
    "exhausted": 7
  },
  "usage_today": {
    "total_requests": 3450,
    "limit": 12500,
    "percentage": 27.6
  },
  "rate_limits": {
    "max_requests_per_day_per_key": 500,
    "sleep_between_requests": 65
  },
  "processing": {
    "num_workers": 25,
    "default_num_filings": 10,
    "supported_analysis_types": [
      "fundamental",
      "perspectives",
      "contrarian",
      "both"
    ]
  },
  "models": {
    "default": "gemini-2.5-flash",
    "available": ["gemini-2.5-flash", "gemini-2.5-pro"],
    "thinking_budget": 4096
  }
}
```

**PUT /api/v1/config** (Admin only)
```json
Request:
{
  "num_workers": 15,
  "sleep_between_requests": 60,
  "default_model": "gemini-2.5-pro"
}

Response:
{
  "message": "Configuration updated successfully",
  "config": {...}  // Updated config
}
```

**POST /api/v1/config/api-keys** (Admin only)
```json
Request:
{
  "api_key": "AIzaSy...",
  "label": "Production Key 26"
}

Response:
{
  "key_id": "uuid",
  "label": "Production Key 26",
  "status": "active",
  "added_at": "2024-12-06T14:00:00Z"
}
```

**DELETE /api/v1/config/api-keys/{key_id}** (Admin only)

**POST /api/v1/baselines**
```json
Request:
{
  "name": "top_50_tech_2024",
  "description": "Top 50 technology companies baseline",
  "tickers": ["AAPL", "MSFT", ...]  // Must have analyses completed
}

Response (202 Accepted):
{
  "baseline_id": "uuid",
  "status": "processing",
  "message": "Baseline meta-analysis started"
}
```

**GET /api/v1/baselines**
```json
Response:
{
  "baselines": [
    {
      "baseline_id": "...",
      "name": "top_50_tech_2024",
      "total_companies": 50,
      "created_at": "2024-12-01T00:00:00Z",
      "is_active": true
    },
    ...
  ]
}
```

**GET /api/v1/baselines/{baseline_id}**
```json
Response:
{
  "baseline_id": "...",
  "name": "top_50_tech_2024",
  "description": "...",
  "companies": ["AAPL", "MSFT", ...],
  "meta_analysis": {
    "universal_success_factors": [...],
    "leadership_patterns": {...},
    "financial_patterns": {...}
  },
  "created_at": "...",
  "is_active": true
}
```

**POST /api/v1/export**
```json
Request:
{
  "format": "csv",  // csv|excel|parquet|json
  "filters": {
    "analysis_type": "fundamental",
    "min_compounder_score": 75,
    "min_alpha_score": 400,
    "tickers": ["AAPL", "MSFT"],  // Optional
    "date_from": "2024-12-01",
    "date_to": "2024-12-06"
  },
  "fields": [
    "ticker",
    "company_name",
    "compounder_score",
    "alpha_score",
    "buffett_verdict",
    "financial_highlights"
  ]
}

Response:
{
  "download_url": "/api/v1/downloads/export-uuid.csv",
  "expires_at": "2024-12-06T15:00:00Z",
  "total_records": 45,
  "file_size": 123456
}
```

**GET /api/v1/progress** (System Overview)
```json
Response:
{
  "active_jobs": 3,
  "queued_jobs": 5,
  "analyses_today": {
    "total": 150,
    "completed": 145,
    "failed": 5
  },
  "api_usage": {
    "requests_today": 3450,
    "requests_remaining": 9050,
    "percentage_used": 27.6,
    "reset_at": "2024-12-07T00:00:00Z"
  },
  "workers": {
    "total": 25,
    "active": 8,
    "idle": 17
  }
}
```

#### WebSocket

**WS /ws/batch-jobs/{job_id}**
```json
Connect:
ws://api.fintel.com/ws/batch-jobs/650e8400-e29b-41d4-a716-446655440000

Receive (Stream of events):
{
  "event": "ticker_started",
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "ticker": "GOOGL",
  "timestamp": "2024-12-06T14:25:00Z"
}

{
  "event": "ticker_completed",
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "ticker": "GOOGL",
  "analysis_id": "...",
  "preview": {
    "compounder_score": 88
  },
  "timestamp": "2024-12-06T14:30:00Z"
}

{
  "event": "ticker_failed",
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "ticker": "AMZN",
  "error": "API quota exceeded",
  "timestamp": "2024-12-06T14:35:00Z"
}

{
  "event": "job_completed",
  "job_id": "650e8400-e29b-41d4-a716-446655440000",
  "total": 5,
  "completed": 4,
  "failed": 1,
  "timestamp": "2024-12-06T14:40:00Z"
}
```

**WS /ws/system** (System-wide events)
```json
{
  "event": "api_quota_warning",
  "message": "API quota at 90% (4500/5000)",
  "timestamp": "..."
}

{
  "event": "worker_status",
  "active_workers": 12,
  "idle_workers": 13,
  "timestamp": "..."
}
```

---

## 5. Data Models Reference

### Complete Model Specifications

All models below are Pydantic `BaseModel` classes that serialize to JSON.

#### TenKAnalysis (Basic 10-K Analysis)

```typescript
interface TenKAnalysis {
  business_model: string;          // How company makes money
  unique_value: string;             // What differentiates them
  key_strategies: string[];         // Strategic initiatives
  financial_highlights: {
    revenue: string;                // Revenue with growth rate
    profit: string;                 // Net income and margins
    cash_position: string;          // Cash and debt levels
  };
  risks: string[];                  // Major risks
  management_quality: string;       // Leadership assessment
  innovation: string;               // R&D approach
  competitive_position: string;     // Market position
  esg_factors: string;              // ESG considerations
  key_takeaways: string[];          // 3-5 main insights
}
```

**Example:**
```json
{
  "business_model": "Subscription-based cloud platform for enterprise collaboration",
  "unique_value": "Integrated ecosystem with strong network effects",
  "key_strategies": [
    "Expand international markets",
    "Develop AI-powered features",
    "Strengthen cybersecurity"
  ],
  "financial_highlights": {
    "revenue": "$500M revenue, up 35% YoY",
    "profit": "$100M net income, 20% margin",
    "cash_position": "$200M cash, $50M debt"
  },
  "risks": [
    "Competition from larger players",
    "Customer concentration (top 10 = 40% revenue)",
    "Data privacy regulations"
  ],
  "management_quality": "Strong - founder-led with deep industry experience",
  "innovation": "15% of revenue to R&D, focused on AI/ML",
  "competitive_position": "Leader in niche market, 35% market share",
  "esg_factors": "Carbon neutral operations, strong governance",
  "key_takeaways": [
    "Rapid growth with expanding margins",
    "Strong product-market fit evidenced by 97% retention",
    "International expansion opportunity (currently 90% US)"
  ]
}
```

#### CompanySuccessFactors (Multi-Year Objective Analysis)

```typescript
interface CompanySuccessFactors {
  company_name: string;
  period_analyzed: string[];                    // ["2015", "2016", ...]
  business_model: {
    core_operations: string;
    strategic_shifts: Array<{
      period: string;                           // "2018"
      change: string;                           // What changed
      measured_outcome: string;                 // Results
    }>;
    operational_consistency: string;
  };
  performance_factors: Array<{
    factor: string;                             // "Network effects"
    business_impact: string;                    // How it affected results
    development: string;                        // How it evolved
  }>;
  financial_metrics: {
    revenue_analysis: string;
    profit_analysis: string;
    capital_decisions: string;
    financial_position: string[];
  };
  market_position: Array<{
    factor: string;
    durability: string;
    business_effect: string;
  }>;
  distinguishing_characteristics: string[];     // What makes them unique
  // ... (simplified for brevity)
}
```

#### ExcellentCompanyFactors (Multi-Year Success-Focused)

```typescript
interface ExcellentCompanyFactors {
  company_name: string;
  years_analyzed: string[];
  business_evolution: {
    core_model: string;
    key_changes: Array<{
      year: string;
      change: string;
      impact: string;
    }>;
    strategic_consistency: string;
  };
  success_factors: Array<{
    factor: string;                             // "Customer obsession"
    importance: string;                         // Why it mattered
    evolution: string;                          // How it developed
  }>;
  financial_performance: {
    revenue_trends: string;
    profitability: string;
    capital_allocation: string;
    financial_strengths: string[];
  };
  competitive_advantages: Array<{
    advantage: string;                          // "Switching costs"
    sustainability: string;                     // "High"
    impact: string;                             // Value created
  }>;
  management_excellence: {
    key_decisions: string[];
    leadership_qualities: string[];
    governance: string;
  };
  unique_attributes: string[];                  // Differentiating factors
  // ... (simplified)
}
```

#### BuffettAnalysis (Value Investing Lens)

```typescript
interface BuffettAnalysis {
  business_understanding: string;               // Simple explanation
  economic_moat: string;                        // Type of moat
  moat_rating: "Wide" | "Narrow" | "None";
  management_quality: string;                   // Grade A-F
  pricing_power: string;                        // Can raise prices?
  return_on_invested_capital: string;           // ROIC calculation
  free_cash_flow_quality: string;               // FCF trends
  business_tailwinds: string[];                 // Secular trends
  intrinsic_value_estimate: string;             // Valuation
  buffett_verdict: "BUY" | "HOLD" | "PASS";
}
```

#### TalebAnalysis (Antifragility Lens)

```typescript
interface TalebAnalysis {
  fragility_assessment: string;                 // Debt, fixed costs
  tail_risk_exposure: string[];                 // Black swan events
  optionality_and_asymmetry: string;            // Upside/downside
  skin_in_the_game: string;                     // Insider ownership
  hidden_risks: string[];                       // Non-obvious risks
  lindy_effect: string;                         // Business model age
  dependency_chains: string;                    // Single points of failure
  via_negativa: string[];                       // What to stop doing
  antifragile_rating: "Fragile" | "Robust" | "Antifragile";
  taleb_verdict: "EMBRACE" | "NEUTRAL" | "AVOID";
}
```

#### ContrarianViewAnalysis

```typescript
interface ContrarianViewAnalysis {
  consensus_view: string;                       // Market narrative
  consensus_wrong_because: string[];            // Why it's wrong
  hidden_strengths: string[];                   // Underappreciated positives
  hidden_weaknesses: string[];                  // Overrated aspects
  misunderstood_metrics: string;                // What market watches vs should watch
  second_order_effects: string[];               // Cascading consequences
  variant_perception: string;                   // Unique thesis
  contrarian_rating: string;                    // "Strong Contrarian BUY"
}
```

#### MultiPerspectiveAnalysis (Combined)

```typescript
interface MultiPerspectiveAnalysis {
  ticker: string;
  company_name: string;
  fiscal_year: number;
  buffett_lens: BuffettAnalysis;
  taleb_lens: TalebAnalysis;
  contrarian_lens: ContrarianViewAnalysis;
  key_insights: string[];                       // Top 5-7 insights
  final_verdict: string;                        // STRONG BUY/BUY/HOLD/SELL/STRONG SELL
}
```

#### BenchmarkComparison (Compounder DNA Scoring)

```typescript
interface BenchmarkComparison {
  company_name: string;
  compounder_potential: {
    score: number;                              // 0-100
    category: string;                           // "Future Compounder" | "Strong Potential" | ...
    summary: string;
    distinctive_strengths: string[];
    critical_gaps: string[];
  };
  success_factor_alignment: Array<{
    factor: string;
    baseline_pattern: string;                   // What top 50 do
    company_manifestation: string;              // How this company shows it
    alignment_strength: string;                 // "Strong" | "Moderate" | "Weak"
    evidence: string[];
  }>;
  leadership_assessment: {
    decision_making_quality: string;
    capital_allocation_discipline: string;
    long_term_orientation: string;
    organizational_health: string;
    succession_readiness: string;
  };
  strategic_positioning_assessment: {
    moat_analysis: string;
    competitive_dynamics: string;
    market_opportunity: string;
    positioning_strength: string;
  };
  financial_patterns_assessment: {
    growth_characteristics: string;
    margin_profile: string;
    capital_efficiency: string;
    reinvestment_approach: string;
  };
  innovation_systems_assessment: {
    rd_effectiveness: string;
    adaptation_capability: string;
    technology_positioning: string;
    future_readiness: string;
  };
  operational_excellence_assessment: {
    execution_consistency: string;
    scalability: string;
    efficiency_trends: string;
    quality_metrics: string;
  };
  final_assessment: {
    verdict: string;
    probability_of_outperformance: "High" | "Medium" | "Low";
    key_watch_metrics: string[];
    investment_considerations: string[];
  };
}
```

**Score Categories:**
- 90-100: Future Compounder
- 75-89: Strong Potential
- 60-74: Developing Contender
- 40-59: Partial Alignment
- 20-39: Limited Alignment
- 0-19: Misaligned

#### ContrarianAnalysis (6-Dimension Scoring)

```typescript
interface ContrarianAnalysis {
  ticker: string;
  company_name: string;
  overall_alpha_score: number;                  // 0-600 (sum of 6 dimensions)
  category: string;                             // "High Alpha Potential" | ...
  strategic_anomaly: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  asymmetric_resources: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  contrarian_positioning: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  cross_industry_dna: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  early_infrastructure: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  intellectual_capital: {
    score: number;                              // 0-100
    evidence: string[];
    reasoning: string;
  };
  synthesis: string;                            // Overall assessment
  investment_thesis: string;                    // Specific thesis
  risk_factors: string[];
  catalyst_timeline: string[];                  // "Q3 2024: Product launch"
  confidence_level: "High" | "Medium" | "Low";
}
```

**Score Interpretation:**
- 500-600: Exceptional contrarian opportunity
- 400-499: High contrarian potential
- 300-399: Moderate contrarian interest
- 200-299: Low contrarian signal
- <200: Not contrarian

---

## 6. User Workflows

### Workflow 1: Single Company Analysis

**User Goal:** Analyze Apple to see if it's a good investment

**Steps:**
1. Navigate to "Analyze Company" page
2. Enter ticker: `AAPL`
3. Select analysis type: `Fundamental + Perspectives`
4. Select analysis path: `Excellent` (because Apple is a known winner)
5. Set number of years: `10`
6. Click "Analyze"

**Backend Actions:**
1. Validate ticker exists
2. Create analysis record in database (status=queued)
3. Submit to Celery task queue
4. Return analysis_id immediately
5. Background worker:
   - Download 10 years of 10-K filings
   - Convert HTML → PDF
   - Extract text
   - Run fundamental analysis for each year
   - Run success factor analysis (excellent path)
   - Run Buffett/Taleb/Contrarian lenses
   - Save results to database
   - Update status to completed

**Frontend Display:**
1. Show "Analysis queued" message with job ID
2. Poll /api/v1/analyses/{analysis_id} every 5 seconds OR use WebSocket
3. Show progress bar (10 filings to analyze)
4. When completed, redirect to results page
5. Display:
   - Compounder DNA score (big prominent number 0-100)
   - Success factors as expandable sections
   - Buffett verdict (BUY/HOLD/PASS)
   - Taleb antifragile rating
   - Contrarian insights
   - Charts: Revenue trend, margin expansion, ROIC over time

### Workflow 2: Batch Analysis

**User Goal:** Analyze 50 technology companies to find top compounders

**Steps:**
1. Navigate to "Batch Analysis" page
2. Upload CSV file with tickers OR paste list
3. Select analysis type: `Fundamental`
4. Select path: `Objective` (unknown companies, need unbiased view)
5. Set workers: `10`
6. Click "Start Batch Job"

**Backend Actions:**
1. Parse ticker list
2. Create batch_job record (status=queued)
3. Submit to task queue
4. For each ticker (in parallel up to 10):
   - Run analysis (same as Workflow 1)
   - Update batch job progress
   - Send WebSocket event on completion
5. When all done, mark job as completed

**Frontend Display:**
1. Show batch job dashboard
2. Real-time progress: "15 of 50 completed (30%)"
3. Live ticker updates via WebSocket: "Analyzing MSFT..."
4. Show completed tickers in table with preview (compounder score)
5. When done:
   - Show summary table sortable by score
   - Filter controls (min score, date range)
   - Export button (CSV, Excel)
   - Bulk actions (delete, re-analyze)

### Workflow 3: Contrarian Scanning

**User Goal:** Find hidden gems in the market

**Steps:**
1. Navigate to "Contrarian Scanner" page
2. Upload ticker list (e.g., S&P 500)
3. Set minimum alpha score: `400` (high threshold)
4. Set top N: `20` (show top 20)
5. Click "Scan"

**Backend Actions:**
1. For each ticker:
   - Check if success factors analysis exists, if not run it
   - Run contrarian scanner (6-dimension scoring)
   - Calculate total alpha score (0-600)
2. Rank by alpha score
3. Filter by minimum threshold
4. Return top N

**Frontend Display:**
1. Progress bar for scanning
2. Results table:
   - Ticker | Company | Alpha Score | Category | Investment Thesis
3. Click row to expand:
   - 6 dimension scores (radar chart)
   - Evidence for each dimension
   - Risk factors
   - Catalyst timeline
4. Export filtered results

### Workflow 4: Compare Companies

**User Goal:** Compare AAPL vs MSFT vs GOOGL

**Steps:**
1. Navigate to "Compare" page
2. Select companies: AAPL, MSFT, GOOGL
3. Select comparison type: `Benchmarking`
4. Click "Compare"

**Frontend Display:**
1. Side-by-side comparison table:
   - Compounder score
   - Success factors (checkmarks for present)
   - Financial metrics
   - Leadership assessment
2. Charts:
   - Bar chart of scores
   - Radar chart of success factor alignment
3. Download comparison report (PDF)

---

## 7. UI Component Requirements

### Page 1: Dashboard (Homepage)

**Purpose:** Overview of system and recent activity

**Components:**
- **Stats Cards**
  - Total Analyses Today
  - Active Batch Jobs
  - API Quota Remaining (%)
  - Top Performer This Week (highest compounder score)

- **Recent Analyses Table**
  - Columns: Ticker, Company, Type, Score, Date, Status
  - Click row → Go to results page

- **Active Jobs Panel**
  - List of running batch jobs
  - Progress bars
  - Pause/Resume/Cancel buttons

- **Quick Actions**
  - "Analyze Single Company" button
  - "Start Batch Job" button
  - "Scan for Contrarian Opportunities" button

### Page 2: Analyze Company

**Components:**
- **Form**
  - Ticker input (with autocomplete if possible)
  - Analysis type dropdown:
    - Fundamental Only
    - Perspectives Only
    - Fundamental + Perspectives
    - Contrarian Scanning
  - Analysis path radio buttons:
    - Excellent (for known winners)
    - Objective (for unknown companies)
    - Help text explaining difference
  - Number of years slider (1-30, default 10)

- **Advanced Options (Collapsible)**
  - Model selection (gemini-2.5-flash or gemini-2.5-pro)
  - Thinking budget (512-8192)
  - Skip download if already cached

- **Submit Button**
  - "Analyze" → Submits job

- **Progress Modal** (appears after submit)
  - "Analyzing AAPL..."
  - Progress bar or spinner
  - "View Results" button (enabled when done)

### Page 3: Batch Analysis

**Components:**
- **Ticker Input**
  - File upload (.csv, .txt)
  - OR text area (paste tickers, one per line)
  - OR manual entry with tags (add/remove chips)
  - Preview: "50 tickers loaded"

- **Configuration**
  - Analysis type dropdown
  - Analysis path selection
  - Number of workers slider (1-25)
  - Job name input

- **Submit Button**
  - "Start Batch Job"

- **Job Progress View** (after submit)
  - Job name at top
  - Overall progress: "15 of 50 completed (30%)"
  - ETA: "Estimated completion: 2 hours"
  - Ticker table:
    - Ticker | Status | Started | Completed | Score
    - Color coding: Green (done), Yellow (processing), Gray (queued), Red (failed)
  - Real-time updates via WebSocket
  - Control buttons: Pause, Resume, Cancel

- **Results View** (when job completes)
  - Summary stats: "45 completed, 5 failed"
  - Table with all results
  - Sort by score, ticker, date
  - Filter controls
  - Export button

### Page 4: Results (Single Company)

**Layout:**

**Header Section:**
- Ticker + Company Name (large)
- Fiscal Year
- Analysis Date
- Status badge

**Scores Section** (Prominent cards at top):
- Compounder DNA Score (0-100)
  - Large number with color (red <40, yellow 40-74, green 75+)
  - Category label ("Future Compounder")
- Alpha Score (0-600) (if contrarian analysis)
  - Large number
  - Category label
- Buffett Verdict (if perspectives)
  - BUY/HOLD/PASS with icon
- Taleb Rating (if perspectives)
  - Fragile/Robust/Antifragile with icon

**Tabs:**

**Tab 1: Overview**
- Key Takeaways (bullet points)
- Business Model (expandable text)
- Financial Highlights
  - Revenue, Profit, Cash Position
- Unique Attributes
- Success Factors (top 5)

**Tab 2: Financial Analysis**
- Revenue trend chart (line chart, 10 years)
- Margin trend chart
- Capital allocation breakdown (pie chart)
- Financial strengths/weaknesses

**Tab 3: Competitive Position**
- Market position assessment
- Competitive advantages (with sustainability ratings)
- Moat analysis (if Buffett lens)

**Tab 4: Perspectives** (if multi-perspective analysis)
- Accordion sections:
  - Buffett Lens
    - Economic moat details
    - ROIC calculation
    - Intrinsic value estimate
  - Taleb Lens
    - Fragility assessment
    - Tail risks (list)
    - Hidden risks
  - Contrarian Lens
    - Consensus vs reality
    - Hidden strengths/weaknesses
    - Variant perception

**Tab 5: Benchmark Comparison** (if available)
- Score breakdown (6 categories)
- Radar chart of alignment
- Factor-by-factor comparison table
- Distinctive strengths
- Critical gaps

**Tab 6: Contrarian Dimensions** (if contrarian analysis)
- 6 dimension cards:
  - Strategic Anomaly (0-100)
  - Asymmetric Resources (0-100)
  - Contrarian Positioning (0-100)
  - Cross-Industry DNA (0-100)
  - Early Infrastructure (0-100)
  - Intellectual Capital (0-100)
- Each card:
  - Score with progress bar
  - Evidence bullets
  - Reasoning text
- Investment Thesis (highlighted box)
- Risk Factors
- Catalyst Timeline

**Tab 7: Raw Data**
- JSON viewer (formatted, collapsible)
- Download JSON button
- Download PDF report button

### Page 5: Compare Companies

**Components:**
- **Company Selector**
  - Search/autocomplete for tickers
  - Add up to 5 companies
  - Must have analyses completed

- **Comparison Table**
  - Rows: Metrics (Compounder Score, Alpha Score, Revenue Growth, etc.)
  - Columns: Companies
  - Color coding for best/worst

- **Charts**
  - Bar chart: Scores comparison
  - Radar chart: Success factor alignment
  - Line charts: Financial metrics over time

- **Export**
  - Download comparison as PDF
  - Download data as CSV

### Page 6: Contrarian Scanner

**Components:**
- **Configuration**
  - Ticker list input (upload or paste)
  - Minimum alpha score slider (0-600, default 400)
  - Top N slider (10-100, default 20)
  - Confidence filter: High, Medium, Low

- **Results Table**
  - Ticker | Company | Alpha Score | Category | Thesis Preview | Actions
  - Click row → Expand details
  - Expanded view:
    - 6 dimension scores
    - Investment thesis (full)
    - Risk factors
    - Catalyst timeline
    - "View Full Analysis" button

- **Visualization**
  - Bubble chart: Alpha Score vs Compounder Score
  - Size = Market Cap
  - Click bubble → Go to company

- **Export**
  - Export top opportunities to CSV/Excel

### Page 7: Export & Reports

**Components:**
- **Export Builder**
  - Select format: CSV, Excel, Parquet, JSON
  - Select data:
    - All analyses
    - Filtered by type
    - Filtered by date range
    - Filtered by score ranges
    - Specific tickers
  - Select fields (checkboxes):
    - Ticker, Company Name
    - Scores (Compounder, Alpha)
    - Verdicts (Buffett, Taleb)
    - Financial metrics
    - Success factors
    - All fields

- **Report Templates**
  - "Top 20 Compounders" → Pre-configured export
  - "High Alpha Opportunities" → Pre-configured export
  - "Tech Sector Summary" → Pre-configured export

- **Schedule Reports** (Future enhancement)
  - Weekly email with top performers
  - Daily digest of new analyses

### Page 8: Configuration (Admin)

**Components:**
- **API Key Management**
  - Table: Label, Status (Active/Exhausted), Usage Today, Actions
  - Add Key button → Modal to paste key
  - Delete button (with confirmation)
  - Usage chart (line chart over 30 days)

- **Rate Limits**
  - Max requests per day per key (input)
  - Sleep between requests (seconds, input)
  - Save button

- **Processing**
  - Default number of workers (slider)
  - Default number of filings (slider)
  - Default model (dropdown)
  - Thinking budget (slider)

- **Baselines**
  - Table: Name, Companies, Created, Active
  - Create Baseline button → Modal:
    - Name input
    - Description
    - Ticker list
    - Submit → Starts meta-analysis
  - Activate/Deactivate toggle

### Page 9: Job History

**Components:**
- **Filters**
  - Date range picker
  - Job type (Single, Batch)
  - Status (All, Completed, Failed)
  - User (if multi-user)

- **Jobs Table**
  - Job Name/ID, Type, Tickers, Status, Created, Duration, Actions
  - Actions: View Results, Re-run, Delete

- **Pagination**
  - 10/25/50 per page

---

## 8. Real-Time Updates

### WebSocket Implementation

**Frontend (React Example):**

```javascript
// Connect to batch job WebSocket
const socket = new WebSocket(`ws://api.fintel.com/ws/batch-jobs/${jobId}`);

socket.onopen = () => {
  console.log('Connected to job updates');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.event) {
    case 'ticker_started':
      updateTickerStatus(data.ticker, 'processing');
      break;

    case 'ticker_completed':
      updateTickerStatus(data.ticker, 'completed');
      setTickerScore(data.ticker, data.preview.compounder_score);
      incrementProgress();
      break;

    case 'ticker_failed':
      updateTickerStatus(data.ticker, 'failed');
      showError(data.ticker, data.error);
      break;

    case 'job_completed':
      showJobCompleteNotification();
      enableExportButton();
      socket.close();
      break;
  }
};

socket.onerror = (error) => {
  console.error('WebSocket error:', error);
  // Fallback to polling
  startPolling();
};
```

**Fallback to Polling:**

If WebSocket fails, poll the API:

```javascript
function pollJobStatus() {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/v1/batch-jobs/${jobId}`);
    const data = await response.json();

    updateProgress(data.progress);

    if (data.status === 'completed' || data.status === 'failed') {
      clearInterval(interval);
      handleJobComplete(data);
    }
  }, 5000); // Poll every 5 seconds
}
```

---

## 9. Authentication & Authorization

### User Roles

**Role: Viewer**
- Can view analyses
- Can export results
- Cannot create analyses
- Cannot modify configuration

**Role: Analyst**
- All Viewer permissions
- Can create single analyses
- Can create batch jobs (limit: 100 tickers per job)
- Daily quota: 100 analyses

**Role: Admin**
- All Analyst permissions
- Can add/remove API keys
- Can modify configuration
- Can create baselines
- Can manage users
- Unlimited daily quota

### Implementation

**Backend (FastAPI):**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")

        user = get_user_from_db(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(role: str):
    """Decorator to require specific role."""
    def role_checker(user = Depends(get_current_user)):
        if user.role not in [role, "admin"]:  # Admin always allowed
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# Usage in endpoints:
@app.post("/api/v1/analyses")
async def create_analysis(
    request: AnalysisRequest,
    user = Depends(require_role("analyst"))
):
    # Check user's daily quota
    if user.analyses_today >= user.daily_quota:
        raise HTTPException(status_code=429, detail="Daily quota exceeded")

    # Create analysis...
```

**Frontend (React):**

```javascript
// Store token after login
const login = async (email, password) => {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password})
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
};

// Add token to all requests
const api = axios.create({
  baseURL: 'http://api.fintel.com'
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 (unauthorized) - redirect to login
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## 10. Deployment Considerations

### Architecture

```
[Frontend (React/Vue)]
       ↓ HTTPS
[Load Balancer (nginx)]
       ↓
[API Server (FastAPI)] ←→ [Redis (cache + queue)]
       ↓                       ↓
[PostgreSQL (results)]   [Celery Workers (x25)]
                               ↓
                         [Google Gemini API]
                         [SEC Edgar API]
```

### Infrastructure Requirements

**API Server:**
- 4 CPU cores, 8GB RAM minimum
- Handles HTTP requests
- Lightweight (just queues tasks)

**Celery Workers:**
- 25 workers (one per API key)
- Each worker: 2GB RAM, 1 CPU
- Total: 25 CPU cores, 50GB RAM
- Can scale horizontally (add more machines)

**PostgreSQL:**
- 4 CPU cores, 16GB RAM
- 500GB SSD storage (results grow over time)
- Backup daily

**Redis:**
- 2 CPU cores, 4GB RAM
- Used for task queue and caching

**Total:**
- ~60 CPU cores
- ~90GB RAM
- 500GB storage
- Estimated cost: $500-1000/month (AWS/GCP)

### Scaling Considerations

**Bottleneck 1: API Rate Limits**
- 25 keys × 500 requests/day = 12,500 analyses/day max
- Solution: Add more API keys (scales linearly)

**Bottleneck 2: Worker Capacity**
- Each analysis: ~90 seconds (65s sleep + 25s processing)
- 25 workers: ~20,000 analyses/day theoretical max
- Solution: Add more workers (cheap to scale)

**Bottleneck 3: Database**
- JSON results: ~50KB per analysis
- 10,000 analyses = 500MB
- 1M analyses = 50GB
- Solution: Archive old analyses, use Parquet compression

### Monitoring

**Metrics to Track:**
- API quota remaining (per key)
- Worker utilization (% busy)
- Queue depth (pending tasks)
- Database size
- Average analysis time
- Error rate (failed analyses)
- User quota usage

**Alerting:**
- API quota < 10% → Email admin
- All workers busy > 1 hour → Scale up warning
- Queue depth > 100 → Capacity warning
- Database > 80% full → Storage warning

### Security

**Must Implement:**
- HTTPS only (TLS 1.3)
- JWT token expiration (1 hour)
- Refresh tokens (7 days)
- Rate limiting per user (100 req/min)
- API key encryption at rest
- Audit logging (who analyzed what, when)
- CORS configuration (restrict origins)
- SQL injection prevention (use ORMs)
- XSS prevention (sanitize inputs)

---

## Summary: Critical Changes for Web UI

### Backend Changes (MUST DO):

1. **Add PostgreSQL database** with schemas for analyses, jobs, users, baselines
2. **Add Celery task queue** with Redis for async processing
3. **Add FastAPI REST API** with all endpoints specified above
4. **Add WebSocket server** for real-time updates
5. **Add authentication** (JWT-based)
6. **Add result caching** (Redis)
7. **Refactor file I/O** to database I/O
8. **Add progress callbacks** from analyzers to database
9. **Add API quota enforcement** per user
10. **Add audit logging**

### Estimated Backend Work: 3-4 weeks

**Week 1:**
- Database schema design and migration
- Basic REST API structure
- Authentication system

**Week 2:**
- Task queue integration
- Refactor analyzers to use database
- Progress tracking

**Week 3:**
- WebSocket implementation
- Caching layer
- API quota management

**Week 4:**
- Testing, bug fixes
- Performance optimization
- Documentation

### Frontend Work (Can Start in Parallel): 4-6 weeks

**Week 1-2:**
- UI design mockups
- Component library setup
- Authentication flows

**Week 3-4:**
- Core pages (Dashboard, Analyze, Batch, Results)
- API integration
- Real-time updates

**Week 5-6:**
- Visualizations (charts, comparisons)
- Export functionality
- Polish and testing

---

## Next Steps

1. **Review this document** with your frontend team
2. **Prioritize features** (MVP vs nice-to-have)
3. **Design database schema** (work with DBA if needed)
4. **Set up infrastructure** (AWS/GCP account, PostgreSQL, Redis)
5. **Backend team: Start with authentication and database layer**
6. **Frontend team: Start with UI mockups and component design**
7. **Schedule weekly syncs** to ensure alignment

---

**Questions?** Contact the Fintel backend team with any clarifications needed.

This guide is a living document - update it as the architecture evolves!
