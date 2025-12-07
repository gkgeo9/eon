# Fintel Quick Start Guide

Get up and running with Fintel in minutes!

## Installation

### 1. Install Dependencies

```bash
cd /Users/gkg/PycharmProjects/Fintel
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Set Up Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Google API keys
nano .env  # or use your favorite editor
```

At minimum, add one Google Gemini API key:
```bash
GOOGLE_API_KEY_1=your_actual_api_key_here
FINTEL_SEC_USER_EMAIL=your.email@example.com
```

### 3. Verify Installation

```python
from fintel.core import get_config

config = get_config()
print(f"Loaded {config.num_api_keys} API keys")
print(f"Data directory: {config.data_dir}")
```

## Basic Workflows

### Workflow 1: Download and Convert a Single Company

```python
from fintel.data.sources.sec import SECDownloader, SECConverter

# Step 1: Download 10-K filings
downloader = SECDownloader(
    company_name="Research Script",
    user_email="you@example.com"
)

filing_path = downloader.download("AAPL", num_filings=5)
print(f"Downloaded to: {filing_path}")

# Step 2: Convert HTML to PDF
converter = SECConverter()
pdfs = converter.convert("AAPL", filing_path)
converter.close()

print(f"Converted {len(pdfs)} filings:")
for pdf in pdfs:
    print(f"  {pdf['year']}: {pdf['pdf_path']}")
```

### Workflow 2: Extract Text from PDFs

```python
from fintel.data.sources.sec import PDFExtractor
from pathlib import Path

extractor = PDFExtractor()

# Extract from a single PDF
pdf_path = Path("./data/raw/sec_filings/sec-edgar-filings/AAPL/10-K/PDF_Filings/AAPL_10-K_2024.pdf")
text = extractor.extract_text(pdf_path)

print(f"Extracted {len(text):,} characters")
print(f"First 500 characters:\n{text[:500]}")

# Get page count
num_pages = extractor.get_page_count(pdf_path)
print(f"PDF has {num_pages} pages")
```

### Workflow 3: Batch Download Multiple Companies

```python
from fintel.data.sources.sec import SECDownloader

downloader = SECDownloader(
    company_name="Research Script",
    user_email="you@example.com"
)

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
results = downloader.download_batch(tickers, num_filings=3)

for ticker, path in results.items():
    if path:
        print(f"{ticker}: ✓ Downloaded to {path}")
    else:
        print(f"{ticker}: ✗ Failed")
```

### Workflow 4: Using Configuration

```python
from fintel.core import get_config, get_logger

# Get global config
config = get_config()

# Access configuration values
print(f"Workers: {config.num_workers}")
print(f"Model: {config.default_model}")
print(f"Storage: {config.storage_backend}")

# Get custom paths
data_path = config.get_data_path("processed", "fundamental")
cache_path = config.get_cache_path("embeddings")
log_path = config.get_log_path("analysis.log")

# Set up logging
logger = get_logger("my_script")
logger.info("Starting analysis...")
```

## Working with Pydantic Schemas

### Fundamental Analysis Schema

```python
from fintel.analysis.fundamental import TenKAnalysis, FinancialHighlights

# Example structure - what you'll get from AI analysis
analysis = TenKAnalysis(
    business_model="Apple designs and manufactures consumer electronics...",
    unique_value="Strong brand loyalty and ecosystem lock-in...",
    key_strategies=["Services growth", "Wearables expansion", "India market"],
    financial_highlights=FinancialHighlights(
        revenue="$383B revenue, up 8% YoY",
        profit="$97B net income, 25% margin",
        cash_position="$61B cash, $107B debt"
    ),
    risks=["China dependency", "Regulatory pressure", "Innovation challenges"],
    management_quality="A-grade capital allocation, strong execution",
    innovation="Mature product cycle, incremental improvements",
    competitive_position="Market leader in premium segment with 50%+ share",
    esg_factors="Carbon neutral by 2030 goal, supplier audits",
    key_takeaways=[
        "Services revenue growing faster than products",
        "Installed base reached 2 billion devices",
        "Gross margin expansion due to mix shift"
    ]
)

# Access fields with autocomplete
print(analysis.business_model)
print(analysis.financial_highlights.revenue)

# Serialize to JSON
json_output = analysis.model_dump_json(indent=2)

# Convert to dict
dict_output = analysis.model_dump()
```

### Multi-Perspective Analysis Schemas

