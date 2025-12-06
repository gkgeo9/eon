# Fintel Examples

This directory contains example scripts demonstrating various Fintel features.

## Available Examples

### 1. Basic Analysis ([basic_analysis.py](basic_analysis.py))

Simple single-company fundamental analysis.

```bash
python examples/basic_analysis.py
```

**What it does:**
- Downloads 5 years of 10-K filings for Apple (AAPL)
- Converts HTML to PDF
- Performs AI-powered fundamental analysis
- Displays business model, revenue, and key strategies

**Duration:** ~10-15 minutes (due to 65-second rate limiting per filing)

---

### 2. Batch Processing ([batch_processing.py](batch_processing.py))

Parallel processing of multiple companies.

```bash
python examples/batch_processing.py
```

**What it does:**
- Processes 5 tech companies in parallel (AAPL, MSFT, GOOGL, NVDA, TSLA)
- Uses 5 parallel workers with separate API keys
- Analyzes 10 years of filings per company
- Saves results to batch_results directory

**Duration:** ~30-45 minutes (parallelized across 5 workers)

---

### 3. Multi-Perspective Analysis ([multi_perspective.py](multi_perspective.py))

Analyze through Buffett, Taleb, and Contrarian lenses.

```bash
python examples/multi_perspective.py
```

**What it does:**
- Analyzes Netflix (NFLX) through 3 investment perspectives
- **Buffett Lens:** Economic moat, ROIC, pricing power
- **Taleb Lens:** Fragility, antifragility, tail risks
- **Contrarian Lens:** Market consensus vs. alternative thesis
- Provides synthesized final verdict

**Duration:** ~5-10 minutes (3 API calls with rate limiting)

---

## Prerequisites

Before running examples, ensure you have:

1. **API Keys Configured:**
   ```bash
   # .env file
   GOOGLE_API_KEY_1=your_key_here
   GOOGLE_API_KEY_2=your_key_here  # Optional, for parallel processing
   # ... up to GOOGLE_API_KEY_25
   ```

2. **Dependencies Installed:**
   ```bash
   cd fintel
   pip install -e .
   ```

3. **Chrome/Chromium** installed (for HTML to PDF conversion)

---

## Understanding Rate Limiting

⏰ **Important:** Fintel implements mandatory 65-second sleep after each API call to comply with SEC rate limits and avoid API quota issues.

- Single filing: ~1-2 minutes (1 API call + 65s sleep)
- 5 filings: ~6-10 minutes (5 API calls)
- Multi-perspective (3 lenses): ~4-6 minutes (3 API calls)
- Parallel processing: Scales linearly with workers (5 workers = ~5x faster)

---

## Customization

All examples can be customized by editing the script variables:

```python
# basic_analysis.py
ticker = "AAPL"  # Change to any ticker
num_years = 5    # Adjust number of years

# batch_processing.py
tickers = ["AAPL", "MSFT", ...]  # Add/remove tickers
num_workers = 5                   # Adjust parallelism

# multi_perspective.py
ticker = "NFLX"  # Change company
year = 2024      # Adjust year
```

---

## CLI Alternative

All examples can also be run using the CLI:

```bash
# Basic analysis
fintel analyze AAPL --years 5

# Batch processing
echo -e "AAPL\nMSFT\nGOOGL\nNVDA\nTSLA" > tickers.txt
fintel batch tickers.txt --workers 5

# Multi-perspective
fintel analyze NFLX --analysis-type perspectives

# Export results
fintel export --format csv --output results.csv
```

See `fintel --help` for all CLI options.

---

## Output Structure

Results are saved in structured directories:

```
data/
├── processed/           # JSON results from fundamental analysis
│   └── AAPL/
│       └── fundamental/
│           ├── 2024_analysis.json
│           ├── 2023_analysis.json
│           └── ...
├── perspectives/        # Multi-perspective analysis results
│   └── NFLX/
│       └── 2024_perspectives.json
├── batch_results/       # Batch processing results
│   ├── AAPL/
│   ├── MSFT/
│   └── ...
└── archive/            # Parquet files (if using Parquet storage)
    └── fundamental/
        └── year=2024/
            └── data.parquet
```

---

## Troubleshooting

### API Key Errors
```
✗ No Google API keys configured
```
**Solution:** Add `GOOGLE_API_KEY_1=...` to your `.env` file

### PDF Conversion Fails
```
✗ Chrome driver not found
```
**Solution:** Install Chrome/Chromium browser

### Rate Limit Errors
```
429 Too Many Requests
```
**Solution:** Wait and retry. Fintel automatically sleeps 65 seconds between calls.

---

## Next Steps

After running examples, explore:

1. **Storage Backends:** Export results to Parquet for efficient querying
2. **Contrarian Scanner:** Find hidden gems with alpha scoring
3. **Custom Analysis:** Write custom prompts and schemas
4. **REST API:** Build a FastAPI service (future feature)

For more information, see [docs/quickstart.md](../docs/quickstart.md).
