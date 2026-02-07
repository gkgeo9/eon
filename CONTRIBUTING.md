# Contributing to EON

## Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd eon

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

## Code Style

We use the following tools for code quality:

- **black** - Code formatting (line length: 100)
- **ruff** - Fast linting
- **mypy** - Type checking

Run before committing:

```bash
# Format code
black eon/ tests/

# Lint and fix
ruff check eon/ tests/ --fix

# Type check
mypy eon/
```

## Project Structure

```
eon/
├── analysis/           # Core analysis logic
│   ├── fundamental/    # Basic 10-K analysis
│   ├── perspectives/   # Buffett, Taleb, Contrarian lenses
│   └── comparative/    # Benchmarking and contrarian scanner
├── ai/                 # LLM providers and key management
├── data/sources/sec/   # SEC filing download and processing
├── ui/                 # Streamlit UI components
│   ├── components/     # Reusable UI components
│   ├── database/       # Database repository
│   └── services/       # Business logic services
└── cli/                # Command-line interface

custom_workflows/       # Custom analysis workflows (auto-discovered)
pages/                  # Streamlit pages
tests/                  # Test suite
```

## Adding a Custom Workflow

Create a new file in `custom_workflows/`:

```python
# custom_workflows/my_workflow.py
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow

class MyResult(BaseModel):
    """Define your output schema."""
    summary: str = Field(description="Key findings")
    score: int = Field(ge=0, le=100, description="Score 0-100")

class MyWorkflow(CustomWorkflow):
    """Your workflow class."""
    name = "My Workflow"
    description = "What this workflow does"
    icon = "🔬"
    min_years = 1
    category = "custom"

    @property
    def prompt_template(self) -> str:
        return """Analyze {ticker} for fiscal year {year}.
        [Your analysis instructions here]"""

    @property
    def schema(self):
        return MyResult
```

The workflow will automatically appear in the Analysis page dropdown.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=eon --cov-report=html

# Run specific test file
pytest tests/test_workflows.py

# Run tests matching a pattern
pytest -k "test_analysis"
```

## Database Migrations

Database migrations are in `eon/ui/database/migrations/`. Files are named with version prefixes (e.g., `v001_initial.sql`, `v002_add_column.sql`) and are applied in order on startup.

To add a migration:

1. Create a new file: `v00X_description.sql`
2. Write idempotent SQL (use `IF NOT EXISTS`)
3. Test with a fresh database

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add multi-year analysis support
fix: Handle database lock in batch processing
docs: Update README with custom workflow example
refactor: Extract PDF processing into separate module
test: Add tests for contrarian scanner
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Run linting and type checks
4. Update documentation if needed
5. Submit PR with clear description

## Architecture Guidelines

### Pydantic Models

All AI outputs use Pydantic models for type safety:

```python
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    ticker: str
    score: int = Field(ge=0, le=100)
    summary: str = Field(description="Brief summary")
```

### Error Handling

Use the custom exceptions in `eon/core/exceptions.py`:

```python
from eon.core.exceptions import AnalysisError, DownloadError

if not pdf_path.exists():
    raise DownloadError(f"Filing not found: {pdf_path}")
```

### Logging

Use module-level loggers:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing {ticker}")
logger.error(f"Failed to analyze: {e}")
```

## Questions?

Open an issue for questions or feature requests.