```python
from fintel.analysis.perspectives import (
    BuffettAnalysis,
    TalebAnalysis,
    ContrarianAnalysis
)

# Buffett Lens - Value Investing
buffett = BuffettAnalysis(
    business_understanding="Simple razor-blade model...",
    economic_moat="Brand power with 20% pricing premium",
    moat_rating="Wide (15+ years sustainable)",
    management_quality="A-grade: 25% ROIC, smart buybacks",
    pricing_power="Raised prices 15% in 2023, lost only 3% volume",
    return_on_invested_capital="ROIC trending up: 18% → 22% → 25%",
    free_cash_flow_quality="FCF conversion 95%, growing faster than revenue",
    business_tailwinds=[
        "Cloud migration driving 30% annual SaaS growth",
        "Aging population increasing healthcare spending"
    ],
    intrinsic_value_estimate="$150B intrinsic vs $100B market cap = 50% upside",
    buffett_verdict="BUY - Wide moat, excellent management, 50% margin of safety"
)

# Taleb Lens - Antifragility
taleb = TalebAnalysis(
    fragility_assessment="Debt/EBITDA 1.5x, can survive 60% revenue drop",
    tail_risk_exposure=[
        "Regulatory ban (5% prob, catastrophic)",
        "Cyber attack (10% prob, severe)",
        "Key supplier collapse (3% prob, moderate)"
    ],
    optionality_and_asymmetry="Hidden patent portfolio worth $5B, limited downside",
    skin_in_the_game="CEO owns $50M stock (5%), buying consistently",
    hidden_risks=[
        "Customer concentration: Top 3 customers = 40% revenue",
        "Key person dependency on founding CEO"
    ],
    lindy_effect="Business model 100+ years old, proven resilient",
    dependency_chains="Single semiconductor supplier in Taiwan",
    via_negativa=["Exit low-margin consumer business", "Simplify product SKUs"],
    antifragile_rating="Robust (resists stress)",
    taleb_verdict="NEUTRAL - Robust but no asymmetric upside"
)

# Contrarian Lens - Variant Perception
contrarian = ContrarianAnalysis(
    consensus_view="Bear consensus: 'Overvalued growth stock, peak margins'",
    consensus_wrong_because=[
        "Market ignores recurring revenue shift (now 60% of total)",
        "Margins expanding due to AI automation, not one-time cuts",
        "Valuation based on old P/E, should use EV/FCF"
    ],
    hidden_strengths=[
        "Undisclosed partnership with major retailer launching Q4",
        "R&D breakthrough reducing costs 40%",
        "New CEO from Amazon, proven operator"
    ],
    hidden_weaknesses=[
        "Customer churn creeping up: 5% → 7% → 9%",
        "Growth from price increases, not volume"
    ],
    variant_perception="Market sees cyclical peak; I see secular growth inflection",
    market_pricing="30x P/E assumes 5% growth; 15% growth justified",
    catalyst_timeline=[
        "Q3 earnings beat (60 days)",
        "Product launch (90 days)",
        "Analyst upgrade cycle (6 months)"
    ],
    positioning="75% institutional ownership, near peak - creates volatility opportunity",
    contrarian_verdict="STRONG BUY - High conviction against pessimistic consensus",
    conviction_level="High - multiple catalysts, low downside"
)
```

## Error Handling

```python
from fintel.core import (
    DownloadError,
    ConversionError,
    ExtractionError
)

try:
    filing_path = downloader.download("INVALID_TICKER", num_filings=5)
except DownloadError as e:
    logger.error(f"Download failed: {e}")

try:
    text = extractor.extract_text(Path("missing.pdf"))
except ExtractionError as e:
    logger.error(f"Extraction failed: {e}")
```

## Context Managers

```python
# Converter supports context manager
with SECConverter() as converter:
    pdfs = converter.convert("AAPL", filing_path)
    # Browser automatically closed when exiting context
```

## Next Steps

1. **Launch the Web UI**: Run `streamlit run streamlit_app.py` for the easiest experience
2. **Explore the schemas**: Check `src/fintel/analysis/fundamental/models/` and `src/fintel/analysis/perspectives/models/`
3. **Check examples**: Browse `examples/` directory for CLI usage examples
4. **Read the main README**: See `README.md` for comprehensive documentation

## Common Issues

### Issue: "PyPDF2 not installed"
```bash
pip install PyPDF2
```

### Issue: "No API keys found"
Make sure you've created `.env` from `.env.example` and added at least one `GOOGLE_API_KEY_1`

### Issue: "Chrome driver not found"
Selenium will auto-download ChromeDriver. If issues persist, manually download and set `FINTEL_CHROME_DRIVER_PATH`

### Issue: "Permission denied" on directories
The system auto-creates directories. Check that you have write permissions in the project folder.

## Tips

1. **Start small**: Test with 1-2 filings before processing many companies
2. **Use parallel processing**: Add multiple API keys to speed up batch operations
3. **Monitor logs**: Check `./logs/` for detailed execution logs
4. **Cache wisely**: Enable caching to avoid redundant API calls
5. **Type hints**: Use type hints for IDE autocomplete with Pydantic models

Happy analyzing! 🚀
