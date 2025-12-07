# Fintel Quick Start Guide

## Platform Status

**FINTEL IS READY TO USE**

Platform validated and working. Both CLI and Web UI available.

## Getting Started

### 1. Activate Virtual Environment
```bash
cd /Users/gkg/PycharmProjects/Fintel
source .venv/bin/activate
```

### 2. Set Up Environment Variables
Ensure your `.env` file has API keys:
```bash
GOOGLE_API_KEY_1=your_key_here
GOOGLE_API_KEY_2=your_key_here
# ... up to GOOGLE_API_KEY_25
```

### 3. Choose Your Interface

**Option A: Web Interface (Recommended)**
```bash
streamlit run streamlit_app.py
```
Opens at `http://localhost:8501`

**Option B: CLI/Examples**
```bash
cd examples

# Basic fundamental analysis (single year)
python 01_basic_fundamental_analysis.py

# Excellent company analysis (multi-year)
python 02_excellent_company_analysis.py

# Random company analysis (objective)
python 03_random_company_analysis.py

# Contrarian scanning
python 04_contrarian_scanning.py
```

## Running Tests

### Quick Validation
```bash
cd examples
python test_final.py
```

### Comprehensive Model Tests
```bash
cd examples
python test_all_models.py
```

### Perspective Analysis Tests
```bash
cd examples
python test_perspectives.py
```

### All Tests
```bash
cd examples
python test_final.py && python test_all_models.py && python test_perspectives.py
```

## What Works Now (CLI)

- Single company fundamental analysis
- Multi-year success factor analysis
- Multi-perspective analysis (Buffett/Taleb/Contrarian)
- Compounder DNA benchmarking (0-100 score)
- Contrarian opportunity scanning (0-100 alpha score)
- Batch processing (parallel analysis)

## Important Notes

### Rate Limiting
- Production: 65 seconds between requests
- Testing: 0 seconds (modify in examples)
- Daily limit: 500 requests per API key

### API Costs
- Each analysis uses 1 API call
- Monitor usage in logs
- Rotate through 25 API keys automatically

### Output
- Results saved to `data/output/` directory
- JSON format for easy parsing
- Timestamped filenames

## Documentation Index

### Essential Documentation
1. `README.md` - Complete platform overview and reference
2. `QUICK_START.md` - This file - getting started guide
3. `docs/quickstart.md` - Additional quick start examples
4. `examples/README.md` - Example scripts documentation
5. `src/fintel/ui/README.md` - Web UI documentation

## File Structure

```
fintel/
├── src/fintel/
│   ├── core/              # Configuration, logging
│   ├── data/              # SEC data sources
│   ├── ai/                # Google Gemini integration
│   ├── analysis/
│   │   ├── fundamental/   # Basic and success factor analysis
│   │   ├── perspectives/  # Buffett, Taleb, Contrarian lenses
│   │   └── comparative/   # Benchmarking, contrarian scanning
│   └── workflows/         # Batch processing workflows
├── examples/              # Example scripts and tests
├── data/
│   ├── filings/           # Downloaded 10-K HTML files
│   ├── pdfs/              # Converted PDF files
│   └── output/            # Analysis results (JSON)
└── docs/                  # Documentation
```

## Common Tasks

### Analyze a Single Company
```python
from fintel.analysis.fundamental.analyzer import FundamentalAnalyzer
from fintel.examples.utils import init_components

api_key_manager, rate_limiter = init_components(sleep_seconds=65)
analyzer = FundamentalAnalyzer(api_key_manager, rate_limiter)

result = analyzer.analyze_company("AAPL", year=2023)
print(result)
```

### Multi-Perspective Analysis
```python
from fintel.analysis.perspectives.analyzer import PerspectiveAnalyzer
from fintel.examples.utils import init_components

api_key_manager, rate_limiter = init_components(sleep_seconds=65)
analyzer = PerspectiveAnalyzer(api_key_manager, rate_limiter)

result = analyzer.analyze("AAPL", year=2023)
# Returns: BuffettAnalysis, TalebAnalysis, ContrarianViewAnalysis
```

### Benchmark Against Top 50
```python
from fintel.analysis.comparative.benchmarking import BenchmarkComparator
from fintel.examples.utils import init_components

api_key_manager, rate_limiter = init_components(sleep_seconds=65)
comparator = BenchmarkComparator(api_key_manager, rate_limiter)

result = comparator.compare_to_baseline("AAPL", year=2023)
# Returns: BenchmarkComparison with 0-100 compounder score
```

### Contrarian Scanning
```python
from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
from fintel.examples.utils import init_components

api_key_manager, rate_limiter = init_components(sleep_seconds=65)
scanner = ContrarianScanner(api_key_manager, rate_limiter)

result = scanner.scan("UNUSUAL_TICKER", year=2023)
# Returns: ContrarianAnalysis with 0-100 alpha score
```

## Troubleshooting

### "No Google API keys found"
- Check `.env` file exists
- Verify environment variables are set
- Restart Python session after updating .env

### "Rate limit exceeded"
- Check rate limiter sleep time (should be 65 seconds in production)
- Verify you haven't exceeded 500 requests/day per key
- Check logs for actual usage

### "Failed to download 10-K"
- Verify ticker symbol is correct
- Check year is valid (company existed, filed 10-K)
- SEC Edgar may be down (retry later)

### "PDF extraction failed"
- Check PDF file exists in `data/pdfs/`
- Verify PDF is not corrupted
- Some 10-Ks are complex (try different company)

## Next Steps

### To Use Fintel Now
1. Launch the web interface: `streamlit run streamlit_app.py`
2. Or explore the CLI examples in `examples/`
3. Read the main `README.md` for comprehensive documentation
4. Check `src/fintel/ui/README.md` for web UI features

---
**Last Updated:** 2025-12-06
**Version:** 1.0
**Status:** Production Ready (CLI + Web UI)
