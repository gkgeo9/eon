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
- **Scalable Processing** - Analyze hundreds of companies in parallel with 25+ API key rotation
- **Extensible Workflows** - Create custom analysis prompts without modifying core code
- **Resume Capability** - Interrupted analyses can be resumed from where they left off
- **Document Caching** - Downloaded SEC filings are cached to avoid redundant downloads

---

## Key Features

| Feature                         | Description                                       |
| ------------------------------- | ------------------------------------------------- |
| **Multi-Perspective Analysis**  | Buffett, Taleb, and Contrarian investment lenses  |
| **Custom Workflows**            | Auto-discovered Python-based analysis workflows   |
| **Batch Processing**            | Analyze 1-1000+ companies in parallel             |
| **Contrarian Scanner**          | 6-dimension hidden gem scoring (0-600 scale)      |
| **Compounder DNA**              | Compare against top 50 proven performers          |
| **Resume Support**              | Continue interrupted analyses automatically       |
| **API Key Rotation**            | Distribute load across 25+ Gemini API keys        |
| **Web + CLI**                   | Both Streamlit UI and command-line interface      |
| **Batch Queue**                 | Multi-day batch processing with progress tracking |
| **Analysis Cancellation**       | Cancel running analyses gracefully                |
| **Cross-Process Rate Limiting** | File-based locking prevents API quota errors      |

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
```

### 3. Launch

**Web Interface (Recommended):**

```bash
streamlit run streamlit_app.py

mac

/Users/gkg/PycharmProjects/Fintel/.venv/bin/python -m streamlit run /Users/gkg/PycharmProjects/Fintel/streamlit_app.py

windows

.venv\Scripts\python -m streamlit run streamlit_app.py


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

## Web Interface

### Pages

| Page                 | Purpose                                                |
| -------------------- | ------------------------------------------------------ |
| **Home**             | Dashboard with metrics, recent analyses, quick actions |
| **Analysis**         | Run single or batch company analysis with all options  |
| **Analysis History** | Search, filter, and manage past analyses               |
| **Results Viewer**   | Explore results in formatted or JSON view, export      |
| **Settings**         | API usage, database viewer, custom prompts, cache      |
| **Batch Queue**      | Multi-day batch processing with rate limit monitoring  |

### Screenshots

**Home Dashboard:**

- Total analyses count
- Currently running analyses
- Today's analysis count
- Unique tickers analyzed
- Recent analyses table with status

**Analysis Page:**

