# Experimentation Module

Simple scripts for custom SEC filing analysis with AI.

## Overview

This module provides **simple, straightforward scripts** to extract custom information from SEC filings using:
- Gemini 3 with HIGH thinking level
- Google Search tool for external research
- Pydantic schemas for structured output
- Existing Fintel infrastructure (downloader, converter, extractor)

## Quick Start

### 1. Simple Leadership Extraction

Extract all directors and executives from a 14A proxy statement:

```bash
python experimentation/simple_leadership_extract.py AAPL
```

This will:
1. Download the latest DEF 14A filing
2. Convert to PDF and extract text
3. Analyze with Gemini 3 + Google Search
4. Output structured JSON with all leadership data

Output saved to: `data/experimentation/leadership/{TICKER}_leadership.json`

### 2. Custom Analysis Template

Copy and customize for your own analysis:

```bash
python experimentation/custom_analysis_template.py AAPL
python experimentation/custom_analysis_template.py MSFT "10-K"
```

**To customize:**
1. Open `custom_analysis_template.py`
2. Modify the `YourCustomAnalysis` Pydantic schema
3. Update the `build_prompt()` function
4. Run the script

## How It Works

All scripts follow this simple pattern:

```python
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor

# 1. Define what you want to extract (Pydantic schema)
class MyAnalysis(BaseModel):
    company: str = Field(description="Company name")
    summary: str = Field(description="Summary of findings")

# 2. Download the filing
downloader = SECDownloader(company_name="Research", user_email="you@email.com")
filing_path = downloader.download("AAPL", num_filings=1, filing_type="DEF 14A")

# 3. Convert and extract text
converter = SECConverter()
pdfs = converter.convert("AAPL", filing_path, filing_type="DEF 14A")

extractor = PDFExtractor()
text = extractor.extract_text(pdfs[0]['pdf_path'])

# 4. Analyze with Gemini 3 + Google Search
client = genai.Client(api_key="YOUR_KEY")

response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents=f"Analyze this filing:\n\n{text}",
    config=types.GenerateContentConfig(
        thinkingConfig={'thinkingLevel': 'HIGH'},
        tools=[types.Tool(googleSearch=types.GoogleSearch())],
        response_mime_type="application/json",
        response_schema=MyAnalysis,
    ),
)

# 5. Get structured JSON output
result = MyAnalysis.model_validate_json(response.text)
print(result.model_dump_json(indent=2))
```

## Available Scripts

### 1. `simple_leadership_extract.py`
Extracts directors and executives from 14A filings with:
- Name, title, role type
- Age, tenure, compensation
- Background, education
- Other boards, independence status
- Google Search for verification

### 2. `custom_analysis_template.py`
Template for creating your own custom analysis:
- Modify Pydantic schema for what you want
- Update prompt for your specific needs
- Works with any SEC filing type (14A, 10-K, 10-Q, etc.)

### 3. Existing complex scripts (optional)
- `leadership_extractor.py` - Full class-based framework
- `example_usage.py` - Examples of different use cases
- `schemas.py` - Pydantic models

## Example Use Cases

### Extract Risk Factors from 10-K
```python
# Modify custom_analysis_template.py:

class RiskAnalysis(BaseModel):
    company: str
    risk_factors: List[str] = Field(description="All risk factors mentioned")
    top_risks: List[str] = Field(description="Top 5 most critical risks")
    risk_trends: str = Field(description="Are risks increasing or decreasing?")

# Then run:
python experimentation/custom_analysis_template.py AAPL "10-K"
```

### Extract Executive Compensation Trends
```python
class CompensationAnalysis(BaseModel):
    company: str
    executives: List[dict]  # Name, title, total comp
    ceo_pay_ratio: float = Field(description="CEO to median employee pay ratio")
    pay_trends: str = Field(description="How comp changed vs last year")
```

### Extract M&A Activity from 8-K
```python
class MandAAnalysis(BaseModel):
    company: str
    acquisitions: List[dict]  # Target, price, date, rationale
    divestitures: List[dict]
    strategic_rationale: str
```

## Files Structure

```
experimentation/
├── README.md                          # This file
├── simple_leadership_extract.py       # Simple leadership extraction
├── custom_analysis_template.py        # Template for custom analysis
├── schemas.py                         # Pydantic schemas (optional)
├── leadership_extractor.py            # Full class-based framework (optional)
└── example_usage.py                   # Example use cases (optional)
```

**Start with:** `simple_leadership_extract.py` or `custom_analysis_template.py`

**Advanced users:** Use `leadership_extractor.py` for more complex workflows

## Configuration

Make sure your `.env` file has:

```bash
FINTEL_GOOGLE_API_KEYS=["your-gemini-api-key"]
FINTEL_SEC_COMPANY_NAME="Your Name"
FINTEL_SEC_USER_EMAIL="your@email.com"
```

## Tips

1. **Start simple**: Use `simple_leadership_extract.py` to see how it works
2. **Customize**: Copy `custom_analysis_template.py` and modify the schema + prompt
3. **Iterate**: Start with small prompts, then add more detail as needed
4. **Use Google Search**: Enable it for external verification and context
5. **Pydantic schemas**: Be specific with Field descriptions - the AI uses them

## Common Patterns

### Extract lists of things
```python
class MyAnalysis(BaseModel):
    items: List[str] = Field(description="All items matching criteria X")
```

### Extract structured data
```python
class Person(BaseModel):
    name: str
    role: str

class MyAnalysis(BaseModel):
    people: List[Person] = Field(description="All people mentioned")
```

### Extract with analysis
```python
class MyAnalysis(BaseModel):
    raw_data: List[str] = Field(description="Extract all X")
    analysis: str = Field(description="What does this mean?")
    recommendation: str = Field(description="What should investors know?")
```

## Supported Filing Types

Works with any SEC filing type:
- **DEF 14A** - Proxy statements (governance, compensation)
- **10-K** - Annual reports (financials, risks, operations)
- **10-Q** - Quarterly reports (earnings, updates)
- **8-K** - Current events (M&A, leadership changes)
- **S-1** - IPO registrations
- **13F** - Institutional holdings
- **4** - Insider transactions
