# Fintel - Financial Intelligence Platform

**Complete, standalone platform for AI-powered SEC 10-K analysis and investment research.**

Synthesizes functionality from `standardized_sec_ai` and `10K_automator` into a production-ready system.

---

## 🚀 Quick Start (When You Come Back)

### 1. Setup Environment

```bash
cd /Users/gkg/PycharmProjects/stock_stuff_06042025/fintel

# Activate your virtual environment
source /path/to/venv/bin/activate

# Install (if not already installed)
pip install -e ".[dev]"
```

### 2. Configure API Keys

Create or edit `.env`:

```bash
# Google Gemini API keys (supports multiple for parallel processing)
GOOGLE_API_KEY_1=your_key_here
GOOGLE_API_KEY_2=your_key_2  # Optional: add more for parallel processing
GOOGLE_API_KEY_3=your_key_3

# SEC Edgar (required for downloading filings)
FINTEL_SEC_USER_EMAIL=your@email.com
FINTEL_SEC_COMPANY_NAME="Research Script"
```

### 3. Run Your First Analysis

```bash
cd examples

# Option A: Basic fundamental analysis
python 01_basic_fundamental_analysis.py

# Option B: Analyze an excellent company
python 02_excellent_company_analysis.py

# Option C: Analyze an unknown company
python 03_random_company_analysis.py

# Option D: Contrarian scanning
python 04_contrarian_scanning.py
```

---

## 📖 Core Concepts

### Two Analysis Paths (CRITICAL)

Fintel provides **TWO DIFFERENT** analysis approaches:

#### 1. **Excellent Company Analysis** → For Known Winners
- **Use when**: Analyzing proven compounders, top 50 performers, companies you want to learn from
- **Prompt bias**: SUCCESS-FOCUSED - assumes company was successful
- **Output**: `ExcellentCompanyFactors` - identifies what made them succeed
- **Directory**: `excellent_company_factors/`
- **Example**: Apple, Microsoft, Google

```python
from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer

analyzer = ExcellentCompanyAnalyzer(api_key_manager, rate_limiter)
result = analyzer.analyze_from_directory(
    ticker="AAPL",
    analyses_dir=Path("analyzed_10k/AAPL"),
    output_dir=Path("excellent_company_factors")
)

# Access success-focused insights
print(result.unique_attributes)  # What made them unique
print(result.success_factors)     # Key success drivers
```

#### 2. **Objective Company Analysis** → For Unknown Companies
- **Use when**: Researching random companies, unbiased screening
- **Prompt bias**: OBJECTIVE/BALANCED - no assumption of success or failure
- **Output**: `CompanySuccessFactors` - identifies both strengths AND weaknesses
- **Directory**: `random_company_factors/`
- **Example**: Companies you're discovering for the first time

```python
from fintel.analysis.fundamental.success_factors import ObjectiveCompanyAnalyzer

analyzer = ObjectiveCompanyAnalyzer(api_key_manager, rate_limiter)
result = analyzer.analyze_from_directory(
    ticker="XYZ",
    analyses_dir=Path("analyzed_10k/XYZ"),
    output_dir=Path("random_company_factors")
)

# Access balanced assessment
print(result.distinguishing_characteristics)
print(result.performance_factors)
```

### Compounder DNA Scoring System

Both analysis paths can be compared against the **Top 50 Baseline** using the COMPOUNDER DNA SCORING:

- **90-100**: Future Compounder - Exceptional alignment with top performers
- **75-89**: Strong Potential - Significant alignment, foundation present
- **60-74**: Developing Contender - Meaningful elements with room to grow
- **40-59**: Partial Alignment - Some positive elements, lacks cohesive pattern
- **20-39**: Limited Alignment - Minimal resemblance to compounders
- **0-19**: Misaligned - Counter to top performer patterns

```python
from fintel.analysis.comparative.benchmarking import BenchmarkComparator

comparator = BenchmarkComparator(
    baseline_path=Path("top_50_meta_analysis.json"),
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

comparison = comparator.compare_against_baseline(
    success_factors=result  # From either analyzer
)

print(f"Score: {comparison.compounder_potential.score}/100")
print(f"Category: {comparison.compounder_potential.category}")
```

---

## 🎯 Features

### Core Capabilities

1. **SEC 10-K Analysis**
   - Download filings from SEC Edgar
   - Convert HTML to markdown
   - AI-powered extraction and analysis
   - Pydantic-validated outputs

2. **Multi-Year Success Factor Analysis**
   - Analyze 10+ years of filings
   - Identify business model evolution
   - Track performance patterns
   - TWO analysis paths (excellent vs objective)