- Single or batch mode toggle
- Ticker input with company name
- Analysis type dropdown (including custom workflows)
- Filing type auto-discovery
- Year selection options
- Real-time progress monitoring

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
│   │   └── extractor.py         # PDF text extraction
│   └── storage/                 # Data persistence
│       ├── json_store.py        # JSON storage backend
│       └── parquet_store.py     # Parquet storage (recommended for scale)
│
├── ui/                          # Streamlit web interface
│   ├── database/                # Data access layer
│   │   ├── repository.py        # DatabaseRepository (SQLite)
│   │   └── migrations/          # Schema migration files (v001-v010)
│   ├── services/                # Business logic
│   │   ├── analysis_service.py  # AnalysisService (main orchestrator)
│   │   ├── batch_queue.py       # Multi-day batch processing service
│   │   └── cancellation.py      # Analysis cancellation token system
│   └── components/              # Reusable UI components
│
├── cli/                         # Command-line interface
│   └── main.py                  # Click-based CLI
│
├── core/                        # Shared infrastructure
│   ├── config.py                # Pydantic configuration management
│   ├── exceptions.py            # Custom exception hierarchy
│   └── logging.py               # Centralized logging
│
└── processing/                  # Parallel processing
    ├── pipeline.py              # Analysis pipeline orchestration
    ├── parallel.py              # ThreadPool worker management
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
├── 5_⚙️_Settings.py             # Settings and database viewer
└── 5_🌙_Batch_Queue.py          # Multi-day batch processing

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
┌─────────────┐     ┌──────────────┐
│ SQLite      │────▶│ Streamlit    │
│ Storage     │     │ UI / Export  │
└─────────────┘     └──────────────┘
```

### Key Components

| Component            | Purpose                                                    |
| -------------------- | ---------------------------------------------------------- |
| `AnalysisService`    | Main orchestrator - coordinates all analysis operations    |
| `DatabaseRepository` | Data access layer with retry logic and concurrency support |
| `APIKeyManager`      | Rotates across 25+ API keys with usage tracking            |
| `GeminiProvider`     | LLM integration with structured output support             |
| `SECDownloader`      | Downloads filings from SEC Edgar with caching              |
| `CustomWorkflow`     | Base class for user-defined analysis workflows             |
| `RequestQueue`       | Cross-process API request serialization with file locking  |
| `BatchQueueService`  | Multi-day batch job management and scheduling              |
| `CancellationToken`  | Graceful analysis cancellation system                      |

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

### Fault-Tolerant Architecture

- **Resume capability** - Interrupted analyses continue from last completed year
- **Exponential backoff retry** - Up to 3 retries with configurable delays
- **SQLite WAL mode** - Concurrent read/write without locking conflicts
- **Completed years tracking** - Prevents re-analyzing already processed data
- **Graceful cancellation** - Stop running analyses without data corruption

### Type-Safe AI Outputs

- **Pydantic v2 structured outputs** ensure 99%+ format consistency
- **Validation at extraction time** not post-processing
- **Custom exception hierarchy** for granular error handling
- **Schema enforcement** reduces hallucination and format errors

---

## Compounder DNA Scoring

Compare any company against the patterns of the top 50 proven compounders:

| Score  | Category                 | Interpretation                                 |
| ------ | ------------------------ | ---------------------------------------------- |
| 90-100 | **Future Compounder**    | Exceptional alignment with top performers      |
| 75-89  | **Strong Potential**     | Significant alignment, foundation present      |
| 60-74  | **Developing Contender** | Meaningful elements with room to grow          |
| 40-59  | **Partial Alignment**    | Some positive elements, lacks cohesive pattern |
| 20-39  | **Limited Alignment**    | Minimal resemblance to compounders             |
| 0-19   | **Misaligned**           | Counter to top performer patterns              |

---

## Database Schema

Fintel uses SQLite with WAL mode for concurrent access. Schema is managed through migrations.

### Core Tables

| Table              | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| `analysis_runs`    | Tracks each analysis job (status, progress, config) |
| `analysis_results` | Stores Pydantic model outputs as JSON               |
| `file_cache`       | Caches downloaded SEC filings                       |
| `custom_prompts`   | User-created analysis prompts                       |
| `user_settings`    | User preferences (key-value)                        |

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

### Logs

Logs are stored in `logs/` directory:

- `fintel.log` - Main application log
- Rotate daily with 7-day retention

---

## Technology Stack

| Layer          | Technologies                                       |
| -------------- | -------------------------------------------------- |
| **Web UI**     | Streamlit 1.30+, Pandas, Polars                    |
| **LLM**        | Google Gemini API, Pydantic 2.0+ structured output |
| **Data**       | PyPDF2, Selenium + Chrome, SEC Edgar API           |
| **Storage**    | SQLite (WAL mode), JSON, Parquet                   |
| **CLI**        | Click, Rich                                        |
| **Processing** | ThreadPool, concurrent.futures                     |
| **Config**     | Pydantic Settings, python-dotenv                   |

---

## Requirements

- Python 3.10+
- Google Chrome (for HTML → PDF conversion)
- Google Gemini API key(s)
- 4GB+ RAM recommended for batch processing

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
- [Session State Management](docs/SESSION_STATE.md) - Streamlit state handling
- [UI Architecture](fintel/ui/README.md) - Web interface details
