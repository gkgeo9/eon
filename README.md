# Fintel

AI-powered SEC filing analysis platform for investment research.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

Fintel analyzes SEC 10-K filings using Google Gemini AI to extract investment insights. It provides multiple analysis perspectives including fundamental analysis, multi-year success factor analysis, and contrarian opportunity scanning.

### Key Features

- **Multi-Perspective Analysis** - Buffett, Taleb, and Contrarian investment lenses
- **Custom Workflows** - Create your own analysis prompts with auto-discovery
- **Batch Processing** - Analyze multiple companies in parallel with 25+ API keys
- **Compounder DNA Scoring** - Compare companies against proven top performers
- **Contrarian Scanner** - Find hidden gems with 6-dimension scoring (0-600 scale)

## Quick Start

### 1. Install

```bash
# Clone and setup
git clone <your-repo-url>
cd Fintel
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Configure

Create `.env` file:

```bash
# Required: Google Gemini API key(s)
GOOGLE_API_KEY_1=your_key_here
GOOGLE_API_KEY_2=your_second_key  # Optional: more keys = faster parallel processing

# Required: SEC Edgar identification
FINTEL_SEC_USER_EMAIL=your@email.com
FINTEL_SEC_COMPANY_NAME="Research Script"
```

### 3. Run

```bash
# Launch web interface
streamlit run streamlit_app.py

# Or use CLI
fintel analyze AAPL --years 5
```

The web app opens at `http://localhost:8501`

## Analysis Types

| Type | Description | Min Years |
|------|-------------|-----------|
| **Fundamental** | Business model, financials, risks, strategies | 1 |
| **Buffett Lens** | Economic moat, management quality, intrinsic value | 1 |
| **Taleb Lens** | Fragility assessment, tail risks, antifragility | 1 |
| **Contrarian Lens** | Hidden opportunities, variant perception | 1 |
| **Multi-Perspective** | Combined Buffett + Taleb + Contrarian analysis | 1 |
| **Excellent Company** | Success factors of proven winners | 3 |
| **Objective Analysis** | Unbiased assessment for screening | 3 |
| **Contrarian Scanner** | 6-dimension hidden compounder scoring | 3 |

## Custom Workflows

Create custom analysis workflows by adding Python files to `custom_workflows/`:

```python
# custom_workflows/my_analysis.py
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow

class MyResult(BaseModel):
    summary: str = Field(description="Key findings")
    score: int = Field(ge=0, le=100, description="Overall score")

class MyAnalysis(CustomWorkflow):
    name = "My Custom Analysis"
    description = "Analyzes specific aspects I care about"
    icon = "🔬"
    min_years = 1

    @property
    def prompt_template(self) -> str:
        return """Analyze {ticker} for fiscal year {year}.
        Focus on [your specific criteria here]."""

    @property
    def schema(self):
        return MyResult
```

Your workflow automatically appears in the Analysis page dropdown.

## Project Structure

```
fintel/
├── analysis/           # Core analysis logic
│   ├── fundamental/    # 10-K analysis, success factors
│   ├── perspectives/   # Buffett, Taleb, Contrarian lenses
│   └── comparative/    # Benchmarking, contrarian scanner
├── ai/                 # LLM providers, API key management
├── data/sources/sec/   # SEC filing download and processing
├── ui/                 # Streamlit components and services
└── cli/                # Command-line interface

custom_workflows/       # Your custom analysis workflows (auto-discovered)
pages/                  # Streamlit pages
tests/                  # Test suite
```

## Web Interface Pages

| Page | Description |
|------|-------------|
| **Analysis** | Run single or batch company analysis |
| **Analysis History** | View past analysis runs and status |
| **Results Viewer** | Explore analysis results in detail |
| **Settings** | Configure API keys and preferences |
| **Database Viewer** | Browse raw database tables |

## CLI Usage

```bash
# Single company analysis
fintel analyze AAPL --years 10

# Batch processing
echo -e "AAPL\nMSFT\nGOOGL" > tickers.txt
fintel batch tickers.txt --workers 10

# Contrarian scan
fintel scan --tickers-file tickers.txt --min-score 400
```

## Configuration

All settings via `.env` or environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY_1` | Primary Gemini API key | Required |
| `GOOGLE_API_KEY_2..25` | Additional keys for parallel processing | Optional |
| `FINTEL_SEC_USER_EMAIL` | Email for SEC Edgar API | Required |
| `FINTEL_NUM_WORKERS` | Parallel worker count | 25 |
| `FINTEL_DATA_DIR` | Data storage directory | `./data` |
| `FINTEL_LOG_DIR` | Log file directory | `./logs` |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black fintel/
ruff check fintel/ --fix

# Type checking
mypy fintel/
```

## Architecture

- **Pydantic Models** - Type-safe structured outputs from AI
- **API Key Rotation** - Automatic rotation across 25+ keys with rate limiting
- **SQLite + WAL** - Concurrent database access for parallel processing
- **Streamlit UI** - Interactive web interface with session state management

## Compounder DNA Scoring

Compare any company against the top 50 proven performers:

| Score | Category | Meaning |
|-------|----------|---------|
| 90-100 | Future Compounder | Exceptional alignment with top performers |
| 75-89 | Strong Potential | Significant alignment, foundation present |
| 60-74 | Developing Contender | Meaningful elements with room to grow |
| 40-59 | Partial Alignment | Some positive elements, lacks cohesive pattern |
| 20-39 | Limited Alignment | Minimal resemblance to compounders |
| 0-19 | Misaligned | Counter to top performer patterns |

## Troubleshooting

**"No API key found"**
```bash
cat .env | grep GOOGLE_API_KEY  # Verify keys exist
```

**"Database locked"**
```bash
sqlite3 fintel.db "PRAGMA integrity_check;"  # Check database health
```

**"SEC download failed"**
- Ensure `FINTEL_SEC_USER_EMAIL` is set
- SEC Edgar may have rate limits during peak hours

## License

Private - For personal use only.

---

**Disclaimer**: This platform is for research and educational purposes. Always conduct your own due diligence before making investment decisions.