3. **Comparative Benchmarking**
   - Compare against top 50 proven winners
   - COMPOUNDER DNA SCORING SYSTEM
   - Detailed factor-by-factor alignment
   - Investment considerations and risks

4. **Contrarian Scanner**
   - Identify hidden gems
   - Six contrarian dimensions
   - Evidence-based scoring (0-600 scale)
   - Find variant perception opportunities

5. **Multi-Perspective Analysis**
   - Warren Buffett lens (moat, management, value)
   - Nassim Taleb lens (fragility, tail risks, antifragility)
   - Contrarian lens (hidden opportunities, variant perception)

### Technical Features

- **Type-Safe**: Pydantic models throughout - no JSON parsing errors
- **Parallel Processing**: Support for 25+ API keys
- **Progress Tracking**: Resume interrupted batch jobs
- **Efficient Storage**: Parquet format (10-100x compression)
- **Production-Ready**: Comprehensive logging, error handling
- **Extensible**: Clean architecture, easy to extend

---

## 📂 Project Structure

```
fintel/
├── src/fintel/
│   ├── core/                    # Configuration, logging, exceptions
│   ├── data/
│   │   ├── sources/sec/         # SEC download, convert, extract
│   │   └── storage/             # JSON, Parquet storage
│   ├── analysis/
│   │   ├── fundamental/
│   │   │   ├── analyzer.py               # Basic 10-K analysis
│   │   │   ├── success_factors.py        # DUAL ANALYZERS (excellent & objective)
│   │   │   ├── models/
│   │   │   │   ├── basic.py              # TenKAnalysis
│   │   │   │   ├── success_factors.py    # CompanySuccessFactors (objective)
│   │   │   │   └── excellent_company_factors.py  # ExcellentCompanyFactors
│   │   │   └── prompts/
│   │   │       ├── basic.py
│   │   │       ├── success_factors.py              # Objective prompt
│   │   │       └── excellent_company_factors.py    # Success-focused prompt
│   │   ├── perspectives/        # Buffett, Taleb, Contrarian lenses
│   │   ├── comparative/
│   │   │   ├── benchmarking.py           # Compare to top 50
│   │   │   ├── contrarian_scanner.py     # Find hidden gems
│   │   │   ├── models/
│   │   │   │   ├── benchmark_comparison.py   # Full scoring framework
│   │   │   │   └── contrarian_scores.py
│   │   │   └── prompts/
│   │   │       ├── benchmark_comparison.py   # Compounder DNA scoring
│   │   │       └── contrarian_scanner.py
│   │   └── options/             # Options analysis
│   ├── ai/                      # LLM providers, key management, rate limiting
│   ├── processing/              # Parallel execution, progress tracking
│   ├── workflows/               # High-level orchestration
│   │   └── comparative.py       # Complete analysis workflows
│   └── cli/                     # Command-line interface
├── examples/                    # **START HERE**
│   ├── 01_basic_fundamental_analysis.py
│   ├── 02_excellent_company_analysis.py
│   ├── 03_random_company_analysis.py
│   └── 04_contrarian_scanning.py
└── tests/                       # Unit tests
```

---

## 🔄 Complete Workflows

### Workflow 1: Analyze Excellent Company

**Use for**: Top 50 compounders, known winners you want to learn from

```python
from fintel.workflows import ComparativeAnalysisWorkflow

workflow = ComparativeAnalysisWorkflow(
    api_key_manager=key_mgr,
    rate_limiter=rate_limiter,
    baseline_path=Path("top_50_meta_analysis.json")
)

# Complete pipeline: Download → Analyze → Success Factors → Compare to Top 50
result = workflow.analyze_excellent_company(
    ticker="AAPL",
    num_years=10,
    output_dir=Path("output/AAPL")
)

# Outputs:
# - output/AAPL/filings/*.htm
# - output/AAPL/analyses/*_analysis.json
# - output/AAPL/success_factors/AAPL_success_factors.json  (excellent prompt)
# - output/AAPL/comparisons/AAPL_benchmark_comparison.json
```

### Workflow 2: Analyze Random Company

**Use for**: Unknown companies, unbiased screening

```python
# Same workflow, different analysis path
result = workflow.analyze_random_company(
    ticker="XYZ",
    num_years=10,
    output_dir=Path("output/XYZ")
)

# Outputs:
# - output/XYZ/success_factors/XYZ_success_factors.json  (objective prompt)
# - output/XYZ/comparisons/XYZ_benchmark_comparison.json
```

### Workflow 3: Batch Contrarian Scan

**Use for**: Finding hidden gems across many companies

