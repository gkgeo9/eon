# Fintel Quick Start Guide

## Platform Status

**FINTEL IS READY TO USE**

All tests passing (14/14). Platform validated and working.

## Running Your First Analysis

### 1. Activate Virtual Environment
```bash
source /Users/gkg/PycharmProjects/stock_stuff_06042025/.venv/bin/activate
cd /Users/gkg/PycharmProjects/stock_stuff_06042025/fintel
```

### 2. Set Up Environment Variables
Ensure your `.env` file has API keys:
```bash
GOOGLE_API_KEY_1=your_key_here
GOOGLE_API_KEY_2=your_key_here
# ... up to GOOGLE_API_KEY_25
```

### 3. Run a Test Analysis
```bash
# Basic fundamental analysis (single year)
python examples/01_basic_fundamental_analysis.py

# Excellent company analysis (multi-year)
python examples/02_excellent_company_analysis.py

# Random company analysis (objective)
python examples/03_random_company_analysis.py

# Contrarian scanning
python examples/04_contrarian_scanning.py
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

### For Using Fintel Now (CLI)
1. `QUICK_START.md` - This file
2. `TEST_RESULTS_SUMMARY.md` - Test validation results
3. `examples/` - Example scripts

### For Building Web UI
1. `FRONTEND_GUIDE.md` - Complete frontend specification (START HERE)
2. `SESSION_COMPLETE.md` - Full session summary

### For Development
1. `TESTING_REPORT.md` - Testing methodology
2. `VALIDATION_COMPLETE.md` - Validation summary

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
1. Run `python examples/test_final.py` to verify setup
2. Pick an example script from `examples/`
3. Modify ticker and year as needed
4. Run and review results in `data/output/`

### To Build Web UI
1. Read `FRONTEND_GUIDE.md` (comprehensive 950+ line guide)
2. Implement PostgreSQL database (schema provided)
3. Build FastAPI REST API (endpoints specified)
4. Add Celery task queue (tasks defined)
5. Build frontend (9 pages designed)

## Support

For issues or questions:
- Check `TESTING_REPORT.md` for known limitations
- Review `SESSION_COMPLETE.md` for full context
- Consult `FRONTEND_GUIDE.md` for architecture details

---
**Last Updated:** 2024-01-15
**Version:** 1.0
**Status:** Production Ready (CLI)
