# CLAUDE.md - AI Assistant Guidelines for EON

This document provides essential context for AI assistants working with the Erebus Observatory Network (EON) codebase.

## Project Overview

EON is an AI-powered SEC filing analysis platform for investment research. It analyzes SEC 10-K and other filings using Google Gemini AI to extract actionable investment insights through multiple investment philosophies (Warren Buffett value investing, Nassim Taleb antifragility, contrarian analysis).

**Key capabilities:**
- Multi-perspective financial analysis (Buffett, Taleb, Contrarian lenses)
- Batch processing with 25+ API key rotation
- Custom workflow system with auto-discovery
- Resume capability for interrupted analyses
- Cross-process rate limiting with file-based locking

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Language | Python 3.10+ |
| Web UI | Streamlit 1.30+ |
| LLM | Google Gemini API with Pydantic structured output |
| Data | PyPDF2, Selenium + Chrome, SEC Edgar API |
| Storage | SQLite (WAL mode), JSON, Parquet |
| CLI | Click, Rich |
| Config | Pydantic Settings, python-dotenv |
| Testing | pytest, pytest-cov |

## Project Structure

```
eon/
├── analysis/                    # Core analysis engines
│   ├── fundamental/             # 10-K analysis
│   │   ├── analyzer.py          # FundamentalAnalyzer
│   │   ├── models/              # Pydantic output schemas
│   │   └── prompts/             # AI prompt templates
│   ├── perspectives/            # Investment lens analyzers (Buffett, Taleb, Contrarian)
│   └── comparative/             # Benchmarking & contrarian scanner
│
├── ai/                          # LLM integration
│   ├── providers/gemini.py      # Google Gemini implementation
│   ├── key_manager.py           # API key rotation (25+ keys)
│   ├── rate_limiter.py          # Request rate limiting
│   └── request_queue.py         # Cross-process request serialization
│
├── core/                        # Shared infrastructure
│   ├── config.py                # EonConfig (Pydantic Settings)
│   ├── exceptions.py            # Custom exception hierarchy
│   ├── interfaces.py            # Protocol definitions (IKeyManager, etc.)
│   └── logging.py               # Centralized logging
│
├── data/sources/sec/            # SEC Edgar integration
│   ├── downloader.py            # Download filings
│   ├── converter.py             # HTML → PDF conversion
│   └── extractor.py             # PDF text extraction
│
├── ui/                          # Streamlit web interface
│   ├── database/                # SQLite data layer
│   │   ├── repository.py        # DatabaseRepository
│   │   └── migrations/          # Schema migrations (v001-v010)
│   └── services/                # Business logic
│       ├── analysis_service.py  # Main orchestrator
│       ├── batch_queue.py       # Multi-day batch processing
│       └── cancellation.py      # Graceful cancellation system
│
└── cli/                         # Command-line interface

custom_workflows/                # User-defined workflows (auto-discovered)
├── base.py                      # CustomWorkflow base class
└── examples/                    # Example workflows

pages/                           # Streamlit pages
tests/                           # Test suite
```

## Development Commands

```bash
# Setup
pip install -e ".[dev]"

# Run web UI
streamlit run streamlit_app.py

# Run CLI
eon analyze AAPL --years 5
eon batch tickers.csv --workers 10

# Testing
pytest                           # Run all tests
pytest --cov=eon             # With coverage
pytest tests/test_file.py -v    # Specific file
pytest -k "test_analysis"       # Pattern match

# Code Quality
black eon/ tests/ pages/     # Format (line-length: 100)
ruff check eon/ --fix        # Lint
mypy eon/                    # Type check
```

## Code Conventions

### Pydantic Models
All AI outputs use Pydantic v2 models for type safety:
```python
from pydantic import BaseModel, Field
from typing import List

class AnalysisResult(BaseModel):
    summary: str = Field(description="Brief summary")
    score: int = Field(ge=0, le=100, description="Score 0-100")
    key_findings: List[str] = Field(description="Top findings")
```

### Exception Handling
Use the custom exception hierarchy in `eon/core/exceptions.py`:
```python
from eon.core.exceptions import AnalysisError, DownloadError, RateLimitError

# Exception hierarchy:
# EonException (base)
# ├── ConfigurationError
# ├── DataSourceError
# │   ├── DownloadError
# │   ├── ConversionError
# │   └── ExtractionError
# ├── AnalysisError
# ├── AIProviderError
# │   ├── RateLimitError
# │   └── KeyQuotaExhaustedError
# ├── StorageError
# └── ValidationError
```

### Logging
Use module-level loggers:
```python
from eon.core import get_logger
logger = get_logger(__name__)

logger.info(f"Processing {ticker}")
logger.error(f"Failed: {e}")
```

### Configuration
Access config via singleton:
```python
from eon.core import get_config

config = get_config()
data_path = config.get_data_path("pdfs", ticker)
```

### Dependency Injection
Services support dependency injection for testability:
```python
class AnalysisService:
    def __init__(
        self,
        db: DatabaseRepository,
        config: Optional[EonConfig] = None,
        key_manager: Optional[IKeyManager] = None,
        rate_limiter: Optional[IRateLimiter] = None,
    ):
        # Dependencies optional for backward compatibility
```