```python
results = workflow.batch_contrarian_scan(
    tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    output_dir=Path("contrarian_scans"),
    resume=True  # Resume from progress.json if interrupted
)

# Outputs:
# - contrarian_scans/{TICKER}_contrarian.json (for each)
# - contrarian_scans/progress.json (resume file)
```

---

## 💡 Common Use Cases

### Use Case 1: Study Top Performers

**Goal**: Learn what made great companies succeed

```python
# 1. Analyze with excellent company prompt
analyzer = ExcellentCompanyAnalyzer(api_key_manager, rate_limiter)
factors = analyzer.analyze_from_directory("AAPL", analyses_dir, output_dir)

# 2. Review success factors
for factor in factors.success_factors:
    print(f"{factor.factor}: {factor.importance}")

# 3. Compare to top 50 to see patterns
comparator = BenchmarkComparator(baseline_path, api_key_manager, rate_limiter)
comparison = comparator.compare_against_baseline(factors)
```

### Use Case 2: Screen for Compounders

**Goal**: Find companies with compounder potential

```python
# 1. Analyze objectively (no bias)
analyzer = ObjectiveCompanyAnalyzer(api_key_manager, rate_limiter)
factors = analyzer.analyze_from_directory("XYZ", analyses_dir, output_dir)

# 2. Score against top 50
comparator = BenchmarkComparator(baseline_path, api_key_manager, rate_limiter)
comparison = comparator.compare_against_baseline(factors)

# 3. Filter by score
if comparison.compounder_potential.score >= 75:
    print(f"⭐ Strong compounder potential!")
    print(comparison.compounder_potential.distinctive_strengths)
```

### Use Case 3: Find Contrarian Opportunities

**Goal**: Identify mispriced companies with hidden strengths

```python
scanner = ContrarianScanner(api_key_manager, rate_limiter)
contrarian = scanner.analyze_from_directory(ticker, analyses_dir, output_file)

# Review contrarian scores
if contrarian.total_score >= 400:  # High contrarian potential
    print(f"🔍 Contrarian opportunity!")
    print(f"Strategic Anomaly: {contrarian.strategic_anomaly.score}/100")
    print(f"Asymmetric Resources: {contrarian.asymmetric_resources.score}/100")
```

---

## 📊 Understanding the Outputs

### 1. TenKAnalysis (Basic Fundamental)

Single-year 10-K analysis:

```python
{
    "ticker": "AAPL",
    "fiscal_year": 2024,
    "business_model": "...",
    "revenue_streams": [...],
    "competitive_advantages": [...],
    "key_risks": [...],
    "management_quality": {...},
    "financial_highlights": {...}
}
```

### 2. ExcellentCompanyFactors (Success-Focused)

Multi-year analysis for known winners:

```python
{
    "company_name": "AAPL",
    "years_analyzed": ["2024", "2023", "2022", ...],
    "business_evolution": {...},
    "success_factors": [
        {
            "factor": "Ecosystem lock-in",
            "importance": "...",
            "evolution": "..."
        }
    ],
    "unique_attributes": [
        "Vertical integration of hardware and software",
        "Premium brand with pricing power",
        ...
    ],
    "competitive_advantages": [...],
    "management_excellence": {...}
}
```

### 3. CompanySuccessFactors (Objective)

Multi-year analysis for unknown companies:

```python
{
    "company_name": "XYZ",
    "period_analyzed": ["2024", "2023", ...],
    "business_model": {...},
    "performance_factors": [
        {
            "factor": "...",
            "business_impact": "...",
            "development": "..."
        }
    ],
    "financial_metrics": {...},
    "market_position": [...],
    "distinguishing_characteristics": [...],
    "forward_outlook": {...}
}
```

### 4. BenchmarkComparison (Compounder DNA)

Comparison against top 50:

```python
{
    "company_name": "AAPL",
    "compounder_potential": {
        "score": 92,  # 0-100
        "category": "Future Compounder",
        "summary": "...",
        "distinctive_strengths": [...],
        "critical_gaps": [...]
    },
    "success_factor_alignment": [...],
    "leadership_assessment": {...},
    "financial_patterns_assessment": {...},
    "final_assessment": {
        "verdict": "...",
        "probability_of_outperformance": "High",
        ...
    }
}
```

### 5. ContrarianAnalysis

Six contrarian dimensions (0-600 total):

```python
{
    "ticker": "XYZ",
    "total_score": 425,  # Out of 600
    "category": "High Contrarian Potential",
    "strategic_anomaly": {"score": 85, ...},
    "asymmetric_resources": {"score": 72, ...},
    "contrarian_positioning": {"score": 68, ...},
    "cross_industry_dna": {"score": 80, ...},
    "early_infrastructure": {"score": 65, ...},
    "intellectual_capital": {"score": 55, ...},
    "synthesis": "..."
}
```

