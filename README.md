# Fintel

**AI-Powered SEC Filing Analysis Platform for Investment Research**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)](https://streamlit.io/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Overview

Fintel is a production-ready platform that analyzes SEC 10-K filings using Google Gemini AI to extract actionable investment insights. It combines multiple investment philosophies—Warren Buffett's value investing, Nassim Taleb's antifragility framework, and contrarian opportunity detection—into a unified analysis system.

### Why Fintel?

- **Multi-Perspective Analysis** - See companies through different investment lenses simultaneously
- **Structured AI Output** - Type-safe Pydantic models ensure consistent, reliable analysis results
- **Enterprise-Grade Batch Processing** - Analyze 1000+ companies reliably with automatic recovery
- **Scalable Processing** - Analyze hundreds of companies in parallel with 25+ API key rotation
- **Extensible Workflows** - Create custom analysis prompts without modifying core code
- **Resume Capability** - Interrupted analyses can be resumed from where they left off
- **Document Caching** - Downloaded SEC filings are cached to avoid redundant downloads
- **Discord Notifications** - Real-time alerts for batch completion, failures, and warnings

---

## Key Features

| Feature                         | Description                                            |
| ------------------------------- | ------------------------------------------------------ |
| **Multi-Perspective Analysis**  | Buffett, Taleb, and Contrarian investment lenses       |
| **Custom Workflows**            | Auto-discovered Python-based analysis workflows        |
| **Batch Processing**            | Analyze 1-1000+ companies with automatic recovery      |
| **Contrarian Scanner**          | 6-dimension hidden gem scoring (0-600 scale)           |
| **Compounder DNA**              | Compare against top 50 proven performers               |
| **Resume Support**              | Continue interrupted analyses automatically            |
| **API Key Rotation**            | Distribute load across 25+ Gemini API keys             |
| **Web + CLI**                   | Both Streamlit UI and command-line interface           |
| **Batch Queue**                 | Multi-day batch processing with progress tracking      |
| **Discord Notifications**       | Real-time alerts for batch events                      |
| **System Monitoring**           | Disk space, memory, and Chrome process monitoring      |
| **Database Backups**            | Automatic daily backups during batch processing        |
| **Cross-Process Rate Limiting** | File-based locking prevents API quota errors           |

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/gkgeo9/fintel.git
cd fintel

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dependencies
pip install -e ".[dev]"
```

### 2. Configuration

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required: Google Gemini API key(s)
GOOGLE_API_KEY_1=your_gemini_api_key_here
GOOGLE_API_KEY_2=your_second_key      # Optional: more keys = faster batch processing
# ... up to GOOGLE_API_KEY_25

# Required: SEC Edgar identification (SEC requires this)
FINTEL_SEC_USER_EMAIL=your@email.com
FINTEL_SEC_COMPANY_NAME="Investment Research"

# Optional: Discord notifications for batch processing
FINTEL_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

### 3. Launch

**Web Interface (Recommended):**

```bash
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`

**Command Line:**

```bash
# Single company analysis
fintel analyze AAPL --years 5

# Batch processing
fintel batch tickers.csv --workers 10
```

---

## Discord Notifications Setup

Fintel can send real-time notifications to Discord for batch processing events. This is highly recommended for overnight batch jobs processing 1000+ companies.

### What Gets Notified

| Event | Description | Color |
|-------|-------------|-------|
| **Batch Completed** | Summary of completed/failed items | Green |
| **Batch Failed** | Error details when batch fails | Red |
| **API Keys Exhausted** | All keys hit daily limit, waiting for reset | Orange |
| **Warnings** | Low disk space, high memory, etc. | Yellow |

### Setup Instructions

1. **Create a Discord Webhook:**
   - Open Discord and go to your server
   - Right-click on the channel where you want notifications → **Edit Channel**
   - Go to **Integrations** → **Webhooks** → **New Webhook**
   - Give it a name (e.g., "Fintel Bot") and copy the webhook URL

2. **Configure Environment Variable:**
   ```bash
   # Add to your .env file
   FINTEL_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdefghijklmnop
   ```

3. **Test the Connection:**
   ```python
   from fintel.core.notifications import NotificationService

   notifier = NotificationService()
   notifier.send_info("Fintel notifications configured successfully!")
   ```

### Example Notifications

**Batch Completed:**
```
✅ Batch Completed
Batch ID: abc12345
Completed: 847
Failed: 3
Duration: 24.5 hours
```

**Batch Failed:**
```
❌ Batch Failed
Batch ID: abc12345
Error: Database connection timeout after 30 retries
```

---

## Analysis Types

### Built-in Analysis Perspectives

| Type                   | Description                                                     | Min Years | Best For                 |
| ---------------------- | --------------------------------------------------------------- | --------- | ------------------------ |
| **Fundamental**        | Business model, financials, risks, competitive position         | 1         | Initial company research |
| **Buffett Lens**       | Economic moat, management quality, intrinsic value focus        | 1         | Value investing          |
| **Taleb Lens**         | Fragility assessment, tail risks, antifragility scoring         | 1         | Risk management          |
| **Contrarian Lens**    | Hidden opportunities, variant perception, market inefficiencies | 1         | Alpha generation         |
| **Multi-Perspective**  | Combined Buffett + Taleb + Contrarian analysis                  | 1         | Comprehensive view       |
| **Excellent Company**  | Success factors from proven multi-year winners                  | 3         | Pattern recognition      |
| **Objective Analysis** | Unbiased success/failure factors for any company                | 3         | Screening                |
| **Contrarian Scanner** | 6-dimension hidden compounder scoring (0-600)                   | 3         | Finding hidden gems      |

### Contrarian Scanner Dimensions

The scanner evaluates companies across six proprietary dimensions:

| Dimension                  | What It Detects                           |
| -------------------------- | ----------------------------------------- |
| **Strategic Anomaly**      | Bold, counterintuitive strategic moves    |
| **Asymmetric Resources**   | Concentrated capital allocation bets      |
| **Contrarian Positioning** | Inverse positioning to industry consensus |
| **Cross-Industry DNA**     | Foreign practices from other industries   |
| **Early Infrastructure**   | Building for future scale before needed   |
| **Intellectual Capital**   | Undervalued patents, IP, and know-how     |

**Scoring:** 0-100 per dimension, 0-600 total Alpha Score

---

## Custom Workflows

Create your own analysis workflows by adding Python files to `custom_workflows/`. They're automatically discovered and appear in the UI.

### Quick Example

```python
# custom_workflows/dividend_analyzer.py
from pydantic import BaseModel, Field
from typing import List
from custom_workflows.base import CustomWorkflow

class DividendResult(BaseModel):
    """Structured output for dividend analysis."""
    dividend_safety_score: int = Field(ge=0, le=100, description="Dividend safety 0-100")
    payout_ratio: float = Field(description="Dividend payout ratio as decimal")
    years_of_growth: int = Field(description="Consecutive years of dividend growth")
    key_risks: List[str] = Field(description="Top risks to dividend sustainability")
    recommendation: str = Field(description="Hold, accumulate, or avoid")

class DividendAnalyzer(CustomWorkflow):
    name = "Dividend Safety"
    description = "Analyzes dividend sustainability and growth potential"
    icon = "💰"
    min_years = 3

    @property
    def prompt_template(self) -> str:
        return """
        Analyze {ticker} for fiscal year {year} focusing on dividend sustainability.

        Evaluate:
        1. Free cash flow coverage of dividends
        2. Payout ratio trends
        3. Balance sheet strength to support dividends
        4. Historical dividend growth track record
        5. Industry cyclicality and impact on dividends

        Be conservative in your safety score assessment.
        """

    @property
    def schema(self):
        return DividendResult
```

See [docs/CUSTOM_WORKFLOWS.md](docs/CUSTOM_WORKFLOWS.md) for the complete developer guide.

---

## Batch Processing Reliability

Fintel includes enterprise-grade reliability features for processing 1000+ companies over multi-day batch runs.

### Reliability Features

| Feature | Description |
|---------|-------------|
| **Disk Space Monitoring** | Preflight checks and periodic monitoring during processing |
| **Chrome Process Cleanup** | Automatic cleanup of orphaned browser processes every 50 companies |
| **Database Backups** | Daily automatic backups with 7-day retention |
| **Thread-Safe Progress** | File-based locking prevents race conditions |
| **Exponential Backoff** | Up to 10 retries with jitter for database operations |
| **Discord Alerts** | Real-time notifications for completion, failures, and warnings |
| **Log Rotation** | 10MB max file size with 5 backup files |
| **SEC Rate Limiting** | Global cross-process rate limiter for SEC Edgar API |

### Running Large Batches (1000+ Companies)

For processing 1000+ companies across 10+ years:

1. **Configure notifications** (see Discord setup above)
2. **Ensure sufficient disk space** (minimum 5GB free, 10GB recommended)
3. **Use the CLI for multi-day runs** (survives browser disconnects)
4. **Monitor via Discord** - you'll receive completion/failure alerts

#### CLI Batch (Recommended for Large Scale)

```bash
# Start in tmux/screen for persistence
tmux new -s fintel-batch

# 1000 companies, 10 years each, multi-perspective analysis
fintel batch companies.csv --years 10 --analysis-type multi

# Detach: Ctrl+B then D
# Reattach later: tmux attach -t fintel-batch

# If interrupted, resume from where it left off
fintel batch --resume

# Resume a specific batch
fintel batch --resume-id <batch_id>

# List all incomplete batches
fintel batch --list-incomplete
```

#### CSV Input Format

```csv
ticker
AAPL
MSFT
GOOGL
AMZN
```

Or with optional company name:

```csv
ticker,company_name
AAPL,Apple Inc.
MSFT,Microsoft Corporation
```

#### Capacity Planning

| Companies | Years | API Requests | Estimated Duration (25 keys) |
|-----------|-------|-------------|------------------------------|
| 10        | 7     | 70          | < 1 day                      |
| 100       | 7     | 700         | ~1.5 days                    |
| 500       | 10    | 5,000       | ~10 days                     |
| 1,000     | 7     | 7,000       | ~14 days                     |
| 1,000     | 10    | 10,000      | ~20 days                     |

**Throughput formula:** 25 API keys x 20 requests/key/day = **500 requests/day**

#### How Batch Processing Works

```
1. Create batch job → tickers stored in SQLite
2. ThreadPoolExecutor starts N workers (up to 25)
3. Each worker:
   a. Reserves an API key (atomic, no collisions)
   b. Downloads SEC filings for one company
   c. Converts HTML → PDF → extracts text
   d. Sends to Gemini AI for each year
   e. Stores validated Pydantic results in DB
   f. Releases API key → picks up next company
4. When all keys hit daily limit → waits for midnight PST reset
5. After reset verification → resumes processing automatically
6. Completed companies are never re-processed on resume
```

#### Error Handling at Scale

| Error Type | Behavior |
|-----------|----------|
| **Context length exceeded** | Company marked as SKIPPED (not retried) |
| **API quota exhausted** | Waits for midnight PST reset, then resumes |
| **Network/transient error** | Retried up to max_retries (default 2) |
| **Process crash** | Resume picks up from last completed company |

---

## Known Limitations & Improvement Opportunities

The following areas have been identified for improvement, particularly for large-scale batch processing (1000+ companies, 10+ years):

### Resume Granularity

**Current:** Resume tracks progress per-company. If a company fails at year 7 of 10, all 10 years are re-processed on resume. The `batch_item_year_checkpoints` table schema exists but the per-year checkpoint logic is not yet implemented.

**Improvement:** Implement per-year resume so interrupted companies restart from the last completed year, not from scratch. This becomes significant at 10+ years per company.

### Throughput Bottleneck

**Current:** All API requests are serialized through a single global file lock with a mandatory 65-second sleep. Even with 25 keys, effective throughput is ~500 requests/day because the lock serializes requests rather than allowing parallel calls on different keys.

**Improvement:** Move to per-key locks instead of a single global lock. Each API key could process requests independently, increasing theoretical throughput to 25 parallel streams. This is the single highest-impact performance improvement possible.

### Batch Priority & Ordering

**Current:** Companies are processed in FIFO order. No way to prioritize specific tickers or re-order the queue mid-batch.

**Improvement:** Add priority levels to batch items so high-interest companies are processed first. The database column exists (`priority`) but is not exposed in the CLI or UI.

### Partial Results on Failure

**Current:** If multi-perspective analysis fails on the Taleb lens after Buffett lens completes, both results are lost. Each perspective is not saved independently.

**Improvement:** Save each perspective result as it completes, so partial multi-analysis results are preserved even if one lens fails.

### Adaptive Rate Limiting

**Current:** Fixed 65-second sleep between all requests regardless of API response headers or actual rate limit state.

**Improvement:** Read Gemini API response headers for rate limit information and adapt sleep duration dynamically. Under low load, requests could be faster; under contention, back off further.

### Export Tooling for Large Datasets

**Current:** Export is available through the UI and a script in `scripts/`. No built-in CLI export command for bulk data extraction from large batch results.

**Improvement:** Add `fintel export --batch-id <id> --format csv` to export all results from a specific batch run, with filtering by status, ticker, or analysis type.

### Chrome Process Management

**Current:** Cleanup runs every 50 companies (arbitrary threshold). No demand-based cleanup or memory monitoring for the Chrome instances used in HTML→PDF conversion.

**Improvement:** Monitor Chrome process memory usage and trigger cleanup when a threshold is exceeded rather than on a fixed schedule.

### Deduplication

**Current:** No check for duplicate tickers in a batch CSV. If `AAPL` appears 3 times, it gets analyzed 3 times.

**Improvement:** Deduplicate tickers on batch creation and warn the user about removed duplicates.

---

## Web Interface

### Pages

| Page                 | Purpose                                                |
| -------------------- | ------------------------------------------------------ |
| **Home**             | Dashboard with metrics, recent analyses, quick actions |
| **Analysis**         | Run single or batch company analysis with all options  |
| **Analysis History** | Search, filter, and manage past analyses               |
| **Results Viewer**   | Explore results in formatted or JSON view, export      |
| **Batch Queue**      | Multi-day batch processing with progress monitoring    |
| **Settings**         | API usage, database viewer, custom prompts, cache      |

---

## CLI Reference

```bash
# Analyze a single company
fintel analyze AAPL --years 5 --type fundamental

# Analyze with specific years
fintel analyze MSFT --years 2020 2021 2022 2023

# Batch process from file
fintel batch tickers.csv --workers 10 --type buffett

# Contrarian scan with minimum score filter
fintel scan --tickers-file universe.txt --min-score 400

# Export results
fintel export --format csv --output results.csv
fintel export --format json --output results.json
```

### CLI Options

| Command   | Options                         | Description                       |
| --------- | ------------------------------- | --------------------------------- |
| `analyze` | `--years`, `--type`, `--filing` | Single company analysis           |
| `batch`   | `--workers`, `--type`           | Parallel multi-company processing |
| `scan`    | `--min-score`, `--tickers-file` | Contrarian opportunity scanning   |
| `export`  | `--format`, `--output`          | Export results to file            |

---

## Project Structure

```
fintel/
├── analysis/                    # Core analysis engines
│   ├── fundamental/             # 10-K analysis, success factors
│   │   ├── analyzer.py          # FundamentalAnalyzer
│   │   ├── success_factors.py   # ExcellentCompanyAnalyzer, ObjectiveCompanyAnalyzer
│   │   ├── models/              # Pydantic output schemas
│   │   └── prompts/             # AI prompt templates
│   ├── perspectives/            # Investment lens analyzers
│   │   ├── analyzer.py          # PerspectiveAnalyzer (Buffett, Taleb, Contrarian)
│   │   ├── models/              # Perspective output schemas
│   │   └── prompts/             # Lens-specific prompts
│   └── comparative/             # Benchmarking & scanning
│       ├── benchmarking.py      # Compare against top performers
│       └── contrarian_scanner.py # 6-dimension hidden gem detection
│
├── ai/                          # LLM integration
│   ├── providers/               # LLM provider implementations
│   │   ├── base.py              # Abstract LLMProvider
│   │   └── gemini.py            # Google Gemini implementation
│   ├── key_manager.py           # API key rotation (25+ keys)
│   ├── rate_limiter.py          # Request rate limiting
│   ├── request_queue.py         # Global cross-process request serialization
│   └── usage_tracker.py         # Persistent API usage tracking
│
├── data/                        # Data acquisition & storage
│   ├── sources/sec/             # SEC Edgar integration
│   │   ├── downloader.py        # Download 10-K/10-Q filings
│   │   ├── converter.py         # HTML → PDF conversion
│   │   ├── extractor.py         # PDF text extraction
│   │   └── rate_limiter.py      # SEC global rate limiter (NEW)
│   └── storage/                 # Data persistence
│       ├── json_store.py        # JSON storage backend
│       └── parquet_store.py     # Parquet storage (recommended for scale)
│
├── ui/                          # Streamlit web interface
│   ├── database/                # Data access layer
│   │   ├── repository.py        # DatabaseRepository (SQLite with retry/backup)
│   │   └── migrations/          # Schema migration files (v001-v012)
│   ├── services/                # Business logic
│   │   ├── analysis_service.py  # AnalysisService (main orchestrator)
│   │   ├── batch_queue.py       # Multi-day batch processing with monitoring
│   │   └── cancellation.py      # Analysis cancellation token system
│   └── components/              # Reusable UI components
│
├── cli/                         # Command-line interface
│   └── main.py                  # Click-based CLI
│
├── core/                        # Shared infrastructure
│   ├── config.py                # Pydantic configuration management
│   ├── exceptions.py            # Custom exception hierarchy
│   ├── logging.py               # Centralized logging with rotation
│   ├── monitoring.py            # Disk/process/health monitoring (NEW)
│   └── notifications.py         # Discord webhook notifications (NEW)
│
└── processing/                  # Parallel processing
    ├── pipeline.py              # Analysis pipeline orchestration
    ├── parallel.py              # ThreadPool worker management
    ├── progress.py              # Thread-safe progress tracking
    └── resume.py                # Resume interrupted analyses

custom_workflows/                # User-defined workflows (auto-discovered)
├── __init__.py                  # Auto-discovery mechanism
├── base.py                      # CustomWorkflow base class
└── examples/                    # Example workflows
    ├── growth_analyzer.py
    ├── moat_analyzer.py
    ├── risk_analyzer.py
    └── management_analyzer.py

pages/                           # Streamlit pages
├── 1_📊_Analysis.py             # Single/batch analysis
├── 2_📈_Analysis_History.py     # History and filtering
├── 3_🔍_Results_Viewer.py       # Results exploration
├── 4_🌙_Batch_Queue.py          # Multi-day batch processing
└── 5_⚙️_Settings.py             # Settings and database viewer

scripts/                         # Utility scripts
└── export_multi_analysis_to_csv.py  # Export results to CSV

streamlit_app.py                 # Home page / dashboard
```

---

## Configuration Reference

### Environment Variables

All settings are configured via `.env` file or environment variables:

#### Required Settings

| Variable                  | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `GOOGLE_API_KEY_1`        | Primary Google Gemini API key                  |
| `FINTEL_SEC_USER_EMAIL`   | Your email for SEC Edgar API (required by SEC) |
| `FINTEL_SEC_COMPANY_NAME` | Company/script name for SEC compliance         |

#### Optional API Keys

| Variable                                       | Description                             |
| ---------------------------------------------- | --------------------------------------- |
| `GOOGLE_API_KEY_2` through `GOOGLE_API_KEY_25` | Additional keys for parallel processing |

#### Processing Settings

| Variable                         | Default | Description                   |
| -------------------------------- | ------- | ----------------------------- |
| `FINTEL_NUM_WORKERS`             | 25      | Parallel worker count         |
| `FINTEL_NUM_FILINGS_PER_COMPANY` | 30      | Historical filings to process |
| `FINTEL_MAX_REQUESTS_PER_DAY`    | 500     | Rate limit per API key        |
| `FINTEL_SLEEP_AFTER_REQUEST`     | 65      | Seconds between API calls     |

#### AI Settings

| Variable                       | Default            | Description                    |
| ------------------------------ | ------------------ | ------------------------------ |
| `FINTEL_DEFAULT_MODEL`         | `gemini-2.5-flash` | LLM model to use               |
| `FINTEL_THINKING_BUDGET`       | 4096               | Thinking tokens for Gemini 2.x |
| `FINTEL_USE_STRUCTURED_OUTPUT` | true               | Use Pydantic structured output |

#### Storage Settings

| Variable                 | Default   | Description                    |
| ------------------------ | --------- | ------------------------------ |
| `FINTEL_DATA_DIR`        | `./data`  | Data storage directory         |
| `FINTEL_CACHE_DIR`       | `./cache` | Cache directory                |
| `FINTEL_LOG_DIR`         | `./logs`  | Log file directory             |
| `FINTEL_STORAGE_BACKEND` | parquet   | Storage: json, parquet, sqlite |

#### Logging Settings

| Variable                 | Default | Description                      |
| ------------------------ | ------- | -------------------------------- |
| `FINTEL_LOG_FILE`        | -       | Custom log file path             |
| `FINTEL_LOG_MAX_SIZE_MB` | 10      | Max log size before rotation     |
| `FINTEL_LOG_BACKUP_COUNT`| 5       | Number of backup logs to keep    |

#### Notification Settings

| Variable                     | Default | Description                        |
| ---------------------------- | ------- | ---------------------------------- |
| `FINTEL_DISCORD_WEBHOOK_URL` | -       | Discord webhook URL for alerts     |

#### Feature Flags

| Variable                          | Default | Description              |
| --------------------------------- | ------- | ------------------------ |
| `FINTEL_ENABLE_CACHING`           | true    | Cache API responses      |
| `FINTEL_ENABLE_PROGRESS_TRACKING` | true    | Enable resume capability |

---

## Architecture

### Design Principles

- **Type Safety** - Pydantic models throughout for reliable structured AI output
- **Concurrency** - SQLite WAL mode + ThreadPool for parallel batch processing
- **Extensibility** - Plugin-style custom workflows with auto-discovery
- **Resilience** - Automatic retry, rate limiting, and resume capability
- **Observability** - Discord notifications, log rotation, health monitoring

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ SEC Edgar   │────▶│ Download &   │────▶│ PDF Text    │
│ 10-K Filing │     │ Convert PDF  │     │ Extraction  │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Pydantic    │◀────│ Gemini AI    │◀────│ Prompt +    │
│ Validation  │     │ Analysis     │     │ Filing Text │
└─────────────┘     └──────────────┘     └─────────────┘
        │
        ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ SQLite      │────▶│ Streamlit    │────▶│ Discord     │
│ Storage     │     │ UI / Export  │     │ Alerts      │
└─────────────┘     └──────────────┘     └─────────────┘
```

### Key Components

| Component             | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `AnalysisService`     | Main orchestrator - coordinates all analysis operations     |
| `DatabaseRepository`  | Data access layer with retry logic and automatic backups    |
| `APIKeyManager`       | Rotates across 25+ API keys with usage tracking             |
| `GeminiProvider`      | LLM integration with structured output support              |
| `SECDownloader`       | Downloads filings from SEC Edgar with caching               |
| `SECRateLimiter`      | Cross-process rate limiting for SEC API compliance          |
| `CustomWorkflow`      | Base class for user-defined analysis workflows              |
| `RequestQueue`        | Cross-process API request serialization with file locking   |
| `BatchQueueService`   | Multi-day batch job management with health monitoring       |
| `NotificationService` | Discord webhook notifications for batch events              |
| `DiskMonitor`         | Monitors disk space and pauses when low                     |
| `ProcessMonitor`      | Cleans up orphaned Chrome processes                         |
| `HealthChecker`       | Comprehensive system health checks                          |
| `CancellationToken`   | Graceful analysis cancellation system                       |

---

## Technical Achievements

This project demonstrates several advanced engineering solutions:

### Cross-Process Rate Limiting

**Problem:** Parallel analyses across threads, processes, and simultaneous CLI/UI execution exceeded Gemini API rate limits (503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED).

**Solution:** File-based locking using `portalocker` that serializes all API requests across the entire system:

- Lock file at `data/api_usage/gemini_request.lock`
- Mandatory 65-second sleep between requests (Gemini requirement)
- Works across ThreadPool workers, ProcessPoolExecutor, and mixed execution modes
- Automatic cleanup on process crash
- Cross-platform compatible (Windows, macOS, Linux)

### Intelligent API Key Rotation

- **25+ API key support** with atomic reservation preventing collisions
- **Least-used strategy** for load balancing across keys
- **Persistent usage tracking** survives restarts via JSON files
- **Daily limit enforcement** per key with real-time availability checking
- **Thread-safe + Process-safe** operations using file locking

### Fault-Tolerant Batch Processing

- **Disk monitoring** - Preflight checks and periodic checks during processing
- **Chrome cleanup** - Automatic cleanup of orphaned browser processes
- **Database backups** - Daily automatic backups with retention policy
- **Thread-safe progress** - File-based locking for progress tracking
- **Exponential backoff** - Up to 10 retries with jitter for database operations
- **Discord notifications** - Real-time alerts for batch events
- **Resume capability** - Interrupted analyses continue from last completed year
- **Graceful cancellation** - Stop running analyses without data corruption

### Type-Safe AI Outputs

- **Pydantic v2 structured outputs** ensure 99%+ format consistency
- **Validation at extraction time** not post-processing
- **Custom exception hierarchy** for granular error handling
- **Schema enforcement** reduces hallucination and format errors

---

## Database Schema

Fintel uses SQLite with WAL mode for concurrent access. Schema is managed through migrations.

### Core Tables

| Table                        | Purpose                                             |
| ---------------------------- | --------------------------------------------------- |
| `analysis_runs`              | Tracks each analysis job (status, progress, config) |
| `analysis_results`           | Stores Pydantic model outputs as JSON               |
| `file_cache`                 | Caches downloaded SEC filings                       |
| `custom_prompts`             | User-created analysis prompts                       |
| `user_settings`              | User preferences (key-value)                        |
| `batch_jobs`                 | Batch queue job definitions                         |
| `batch_items`                | Individual items within batch jobs                  |
| `batch_item_year_checkpoints`| Per-year progress for resume capability             |

### Migrations

Located in `fintel/ui/database/migrations/`:

| Version | Description                                              |
| ------- | -------------------------------------------------------- |
| v001    | Initial schema (runs, results, prompts, cache, settings) |
| v002    | Progress tracking columns                                |
| v003    | Filing types cache                                       |
| v004    | Custom workflow support                                  |
| v005    | API usage tracking and indexes                           |
| v006    | Resume tracking (completed_years, last_activity)         |
| v007    | Batch queue and synthesis tables                         |
| v008    | CIK support for SEC lookups                              |
| v009    | Placeholder (gap filler)                                 |
| v010    | Synthesis checkpoints                                    |
| v011    | Batch year tracking                                      |
| v012    | Batch improvements (indexes, year checkpoints)           |

---

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fintel --cov-report=html

# Run specific test file
pytest tests/test_analyzer.py -v
```

### Code Quality

```bash
# Format code
black fintel/ pages/ custom_workflows/

# Lint
ruff check fintel/ --fix

# Type checking
mypy fintel/
```

### Adding a New Analysis Type

1. Create models in `fintel/analysis/<type>/models/`
2. Create prompts in `fintel/analysis/<type>/prompts/`
3. Implement analyzer in `fintel/analysis/<type>/analyzer.py`
4. Register in `AnalysisService._run_analysis_by_type()`
5. Add to UI dropdown in `pages/1_📊_Analysis.py`

### Adding a Custom Workflow

1. Create file in `custom_workflows/` (e.g., `my_workflow.py`)
2. Define Pydantic schema for output
3. Subclass `CustomWorkflow`
4. Implement `prompt_template` and `schema` properties
5. Restart app - workflow auto-discovers

---

## Troubleshooting

### Common Issues

**"No API key found"**

```bash
# Verify keys exist in .env
grep GOOGLE_API_KEY .env
```

**"Database locked"**

```bash
# Check database integrity
sqlite3 data/fintel.db "PRAGMA integrity_check;"

# If needed, close all connections and restart
```

**"SEC download failed"**

- Ensure `FINTEL_SEC_USER_EMAIL` is set (SEC requires this)
- SEC Edgar may rate limit during peak hours (try again later)
- Check logs in `logs/` directory for details

**"Rate limit exceeded"**

- Add more API keys (up to 25)
- Reduce `FINTEL_NUM_WORKERS`
- Increase `FINTEL_SLEEP_AFTER_REQUEST`

**"Analysis interrupted"**

- Go to Analysis History page
- Find interrupted runs in "Interrupted Analyses" section
- Click "Resume" to continue from last completed year

**"Low disk space" notifications**

- Fintel monitors disk space during batch processing
- Minimum 5GB free required, 10GB recommended
- Clean up old PDFs in `data/pdfs/` if needed

**"Discord notifications not working"**

- Verify `FINTEL_DISCORD_WEBHOOK_URL` is set correctly
- Test webhook manually: `curl -X POST -H "Content-Type: application/json" -d '{"content":"test"}' YOUR_WEBHOOK_URL`
- Check logs for "Discord webhook" errors

### Logs

Logs are stored in `logs/` directory:

- `fintel.log` - Main application log
- Automatic rotation at 10MB with 5 backup files

---

## Technology Stack

| Layer          | Technologies                                       |
| -------------- | -------------------------------------------------- |
| **Web UI**     | Streamlit 1.30+, Pandas, Polars                    |
| **LLM**        | Google Gemini API, Pydantic 2.0+ structured output |
| **Data**       | PyPDF2, Selenium + Chrome, SEC Edgar API           |
| **Storage**    | SQLite (WAL mode), JSON, Parquet                   |
| **CLI**        | Click, Rich                                        |
| **Processing** | ThreadPool, concurrent.futures, portalocker        |
| **Config**     | Pydantic Settings, python-dotenv                   |
| **Monitoring** | psutil (optional), shutil, urllib                  |

---

## Requirements

- Python 3.10+
- Google Chrome (for HTML → PDF conversion)
- Google Gemini API key(s)
- 4GB+ RAM recommended for batch processing
- 10GB+ free disk space for large batch runs
- psutil (optional, for memory monitoring and Chrome cleanup)

---

## License

Private - For personal use only.

---

## Disclaimer

This platform is for research and educational purposes only. The analysis results are AI-generated and should not be considered financial advice. Always conduct your own due diligence and consult with qualified financial professionals before making investment decisions.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Documentation

- [Custom Workflows Guide](docs/CUSTOM_WORKFLOWS.md) - Complete developer documentation
- [Contributing Guide](CONTRIBUTING.md) - Development setup and contribution guidelines
