<p align="center">
    <picture>
    <img src="https://github.com/gkgeo9/eon/blob/main/logo.png?raw=true" alt="" width="500">
  </picture>
</p>

<p align="center">
  <picture>
    <img src="https://github.com/gkgeo9/eon/blob/main/watermark.png?raw=true" alt="" width="900">
  </picture>
</p>

# Erebus Observatory Network (EON)

**AI-Powered SEC Filing Analysis Platform for Investment Research**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)](https://streamlit.io/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![38K+ Lines](https://img.shields.io/badge/codebase-38%2C000%2B_lines-brightgreen.svg)](#codebase-statistics)
[![158 Modules](https://img.shields.io/badge/modules-158-orange.svg)](#codebase-statistics)

---

## Overview

**Erebus Observatory Network (EON)** is a production-grade platform that transforms raw SEC filings into structured, actionable investment intelligence using AI. Feed it a ticker symbol and EON will download filings from SEC Edgar, convert them to machine-readable text, run them through multiple AI-powered investment analysis frameworks, and deliver type-safe, validated results through a web dashboard or CLI.

The platform applies three distinct investment philosophies simultaneously:

- **Warren Buffett's Value Investing** -- Economic moat analysis, management quality scoring, ROIC calculations, intrinsic value estimation
- **Nassim Taleb's Antifragility Framework** -- Fragility assessment, black swan scenario modeling, optionality detection, Lindy effect evaluation
- **Contrarian Opportunity Detection** -- Variant perception identification, consensus challenge, hidden strengths/weaknesses, second-order effects

### Why EON?

| Capability | What It Means |
|---|---|
| **Multi-Perspective Analysis** | See companies through 3+ investment lenses simultaneously, not just one |
| **Type-Safe AI Output** | Every AI response is validated against Pydantic schemas -- no malformed data |
| **1000+ Company Scale** | Batch-process entire market sectors over multi-day runs with automatic recovery |
| **25-Key Parallel Processing** | Distribute load across 25+ API keys with atomic reservation and adaptive throttling |
| **Plugin Workflows** | Create custom analysis prompts in a single Python file -- auto-discovered, no core changes |
| **Crash-Resistant Resume** | Interrupted at year 7 of 10? Resume picks up at year 8, not from scratch |
| **Cross-Process Rate Limiting** | File-based locking coordinates API access across threads, processes, and concurrent CLI/UI sessions |
| **Real-Time Monitoring** | Discord notifications, disk/memory monitoring, health checks, log rotation |

---

## How It Works

```
                                  EON Pipeline
                                  ============

  ┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
  │  SEC Edgar   │──────>│  Download & Cache │──────>│  HTML → PDF      │
  │  EDGAR API   │       │  (rate-limited)   │       │  (Selenium/CDP)  │
  └──────────────┘       └──────────────────┘       └──────────────────┘
                                                            │
                                                            v
  ┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
  │  Pydantic    │<──────│  Google Gemini    │<──────│  PDF → Text      │
  │  Validation  │       │  Structured Gen   │       │  (PyPDF2)        │
  └──────────────┘       └──────────────────┘       └──────────────────┘
         │                                                  ^
         │            ┌─────────────────────┐               │
         │            │  API Key Manager    │───────────────┘
         │            │  (25-key rotation,  │
         │            │   adaptive sleep,   │
         │            │   file-based locks) │
         │            └─────────────────────┘
         v
  ┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
  │  SQLite DB   │──────>│  Streamlit UI    │──────>│  Discord Alerts  │
  │  (WAL mode)  │       │  + CLI Export     │       │  (webhooks)      │
  └──────────────┘       └──────────────────┘       └──────────────────┘
```

**Each filing goes through a 4-stage pipeline:**

1. **Acquire** -- Download SEC filings via EDGAR API with cross-process rate limiting and intelligent caching
2. **Transform** -- Convert HTML filings to PDF via headless Chrome (CDP protocol), then extract text with PyPDF2
3. **Analyze** -- Send extracted text + investment-philosophy prompt to Google Gemini with Pydantic schema enforcement
4. **Store & Present** -- Validate output against typed schemas, persist to SQLite/JSON/Parquet, render in Streamlit or export via CLI

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/gkgeo9/eon.git
cd eon

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dependencies
pip install -e ".[dev]"
```

### 2. Configuration

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
EON_SEC_USER_EMAIL=your@email.com
EON_SEC_COMPANY_NAME="Investment Research"

# Optional: Discord notifications for batch processing
EON_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

### 3. Launch

**Web Interface (Recommended):**

```bash
# Default (localhost:8501)
eon web

# Custom port
eon web --port 8080

# Allow external connections
eon web --host 0.0.0.0
```

Opens at `http://localhost:8501`

**Command Line:**

```bash
# Single company analysis
eon analyze AAPL --years 5

# Batch processing from CSV
eon batch tickers.csv --workers 10
```

---

## Analysis Types

### Built-in Investment Perspectives

| Type | Description | Min Years | Best For |
|---|---|---|---|
| **Fundamental** | Business model, financials, risks, competitive position | 1 | Initial company research |
| **Buffett Lens** | Economic moat (5 sources), management quality, ROIC trends, intrinsic value | 1 | Value investing |
| **Taleb Lens** | Fragility scoring, black swan scenarios, optionality, Lindy effect | 1 | Risk management |
| **Contrarian Lens** | Variant perception, consensus challenge, hidden strengths/weaknesses | 1 | Alpha generation |
| **Multi-Perspective** | Combined Buffett + Taleb + Contrarian with synthesis verdict | 1 | Comprehensive view |
| **Excellent Company** | Success factor extraction from proven multi-year winners | 3 | Pattern recognition |
| **Objective Analysis** | Unbiased success/failure factor identification | 3 | Screening |
| **Contrarian Scanner** | 6-dimension hidden compounder scoring (0-600 scale) | 3 | Finding hidden gems |

### Contrarian Scanner: 6-Dimension Alpha Score

The scanner evaluates companies on six proprietary dimensions, each scored 0-100:

| Dimension | What It Detects | High Score Means |
|---|---|---|
| **Strategic Anomaly** | Bold, counterintuitive strategic moves | Company is defying industry playbook with logic |
| **Asymmetric Resources** | Concentrated capital allocation bets | All-in bet on transformative opportunity (25-50%+ of resources) |
| **Contrarian Positioning** | Inverse positioning to industry consensus | Clear opposite strategy to industry orthodoxy |
| **Cross-Industry DNA** | Foreign practices from other industries | Operating like a fundamentally different industry |
| **Early Infrastructure** | Building for future scale before needed | Creating infrastructure for markets that don't yet exist |
| **Intellectual Capital** | Undervalued patents, IP, and know-how | Game-changing IP completely unrecognized by market |

**Composite Alpha Score: 0-600.** Most companies score 120-300. Scores above 400 indicate exceptional contrarian potential.

### Investment Philosophy Deep-Dives

**Buffett Lens** evaluates five moat sources (Brand Power, Network Effects, Switching Costs, Cost Advantage, Regulatory Moat) with quantitative proof requirements. It calculates ROIC over 5 years (`NOPAT / (Debt + Equity - Cash)`), grades management capital allocation A-F, and estimates intrinsic value using 8-12x normalized owner earnings with a 30%+ margin of safety requirement.

**Taleb Lens** computes a fragility score based on Debt/EBITDA (>3x = fragile), fixed cost ratio, customer concentration (>10% = dependency), and cash runway. It generates 5-7 specific black swan scenarios with probability/impact ratings, evaluates optionality (asymmetric upside), and applies the Lindy Effect (time-tested business models survive longer).

**Contrarian Lens** maps the consensus narrative, then systematically challenges it with 3-5 data-backed reasons. It identifies misunderstood metrics (what the market watches vs. what matters), traces second-order effects (if X then Y then Z), and constructs a variant perception thesis with conviction level.

---

## Custom Workflows

Create your own analysis workflows by adding Python files to `custom_workflows/`. They're automatically discovered and appear in the UI -- no core code changes needed.

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

### Included Example Workflows

| Workflow | Focus | File |
|---|---|---|
| **Growth Analyzer** | Revenue growth patterns, CAGR, sustainability | `examples/growth_analyzer.py` |
| **Moat Analyzer** | Competitive advantage depth and durability | `examples/moat_analyzer.py` |
| **Risk Analyzer** | Risk factor identification and scoring | `examples/risk_analyzer.py` |
| **Management Analyzer** | Leadership quality and capital allocation | `examples/management_analyzer.py` |
| **Moonshot Analyzer** | Asymmetric upside / high-risk opportunities | `examples/moonshot_analyzer.py` |
| **Option Analyzer** | Options-thinking and embedded optionality | `examples/option_analyzer.py` |

The `CustomWorkflow` base class validates your workflow at load time -- checking for required `{ticker}` and `{year}` placeholders, Pydantic schema correctness, field descriptions, and prompt length. Validation errors include actionable suggestions.

See [docs/CUSTOM_WORKFLOWS.md](docs/CUSTOM_WORKFLOWS.md) for the complete developer guide.

---

## Batch Processing

EON is designed for large-scale, multi-day batch analysis of 1000+ companies.

### Running Large Batches

```bash
# Start in tmux/screen for persistence
tmux new -s eon-batch

# 1000 companies, 10 years each, multi-perspective analysis
eon batch companies.csv --years 10 --analysis-type multi

# Detach: Ctrl+B then D
# Reattach later: tmux attach -t eon-batch

# If interrupted, resume from where it left off
eon batch --resume

# Resume a specific batch
eon batch --resume-id <batch_id>

# List all incomplete batches
eon batch --list-incomplete
```

### CSV Input Format

```csv
ticker,company_name
AAPL,Apple Inc.
MSFT,Microsoft Corporation
GOOGL,Alphabet Inc.
```

### Capacity Planning

| Companies | Years | API Requests | Est. Duration (25 keys) |
|---|---|---|---|
| 10 | 7 | 70 | < 1 day |
| 100 | 7 | 700 | ~1.5 days |
| 500 | 10 | 5,000 | ~10 days |
| 1,000 | 7 | 7,000 | ~14 days |
| 1,000 | 10 | 10,000 | ~20 days |

**Throughput:** 25 API keys x 20 requests/key/day = **500 requests/day**

### How It Works Internally

```
1. Create batch job → tickers + config stored in SQLite
2. ThreadPoolExecutor starts N workers (up to 25, one per API key)
3. Each worker:
   a. Atomically reserves an API key (no collisions via threading.Condition)
   b. Downloads SEC filings with staggered starts (prevents thundering herd)
   c. Converts HTML → PDF via headless Chrome (CDP protocol)
   d. Extracts text with PyPDF2
   e. Sends text + prompt to Gemini AI
   f. Validates response against Pydantic schema
   g. Stores result in SQLite immediately (per-year checkpoint)
   h. Releases API key → picks up next company
4. When all keys hit daily limit → waits for midnight PST reset
5. Adaptive sleep: reduces from 65s to ~40s after 5 consecutive successes
6. On 429 errors: increases sleep by 50% (65s → 97.5s)
7. Completed companies are never re-processed on resume
```

### Reliability Features

| Feature | Description |
|---|---|
| **Per-Year Resume** | Results saved after each year. Interrupted at year 7/10 → resumes at year 8 |
| **Adaptive Rate Limiting** | Sleep decreases on success, increases on 429s. Learns API behavior |
| **Disk Space Monitoring** | Preflight check (10GB recommended) + periodic monitoring during runs |
| **Chrome Process Cleanup** | Demand-based cleanup triggered by memory pressure (>80%) |
| **Database Backups** | Daily automatic backups with 7-day retention policy |
| **Exponential Backoff** | Up to 10 retries with jitter for database operations |
| **Priority Ordering** | `--priority` flag processes important tickers first |
| **Ticker Deduplication** | Duplicate tickers in CSV automatically removed with logging |
| **Graceful Cancellation** | Stop running analyses without data corruption |

### Error Handling at Scale

| Error Type | Behavior |
|---|---|
| **Context length exceeded** | Company marked as SKIPPED (filing too large for model context) |
| **API quota exhausted** | All workers pause, wait for midnight PST reset, then auto-resume |
| **Rate limit (429)** | Unlimited retries, parses `retryDelay` from API response, adds buffer |
| **Transient (500/502/503)** | Up to 3 retries with exponential backoff + jitter |
| **Network error** | Retried up to max_retries (default 2) |
| **Process crash** | Resume picks up from last completed year (not company) |

---

## Web Interface

### Pages

| Page | Purpose |
|---|---|
| **Home** | Dashboard with metrics, recent analyses, quick actions |
| **Analysis** | Run single or batch company analysis with all configuration options |
| **Analysis History** | Search, filter, and manage past analyses |
| **Results Viewer** | Explore results in formatted or raw JSON view, export |
| **Batch Queue** | Multi-day batch processing with real-time progress monitoring |
| **Settings** | API usage stats, database viewer, custom prompts, cache management |

---

## CLI Reference

```bash
# Analyze a single company
eon analyze AAPL --years 5 --type fundamental

# Analyze with specific years
eon analyze MSFT --years 2020 2021 2022 2023

# Batch process from file
eon batch tickers.csv --workers 10 --type buffett

# Contrarian scan with minimum score filter
eon scan --tickers-file universe.txt --min-score 400

# Export results
eon export --format csv --output results.csv

# Export from a specific batch run
eon export --batch-id abc12345 --output batch_results.csv

# Export only completed items
eon export --batch-id abc12345 --status-filter completed --output completed.csv

# Launch web interface
eon web --port 8501
```

| Command | Key Options | Description |
|---|---|---|
| `analyze` | `--years`, `--type`, `--filing` | Single company analysis |
| `batch` | `--years`, `--type`, `--priority`, `--resume` | Multi-day batch processing |
| `scan` | `--min-score`, `--tickers-file` | Contrarian opportunity scanning |
| `export` | `--format`, `--output`, `--batch-id`, `--status-filter` | Export results to CSV/Excel/Parquet |
| `web` | `--port`, `--host` | Launch Streamlit web interface |

---

## Discord Notifications

Real-time alerts for batch processing events. Recommended for overnight runs.

| Event | Embed Color | Description |
|---|---|---|
| **Batch Completed** | Green | Summary with completed/failed counts and duration |
| **Batch Failed** | Red | Error details and batch ID |
| **Keys Exhausted** | Orange | All keys hit daily limit, waiting for midnight reset |
| **Warning** | Yellow | Low disk space, high memory, Chrome cleanup triggered |
| **Progress** | Blue | Unicode progress bar, ETA, completion count |

### Setup

1. Create a Discord webhook (Server Settings → Integrations → Webhooks)
2. Add to `.env`: `EON_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`
3. Test: `python -c "from eon.core.notifications import NotificationService; NotificationService().send_info('Test')"`

---

## Architecture

### Design Principles

| Principle | Implementation |
|---|---|
| **Type Safety** | Pydantic v2 models for all AI outputs, config, and data transfer objects |
| **Concurrency** | SQLite WAL mode + ThreadPool + file-based locking for parallel processing |
| **Extensibility** | Plugin-style custom workflows with auto-discovery + Protocol-based DI |
| **Resilience** | Adaptive retry, rate limiting, resume, graceful cancellation, health monitoring |
| **Observability** | Discord notifications, structured logging with rotation, health checks |
| **Explicit Errors** | Custom exception hierarchy + `Result[T]` types prevent silent failures |

### Three-Layer Concurrency Control

The system uses three independent concurrency mechanisms to coordinate API access:

```
Layer 1: Global Semaphore (GeminiRequestQueue)
  └─ Limits total concurrent API requests to MAX_CONCURRENT (default: 25)

Layer 2: Per-Key File Locks (GeminiRequestQueue)
  └─ portalocker.LOCK_EX on data/api_usage/gemini_request_{hash}.lock
  └─ Prevents the same API key from being used concurrently

Layer 3: Atomic Key Reservation (APIUsageTracker)
  └─ threading.Condition() for thread-safe reserve/release
  └─ Persistent JSON files for cross-process tracking
  └─ Survives restarts and process crashes
```

This allows N keys to process N requests in parallel while ensuring no key is ever double-used. The same pattern applies separately to SEC Edgar API access.

### Key Components

| Component | Module | Purpose |
|---|---|---|
| `FundamentalAnalyzer` | `eon.analysis.fundamental` | 10-K analysis with 3-stage pipeline (extract → prompt → AI) |
| `PerspectiveAnalyzer` | `eon.analysis.perspectives` | Buffett/Taleb/Contrarian investment lens analysis |
| `ContrarianScanner` | `eon.analysis.comparative` | 6-dimension alpha scoring for hidden gem detection |
| `AnalysisRunner` | `eon.analysis.runner` | Generic year-by-year execution with progress tracking |
| `GeminiProvider` | `eon.ai.providers.gemini` | Gemini API with structured output, retry, adaptive sleep |
| `APIKeyManager` | `eon.ai.key_manager` | 25+ key rotation with least-used strategy |
| `GeminiRequestQueue` | `eon.ai.request_queue` | Cross-process request serialization with adaptive throttling |
| `APIUsageTracker` | `eon.ai.usage_tracker` | Persistent per-key usage tracking with atomic file writes |
| `SECDownloader` | `eon.data.sources.sec` | SEC Edgar download with ticker + CIK support |
| `SECConverter` | `eon.data.sources.sec` | HTML → PDF conversion via headless Chrome CDP |
| `PDFExtractor` | `eon.data.sources.sec` | PDF text extraction with chunking for large files |
| `DatabaseRepository` | `eon.ui.database` | SQLite DAL with retry, backup, WAL mode |
| `BatchQueueService` | `eon.ui.services` | Multi-day batch orchestration with health monitoring |
| `AnalysisService` | `eon.ui.services` | Main orchestrator coordinating all analysis operations |
| `CancellationToken` | `eon.ui.services` | Thread-safe cooperative cancellation system |
| `NotificationService` | `eon.core.notifications` | Discord webhook notifications with rich embeds |
| `HealthChecker` | `eon.core.monitoring` | Disk, memory, and process health monitoring |
| `ParallelProcessor` | `eon.processing` | ProcessPoolExecutor orchestration with staggered starts |
| `ProgressTracker` | `eon.processing` | File-based progress tracking with cross-process locking |
| `CustomWorkflow` | `custom_workflows.base` | Abstract base for plugin analysis workflows |

---

## Project Structure

```
eon/
├── analysis/                        # Core analysis engines (31 files)
│   ├── runner.py                    # Generic year-by-year analysis runner
│   ├── fundamental/                 # 10-K fundamental analysis
│   │   ├── analyzer.py              # FundamentalAnalyzer (3-stage pipeline)
│   │   ├── success_factors.py       # ExcellentCompanyAnalyzer, ObjectiveCompanyAnalyzer
│   │   ├── schemas.py               # TenKAnalysis Pydantic schema
│   │   ├── models/                  # Output schemas (basic, success_factors, excellent)
│   │   └── prompts/                 # Prompt templates per analysis type
│   ├── perspectives/                # Investment philosophy analyzers
│   │   ├── analyzer.py              # PerspectiveAnalyzer (Buffett, Taleb, Contrarian)
│   │   ├── schemas.py               # BuffettAnalysis, TalebAnalysis, ContrarianAnalysis
│   │   └── prompts/                 # Per-lens prompts (buffett, taleb, contrarian, combined)
│   └── comparative/                 # Benchmarking and scanning
│       ├── benchmarking.py          # Compounder DNA comparison
│       ├── contrarian_scanner.py    # 6-dimension alpha scoring
│       └── models/                  # ContrarianScores, BenchmarkComparison schemas
│
├── ai/                              # LLM integration layer (13 files, ~2,300 LOC)
│   ├── providers/
│   │   ├── base.py                  # Abstract LLMProvider interface
│   │   └── gemini.py                # Google Gemini: structured output, retry, error handling
│   ├── key_manager.py               # 25+ key rotation with atomic reservation
│   ├── rate_limiter.py              # Mandatory sleep enforcement with timezone-aware quotas
│   ├── request_queue.py             # Cross-process serialization with adaptive throttling
│   ├── usage_tracker.py             # Persistent per-key tracking (673 lines, the most complex)
│   ├── api_config.py                # APILimits, SECLimits frozen dataclasses
│   └── prompts/                     # All prompt templates (fundamental, perspectives, comparative)
│
├── data/                            # Data acquisition and storage (14 files, ~3,400 LOC)
│   ├── corpus.py                    # Intelligent filing cache with freshness detection
│   ├── sources/sec/
│   │   ├── downloader.py            # SEC Edgar API (ticker + CIK support, 839 lines)
│   │   ├── converter.py             # HTML → PDF via Selenium/Chrome CDP with retry
│   │   ├── extractor.py             # PDF text extraction with chunking
│   │   ├── request_queue.py         # SEC-specific cross-process rate limiting
│   │   └── rate_limiter.py          # SEC global rate limiter (8 req/sec, under 10 limit)
│   └── storage/
│       ├── base.py                  # Abstract StorageBackend
│       ├── json_store.py            # Human-readable JSON storage
│       ├── parquet_store.py         # Columnar Parquet with partitioning (10-100x compression)
│       └── exporter.py              # Multi-format export (CSV, Excel, Parquet)
│
├── core/                            # Shared infrastructure (11 files, ~2,400 LOC)
│   ├── config.py                    # EonConfig (Pydantic Settings, thread-safe singleton)
│   ├── exceptions.py                # 11-type exception hierarchy
│   ├── interfaces.py                # 6 Protocol definitions for dependency injection
│   ├── logging.py                   # Centralized logging with rotation (10MB, 5 backups)
│   ├── monitoring.py                # DiskMonitor, ProcessMonitor, HealthChecker
│   ├── notifications.py             # Discord webhook service with rich embeds
│   ├── analysis_types.py            # Central registry of 8 built-in analysis types
│   ├── formatting.py                # Shared status/duration formatting
│   ├── result.py                    # Result[T] and BatchResult[T] types
│   └── utils.py                     # Filing type classifications (annual/quarterly/event)
│
├── ui/                              # Streamlit web interface
│   ├── database/
│   │   ├── repository.py            # DatabaseRepository with retry and auto-backup
│   │   └── migrations/              # 12 SQL migration files (v001-v012)
│   ├── services/
│   │   ├── analysis_service.py      # Main analysis orchestrator
│   │   ├── batch_queue.py           # Multi-day batch processing with health monitoring
│   │   └── cancellation.py          # Thread-safe cooperative cancellation system
│   └── components/                  # Reusable Streamlit UI components
│
├── cli/                             # Command-line interface
│   └── main.py                      # Click-based CLI (analyze, batch, scan, export, web)
│
└── processing/                      # Parallel processing
    ├── parallel.py                  # ProcessPoolExecutor with staggered worker starts
    └── progress.py                  # File-based progress tracking with cross-process locking

custom_workflows/                    # User-defined workflows (auto-discovered)
├── base.py                          # CustomWorkflow ABC with validation
└── examples/                        # 6 example workflows
    ├── growth_analyzer.py           # Revenue growth patterns and sustainability
    ├── moat_analyzer.py             # Competitive advantage analysis
    ├── risk_analyzer.py             # Risk factor scoring
    ├── management_analyzer.py       # Leadership quality assessment
    ├── moonshot_analyzer.py         # Asymmetric upside detection
    └── option_analyzer.py           # Embedded optionality analysis

pages/                               # Streamlit pages
├── 1_📊_Analysis.py                 # Single/batch analysis (953 lines)
├── 2_📈_Analysis_History.py         # History, filtering, resume
├── 3_🔍_Results_Viewer.py           # Results exploration and export
├── 4_🌙_Batch_Queue.py              # Multi-day batch management
└── 5_⚙️_Settings.py                 # API usage, database, cache

streamlit_app.py                     # Home page / dashboard
```

---

## Codebase Statistics

| Metric | Value |
|---|---|
| **Total Python files** | 158 |
| **Total lines of code** | 38,000+ |
| **SQL migration files** | 14 (509 lines) |
| **Test files** | 17 |
| **Built-in analysis types** | 8 |
| **Example custom workflows** | 6 |
| **Pydantic models** | 30+ |
| **Protocol interfaces** | 6 |
| **Exception types** | 11 |
| **Database tables** | 8 |
| **Database migrations** | 12 versions |
| **Dependencies** | 20 production + 7 dev |

---

## Configuration Reference

All settings via `.env` file or environment variables:

### Required

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY_1` | Primary Google Gemini API key |
| `EON_SEC_USER_EMAIL` | Your email for SEC Edgar API (required by SEC) |
| `EON_SEC_COMPANY_NAME` | Company/project name for SEC compliance |

### API Keys (Optional)

`GOOGLE_API_KEY_2` through `GOOGLE_API_KEY_25` -- more keys = faster parallel processing.

### Processing

| Variable | Default | Description |
|---|---|---|
| `EON_NUM_WORKERS` | 25 | Parallel worker count (1-100) |
| `EON_NUM_FILINGS_PER_COMPANY` | 30 | Historical filings to process (1-50) |
| `EON_MAX_REQUESTS_PER_DAY` | 500 | Daily rate limit per API key |
| `EON_SLEEP_AFTER_REQUEST` | 65 | Seconds between API calls |

### AI

| Variable | Default | Description |
|---|---|---|
| `EON_DEFAULT_MODEL` | `gemini-2.5-flash` | LLM model to use |
| `EON_THINKING_BUDGET` | 4096 | Thinking tokens for Gemini 2.x |
| `EON_USE_STRUCTURED_OUTPUT` | true | Enforce Pydantic structured output |

### Storage

| Variable | Default | Description |
|---|---|---|
| `EON_DATA_DIR` | `./data` | Data storage directory |
| `EON_CACHE_DIR` | `./cache` | Cache directory |
| `EON_LOG_DIR` | `./logs` | Log file directory |
| `EON_STORAGE_BACKEND` | parquet | Backend: json, parquet, sqlite |

### Logging

| Variable | Default | Description |
|---|---|---|
| `EON_LOG_FILE` | - | Custom log file path |
| `EON_LOG_MAX_SIZE_MB` | 10 | Max log size before rotation |
| `EON_LOG_BACKUP_COUNT` | 5 | Number of backup logs to keep |

### Notifications

| Variable | Default | Description |
|---|---|---|
| `EON_DISCORD_WEBHOOK_URL` | - | Discord webhook URL for alerts |
| `EON_DISCORD_PROGRESS_INTERVAL` | 0 | Progress notification interval (0-100%, 0 disables) |

### Feature Flags

| Variable | Default | Description |
|---|---|---|
| `EON_ENABLE_CACHING` | true | Cache API responses |
| `EON_ENABLE_PROGRESS_TRACKING` | true | Enable resume capability |

---

## Database

SQLite with WAL mode for concurrent access. Schema managed through idempotent migrations.

### Tables

| Table | Purpose |
|---|---|
| `analysis_runs` | Tracks each analysis job (status, progress, config) |
| `analysis_results` | Stores validated Pydantic model outputs as JSON |
| `file_cache` | Caches downloaded SEC filing paths |
| `custom_prompts` | User-created analysis prompts |
| `user_settings` | User preferences (key-value store) |
| `batch_jobs` | Batch queue job definitions |
| `batch_items` | Individual items within batch jobs |
| `batch_item_year_checkpoints` | Per-year progress for resume capability |

### Migrations (v001-v012)

Located in `eon/ui/database/migrations/`. Each migration uses `IF NOT EXISTS` for idempotent execution. Applied automatically on startup.

---

## Development

### Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

### Testing

```bash
pytest                              # Run all tests (with coverage)
pytest --cov=eon --cov-report=html  # HTML coverage report
pytest tests/test_batch_queue.py -v # Specific file
pytest -k "test_rate_limiting"      # Pattern match
```

### Code Quality

```bash
black eon/ pages/ custom_workflows/    # Format (line-length: 100)
ruff check eon/ --fix                  # Lint
mypy eon/                              # Type check
```

### Adding a New Analysis Type

1. Create models in `eon/analysis/<type>/models/`
2. Create prompts in `eon/analysis/<type>/prompts/`
3. Implement analyzer in `eon/analysis/<type>/analyzer.py`
4. Register in `AnalysisService._run_analysis_by_type()`
5. Add to UI dropdown in `pages/1_📊_Analysis.py`

### Adding a Custom Workflow

1. Create file in `custom_workflows/examples/` (e.g., `my_workflow.py`)
2. Define Pydantic schema for output
3. Subclass `CustomWorkflow`
4. Implement `prompt_template` and `schema` properties
5. Restart app -- workflow auto-discovers

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **"No API key found"** | Verify `GOOGLE_API_KEY_1` is set in `.env` |
| **"Database locked"** | Run `sqlite3 data/eon.db "PRAGMA integrity_check;"`, restart if needed |
| **"SEC download failed"** | Ensure `EON_SEC_USER_EMAIL` is set. SEC may rate-limit during peak hours |
| **"Rate limit exceeded"** | Add more API keys, reduce `EON_NUM_WORKERS`, or increase `EON_SLEEP_AFTER_REQUEST` |
| **"Analysis interrupted"** | Go to Analysis History page → find interrupted run → click "Resume" |
| **"Low disk space"** | EON requires 5GB minimum, 10GB recommended. Clean `data/pdfs/` if needed |
| **"Discord not working"** | Verify webhook URL. Test: `curl -X POST -H "Content-Type: application/json" -d '{"content":"test"}' $URL` |

### Logs

Stored in `logs/` directory. Main log: `eon.log`. Automatic rotation at 10MB with 5 backups.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Language** | Python 3.10+ (fully typed) |
| **Web UI** | Streamlit 1.30+, Pandas, Polars |
| **LLM** | Google Gemini API via `google-genai`, Pydantic v2 structured output |
| **Data Acquisition** | SEC Edgar API, `sec-edgar-downloader`, Selenium + Chrome CDP |
| **PDF Processing** | PyPDF2 (extraction), Chrome DevTools Protocol (HTML → PDF) |
| **Storage** | SQLite (WAL mode), JSON, Apache Parquet (via PyArrow) |
| **CLI** | Click, Rich, tqdm |
| **Concurrency** | ThreadPoolExecutor, ProcessPoolExecutor, portalocker (file locks) |
| **Config** | Pydantic Settings, python-dotenv |
| **Monitoring** | psutil (optional), Discord webhooks, structured logging |
| **Market Data** | yfinance |

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
- [Project Showcase](PROJECT_SHOWCASE.md) - Technical deep-dive and engineering highlights
- [Contributing Guide](CONTRIBUTING.md) - Development setup and contribution guidelines