---

## 🛠️ CLI Usage

```bash
# Analyze single company
fintel analyze AAPL --years 10

# Batch process
echo -e "AAPL\nMSFT\nGOOGL" > tickers.txt
fintel batch tickers.txt --workers 10

# Contrarian scan
fintel scan --tickers-file tickers.txt --min-score 400

# Export results
fintel export --format parquet --output results.parquet
```

---

## 🔧 Configuration

All settings via `.env` or environment variables:

```bash
# API Keys
GOOGLE_API_KEY_1=...
GOOGLE_API_KEY_2=...

# SEC Edgar
FINTEL_SEC_USER_EMAIL=your@email.com
FINTEL_SEC_COMPANY_NAME="Research"

# Processing
FINTEL_NUM_WORKERS=25
FINTEL_NUM_FILINGS_PER_COMPANY=30

# Paths
FINTEL_DATA_DIR=./data
FINTEL_CACHE_DIR=./cache
FINTEL_LOG_DIR=./logs
```

---

## 📈 Performance

- **Parallel Processing**: 25 workers with API key rotation
- **Rate Limiting**: Automatic 65s sleep between requests per key
- **Storage**: Parquet format (10-100x compression vs JSON)
- **Resume**: Progress tracking for interrupted batch jobs
- **Efficiency**: Process 1,000+ companies with proper API management

---

## 🎓 Learning Resources

### Start Here
1. Read this README fully
2. Run examples/01_basic_fundamental_analysis.py
3. Run examples/02_excellent_company_analysis.py
4. Run examples/03_random_company_analysis.py
5. Explore the models in `src/fintel/analysis/fundamental/models/`

### Key Concepts
- **Dual Analysis Paths**: Understand when to use excellent vs objective
- **Compounder DNA**: Learn the 90-100 scoring framework
- **Contrarian Signals**: Six dimensions of hidden potential
- **Pydantic Models**: Type-safe data structures

---

## ⚠️ Important Notes

### When to Use Each Analyzer

✅ **Use ExcellentCompanyAnalyzer** when:
- Analyzing top 50 compounders
- Studying known successful companies
- Learning success patterns
- You want SUCCESS-FOCUSED insights

✅ **Use ObjectiveCompanyAnalyzer** when:
- Screening unknown companies
- Researching random stocks
- You want BALANCED assessment
- No prior bias about success/failure

### API Usage

- Requires Google Gemini API keys
- Thinking budget: 4096 tokens (deep analysis)
- Rate limiting: 65 seconds between requests per key
- Support for 25+ keys in parallel

### Data Sources

- SEC Edgar for 10-K filings
- Requires email for SEC API
- Filings cached locally

---

## 🚧 Troubleshooting

### "No API key found"
```bash
# Check .env file exists
cat .env

# Verify keys are set
echo $GOOGLE_API_KEY_1
```

### "Baseline file not found"
```bash
# Ensure you have the top 50 meta-analysis
ls top_50_meta_analysis.json

# Or specify path explicitly
comparator = BenchmarkComparator(
    baseline_path=Path("/full/path/to/top_50_meta_analysis.json"),
    ...
)
```

### "No analyses found"
```bash
# Check analyses directory exists
ls analyzed_10k/AAPL/

# Should contain: AAPL_2024_analysis.json, AAPL_2023_analysis.json, etc.
```

---

## 📝 Changelog

### Latest Updates (Current)
- ✅ Restored dual analysis paths (excellent vs random)
- ✅ Complete benchmark comparator with COMPOUNDER DNA SCORING
- ✅ Comprehensive workflows module
- ✅ Full examples for all use cases
- ✅ This excellent README!

### Previous
- ✅ Multi-perspective analysis (Buffett, Taleb, Contrarian)
- ✅ Contrarian scanner with 6-dimension scoring
- ✅ Parallel processing with 25 workers
- ✅ Pydantic models throughout
- ✅ CLI interface

---

## 🎯 Next Steps

Now that you have this README:

1. **Set up your environment** (API keys in `.env`)
2. **Run Example 1** (basic analysis)
3. **Run Example 2** (excellent company - use for top performers)
4. **Run Example 3** (random company - use for screening)
5. **Explore the models** to understand data structures
6. **Build your own workflows** using the components

**You can now archive `standardized_sec_ai` and `10K_automator` folders.**
Everything is in Fintel! 🎉

---

**License**: Private - For personal use only
**Author**: Built by synthesizing standardized_sec_ai and 10K_automator
**Purpose**: Investment research and education

**⚠️ Disclaimer**: This platform is for research purposes. Always conduct your own due diligence before making investment decisions.