## Key Patterns

### API Key Management
- Keys are rotated across 25+ configured keys
- Atomic reservation prevents collisions in parallel processing
- Persistent usage tracking survives restarts
```python
api_key = self.api_key_manager.reserve_key()
try:
    # Use key
    self.api_key_manager.record_usage(api_key)
finally:
    self.api_key_manager.release_key(api_key)
```

### Cross-Process Rate Limiting
File-based locking using `portalocker` serializes API requests:
- Lock file at `data/api_usage/gemini_request.lock`
- 65-second mandatory sleep between requests (Gemini requirement)

### Custom Workflows
Auto-discovered Python files in `custom_workflows/`:
```python
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow

class MyResult(BaseModel):
    score: int = Field(ge=0, le=100, description="Score 0-100")

class MyWorkflow(CustomWorkflow):
    name = "My Workflow"
    description = "What this does"
    icon = "🔬"
    min_years = 1

    @property
    def prompt_template(self) -> str:
        return "Analyze {ticker} for fiscal year {year}..."

    @property
    def schema(self):
        return MyResult
```

### Database Migrations
Located in `eon/ui/database/migrations/` with version prefixes:
- Use `IF NOT EXISTS` for idempotent SQL
- Applied automatically on startup

## Testing Patterns

### Fixtures (in tests/conftest.py)
```python
@pytest.fixture
def temp_dir() -> Path:
    """Temporary directory cleaned up after test."""

@pytest.fixture
def test_db(temp_db_path: Path):
    """Test DatabaseRepository with migrations applied."""

@pytest.fixture
def mock_gemini_provider():
    """Mock GeminiProvider returning fake results."""
```

### Test Markers
```python
@pytest.mark.unit          # Fast, no external dependencies
@pytest.mark.integration   # May use database
@pytest.mark.stress        # Slow, high concurrency
@pytest.mark.slow          # Tests > 5 seconds
```

## Environment Variables

Required:
- `GOOGLE_API_KEY_1` (through `GOOGLE_API_KEY_25`) - Gemini API keys
- `EON_SEC_USER_EMAIL` - Email for SEC Edgar compliance
- `EON_SEC_COMPANY_NAME` - Company name for SEC compliance

Key settings:
- `EON_DEFAULT_MODEL=gemini-2.5-flash`
- `EON_NUM_WORKERS=25`
- `EON_SLEEP_AFTER_REQUEST=65`
- `EON_STORAGE_BACKEND=parquet`

## Common Tasks

### Adding a New Analysis Type
1. Create models in `eon/analysis/<type>/models/`
2. Create prompts in `eon/analysis/<type>/prompts/`
3. Implement analyzer in `eon/analysis/<type>/analyzer.py`
4. Register in `AnalysisService._run_analysis_by_type()`
5. Add to UI dropdown in `pages/1_📊_Analysis.py`

### Adding a Database Migration
1. Create `eon/ui/database/migrations/v0XX_description.sql`
2. Write idempotent SQL (use `IF NOT EXISTS`)
3. Test with fresh database

### Debugging Rate Limit Issues
- Check `data/api_usage/` for usage files
- Review lock file at `data/api_usage/gemini_request.lock`
- Increase `EON_SLEEP_AFTER_REQUEST` if needed
- Add more API keys (up to 25)

## Important Files Reference

| Purpose | File |
|---------|------|
| Main entry point (web) | `streamlit_app.py` |
| Main entry point (CLI) | `eon/cli/main.py` |
| Configuration | `eon/core/config.py` |
| Exceptions | `eon/core/exceptions.py` |
| Analysis orchestrator | `eon/ui/services/analysis_service.py` |
| Database repository | `eon/ui/database/repository.py` |
| Gemini provider | `eon/ai/providers/gemini.py` |
| API key manager | `eon/ai/key_manager.py` |
| Rate limiter | `eon/ai/rate_limiter.py` |
| Custom workflow base | `custom_workflows/base.py` |
| Test fixtures | `tests/conftest.py` |

## Code Style

- **Formatter**: Black (line-length: 100)
- **Linter**: Ruff
- **Type checker**: mypy
- **Imports**: Organized by isort (via ruff)
- **Docstrings**: Google style

## Commit Message Format
```
feat: Add multi-year analysis support
fix: Handle database lock in batch processing
docs: Update README with custom workflow example
refactor: Extract PDF processing into separate module
test: Add tests for contrarian scanner
```

## Important Notes for AI Assistants

1. **Never commit secrets** - API keys are in `.env` (gitignored)
2. **Use existing exceptions** - Don't create new ones unless necessary
3. **Follow Pydantic patterns** - All AI outputs must use Pydantic models with Field descriptions
4. **Test before committing** - Run `pytest` to verify changes
5. **Maintain backward compatibility** - Services support DI for testing
6. **Rate limiting is critical** - Never bypass the rate limiter or key manager
7. **Database uses WAL mode** - Concurrent access is handled via SQLite WAL
8. **Custom workflows auto-discover** - Just add Python files to `custom_workflows/`
