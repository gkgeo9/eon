# Custom Workflows Developer Guide

This guide explains how to create custom analysis workflows for Fintel. Custom workflows allow you to define specialized prompts and structured output schemas to extract specific insights from SEC filings.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Creating a Workflow](#creating-a-workflow)
5. [Schema Design](#schema-design)
6. [Prompt Engineering](#prompt-engineering)
7. [Advanced Features](#advanced-features)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## Overview

### What are Custom Workflows?

Custom workflows are Python classes that define:
- **A prompt template**: Instructions for the AI to analyze SEC filings
- **A Pydantic schema**: Structured output format for consistent, parseable results
- **Metadata**: Name, description, icon, and requirements for the UI

### How They Work

```
SEC Filing (10-K/10-Q) → PDF Extraction → Your Prompt + Filing Text → Gemini AI → Structured Output (JSON)
```

1. User selects ticker, years, and your workflow in the UI
2. Fintel downloads and extracts the SEC filing text
3. Your prompt template is filled with `{ticker}` and `{year}`
4. The filing text is appended to your prompt
5. Gemini AI generates a response matching your Pydantic schema
6. Results are saved to the database and displayed in the UI

---

## Quick Start

### Step 1: Create a New File

Create a new Python file in `custom_workflows/` or `custom_workflows/examples/`:

```bash
touch custom_workflows/my_analyzer.py
```

### Step 2: Define Your Workflow

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
My Custom Analyzer Workflow.

Brief description of what this workflow does.
"""

from typing import List
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


# Step 2a: Define your output schema
class MyAnalysisResult(BaseModel):
    """Schema for my analysis output."""

    summary: str = Field(
        description="Brief 2-3 sentence summary of findings"
    )

    key_metrics: List[str] = Field(
        description="Top 5 important metrics extracted from the filing"
    )

    score: int = Field(
        ge=0, le=100,
        description="Overall score from 0-100"
    )

    recommendation: str = Field(
        description="'Buy', 'Hold', or 'Sell' recommendation with reasoning"
    )


# Step 2b: Define your workflow class
class MyAnalyzer(CustomWorkflow):
    """Brief description for the workflow."""

    # Required metadata
    name = "My Analyzer"           # Display name in UI dropdown
    description = "Analyzes X, Y, and Z from SEC filings"  # Help text
    icon = "🔍"                    # Emoji for UI
    min_years = 1                  # Minimum years required (1 for single-year)
    category = "custom"            # Category for grouping

    @property
    def prompt_template(self) -> str:
        return """
You are an expert financial analyst reviewing {ticker} for fiscal year {year}.

Analyze the SEC filing and provide:

1. **SUMMARY**: A brief overview of the company's performance
2. **KEY METRICS**: The 5 most important financial metrics
3. **SCORE**: Rate the overall health (0-100)
4. **RECOMMENDATION**: Your investment recommendation

Be specific and cite numbers from the filing.
"""

    @property
    def schema(self):
        return MyAnalysisResult
```

### Step 3: Test Your Workflow

Your workflow will be automatically discovered! Restart the Streamlit app and check:

```bash
streamlit run streamlit_app.py
```

Navigate to Analysis → Select your workflow from the dropdown.

---

## Architecture

### File Structure

```
custom_workflows/
├── __init__.py          # Auto-discovery logic (don't modify)
├── base.py              # CustomWorkflow base class (don't modify)
├── my_workflow.py       # Your workflow (create new files here)
└── examples/
    ├── __init__.py
    ├── growth_analyzer.py    # Example: Growth analysis
    └── option_analyzer.py    # Example: Options strategy
```

### Auto-Discovery

Fintel automatically discovers workflows by:
1. Scanning `custom_workflows/` and `custom_workflows/examples/` for `.py` files
2. Finding classes that inherit from `CustomWorkflow`
3. Registering them with the filename as the workflow ID

**File naming rules:**
- Use lowercase with underscores: `my_analyzer.py`
- Files starting with `_` are ignored
- `base.py` is ignored
- One workflow class per file (recommended)

### Workflow ID

The workflow ID is derived from the filename:
- `growth_analyzer.py` → ID: `growth_analyzer`
- `examples/option_analyzer.py` → ID: `examples.option_analyzer`

---

## Creating a Workflow

### Required Components

Every workflow must define:

| Component | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Display name in UI (e.g., "Growth Analyzer") |
| `description` | `str` | Help text shown in UI |
| `icon` | `str` | Single emoji character |
| `min_years` | `int` | Minimum years required (1+) |
| `prompt_template` | `property` | Prompt with `{ticker}` and `{year}` placeholders |
| `schema` | `property` | Pydantic BaseModel class |

### Optional Components

| Component | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | `str` | `"custom"` | For grouping workflows |

### Metadata Guidelines

```python
class MyWorkflow(CustomWorkflow):
    # Name: 2-4 words, title case
    name = "Competitive Moat Analyzer"

    # Description: One sentence, what it does
    description = "Identifies and rates competitive advantages from 10-K filings"

    # Icon: Single emoji that represents the analysis
    icon = "🏰"  # Castle for "moat"

    # min_years: How many years of data needed?
    min_years = 1   # Single-year analysis
    # min_years = 3   # Multi-year trend analysis
    # min_years = 5   # Long-term historical analysis

    # Category: Group similar workflows
    category = "fundamental"  # Options: fundamental, growth, risk, derivatives, custom
```

---

## Schema Design

The schema defines the structure of your analysis output. Use Pydantic's `BaseModel` with `Field` for descriptions.

### Field Types

```python
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ComprehensiveSchema(BaseModel):
    """Example showing all supported field types."""

    # Simple string
    summary: str = Field(
        description="Brief summary of findings"
    )

    # Constrained integer
    score: int = Field(
        ge=0, le=100,  # Greater/equal 0, less/equal 100
        description="Score from 0-100"
    )

    # Constrained float
    growth_rate: float = Field(
        ge=-1.0, le=10.0,
        description="Growth rate as decimal (-1.0 to 10.0)"
    )

    # Boolean
    is_profitable: bool = Field(
        description="True if company is profitable"
    )

    # List of strings
    risk_factors: List[str] = Field(
        description="Top 3-5 risk factors"
    )

    # List of custom objects
    segments: List[dict] = Field(
        description="List of business segments with name and revenue"
    )

    # Enum/Literal (restricted choices)
    recommendation: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="Investment recommendation"
    )

    # Optional field
    dividend_yield: Optional[float] = Field(
        default=None,
        description="Dividend yield if applicable"
    )
```

### Nested Schemas

For complex outputs, use nested models:

```python
class SegmentAnalysis(BaseModel):
    """Analysis of a single business segment."""
    name: str = Field(description="Segment name")
    revenue: float = Field(description="Revenue in millions")
    growth: float = Field(description="YoY growth rate")
    margin: float = Field(description="Operating margin")


class CompanyAnalysis(BaseModel):
    """Full company analysis with segments."""

    company_summary: str = Field(description="Overall summary")

    segments: List[SegmentAnalysis] = Field(
        description="Analysis of each business segment"
    )

    total_score: int = Field(ge=0, le=100, description="Overall score")
```

### Field Description Best Practices

The `description` in each `Field()` is **critical** - it's used by the AI to understand what to output:

```python
# BAD - Too vague
score: int = Field(description="A score")

# GOOD - Specific and actionable
score: int = Field(
    ge=0, le=100,
    description="Quality score from 0-100 where: "
    "0-30 = Poor (significant issues), "
    "31-60 = Average (some concerns), "
    "61-80 = Good (minor issues), "
    "81-100 = Excellent (best in class)"
)
```

---

## Prompt Engineering

### Prompt Structure

A good prompt has these sections:

```python
@property
def prompt_template(self) -> str:
    return """
You are [ROLE] analyzing {ticker} for fiscal year {year}.

[CONTEXT - What's the goal?]

[INSTRUCTIONS - Numbered list of what to analyze]

1. **SECTION NAME**
   - Specific point to analyze
   - Another point

2. **SECTION NAME**
   - Points...

[OUTPUT GUIDANCE - How to format responses]

[EXAMPLES - Optional but helpful]
"""
```

### Placeholder Variables

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{ticker}` | Company ticker symbol | `AAPL`, `MSFT` |
| `{year}` | Fiscal year | `2024`, `2023` |

The filing text is automatically appended after your prompt.

### Example: Well-Structured Prompt

```python
@property
def prompt_template(self) -> str:
    return """
You are a value investing analyst in the style of Warren Buffett analyzing {ticker} for fiscal year {year}.

Your goal is to determine if this company has durable competitive advantages ("moats").

### ANALYSIS FRAMEWORK

1. **COMPETITIVE MOAT IDENTIFICATION**
   - Network effects: Does the product become more valuable with more users?
   - Switching costs: How hard is it for customers to leave?
   - Cost advantages: Does the company have structural cost benefits?
   - Intangible assets: Patents, brands, regulatory licenses?
   - Efficient scale: Is the market too small for competitors?

2. **MOAT DURABILITY**
   - How long has this advantage existed?
   - What could erode it? (Technology, regulation, competition)
   - Is management investing to maintain/extend it?

3. **FINANCIAL EVIDENCE**
   - Return on invested capital (ROIC) trends
   - Gross and operating margin trends
   - Pricing power evidence
   - Market share data

### OUTPUT REQUIREMENTS

- Be SPECIFIC: Quote exact numbers, percentages, and dollar amounts
- Be BALANCED: Acknowledge both strengths and weaknesses
- Be FORWARD-LOOKING: Consider how moats might evolve

### SCORING GUIDE

- 80-100: Wide moat (dominant, durable advantages)
- 60-79: Narrow moat (some advantages, some risks)
- 40-59: No moat (competing on price/execution)
- 0-39: Negative moat (structural disadvantages)
"""
```

### JSON Examples in Prompts

If you want to show example output, **escape curly braces** by doubling them:

```python
@property
def prompt_template(self) -> str:
    return """
...

### EXAMPLE OUTPUT FORMAT

{{
  "moat_type": "Network Effects",
  "moat_score": 85,
  "reasoning": "The company's marketplace has 50M active users..."
}}

Analyze {ticker} now.
"""
```

---

## Advanced Features

### Multi-Year Analysis

For workflows that compare multiple years:

```python
class TrendAnalyzer(CustomWorkflow):
    name = "5-Year Trend Analyzer"
    min_years = 5  # Requires 5 years of data

    @property
    def prompt_template(self) -> str:
        return """
You are analyzing {ticker} for fiscal year {year}.

This is part of a 5-year trend analysis. Focus on:
- Year-over-year changes
- Compounding effects
- Trend inflection points

The complete trend will be assembled from each year's analysis.
"""
```

### Category-Based Grouping

Group related workflows:

```python
# Fundamental analysis workflows
category = "fundamental"

# Growth-focused workflows
category = "growth"

# Risk analysis workflows
category = "risk"

# Options/derivatives workflows
category = "derivatives"

# Custom/other
category = "custom"
```

### Validation

Add custom validation logic:

```python
def validate_config(self, years: int) -> bool:
    """Custom validation."""
    if years < self.min_years:
        raise ValueError(
            f"{self.name} requires at least {self.min_years} years"
        )
    if years > 10:
        raise ValueError(
            f"{self.name} supports at most 10 years (got {years})"
        )
    return True
```

---

## Best Practices

### DO

1. **Use specific field descriptions** - The AI reads these to understand output format
2. **Constrain numeric fields** - Use `ge`, `le`, `gt`, `lt` for valid ranges
3. **Use Literal for enums** - Restrict to valid choices
4. **Structure prompts clearly** - Use headers, numbered lists, bullet points
5. **Include scoring guides** - Explain what scores mean
6. **Request specific data** - Ask for numbers, percentages, dollar amounts
7. **Test with multiple companies** - Ensure prompts work across industries

### DON'T

1. **Don't use vague descriptions** - "A score" vs "Quality score 0-100 where..."
2. **Don't forget placeholders** - Must include `{ticker}` and `{year}`
3. **Don't make prompts too long** - Stay under ~2000 words
4. **Don't request unavailable data** - 10-K doesn't have real-time data
5. **Don't use single curly braces in examples** - Escape as `{{` and `}}`

### Performance Tips

1. **Smaller schemas = faster processing** - Only request what you need
2. **Fewer list items = more reliable** - Ask for "top 3-5" not "all"
3. **Simple types = fewer errors** - `str` and `int` are most reliable

---

## Troubleshooting

### Workflow Not Appearing in UI

1. Check file is in `custom_workflows/` or `custom_workflows/examples/`
2. Ensure filename doesn't start with `_`
3. Verify class inherits from `CustomWorkflow`
4. Check for Python syntax errors
5. Restart the Streamlit app

### Schema Validation Errors

```python
# Error: "Field required"
# Fix: Ensure all fields have descriptions

score: int = Field(description="...")  # Good
score: int  # Bad - no description
```

### Prompt Errors

```python
# Error: KeyError: 'something'
# Cause: Unescaped curly braces in prompt

# Bad
return "Format: {name: value}"

# Good
return "Format: {{name: value}}"
```

### AI Output Not Matching Schema

1. Make field descriptions more explicit
2. Add example values in descriptions
3. Use `Literal` for restricted choices
4. Simplify nested structures

---

## API Reference

### CustomWorkflow Base Class

```python
class CustomWorkflow(ABC):
    """Base class for custom workflows."""

    # Class attributes (override these)
    name: str = "Custom Workflow"
    description: str = "A custom analysis workflow"
    icon: str = "🔧"
    min_years: int = 1
    category: str = "custom"

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return prompt with {ticker} and {year} placeholders."""
        pass

    @property
    @abstractmethod
    def schema(self) -> Type[BaseModel]:
        """Return Pydantic schema class."""
        pass

    def validate_config(self, years: int) -> bool:
        """Validate configuration. Override for custom logic."""
        pass
```

### Discovery Functions

```python
from custom_workflows import (
    discover_workflows,  # Force re-scan
    get_workflow,        # Get by ID
    list_workflows,      # List all with metadata
    reload_workflows,    # Force reload all
)

# List all workflows
workflows = list_workflows()
# Returns: [{"id": "...", "name": "...", "description": "...", ...}, ...]

# Get specific workflow
workflow_class = get_workflow("growth_analyzer")
workflow = workflow_class()
print(workflow.prompt_template)
```

---

## Complete Example: Dividend Analyzer

Here's a complete, production-ready workflow:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dividend Safety Analyzer Workflow.

Analyzes dividend sustainability, payout safety, and yield attractiveness.
Useful for income-focused investors.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class DividendMetrics(BaseModel):
    """Key dividend metrics."""
    dividend_per_share: float = Field(description="Annual dividend per share in USD")
    payout_ratio: float = Field(ge=0, le=2.0, description="Dividend payout ratio (dividends / earnings)")
    fcf_payout_ratio: float = Field(ge=0, le=2.0, description="Dividend / Free Cash Flow ratio")
    years_of_increases: int = Field(ge=0, description="Consecutive years of dividend increases")
    yield_estimate: float = Field(ge=0, le=0.30, description="Approximate dividend yield (0.00-0.30)")


class DividendAnalysisResult(BaseModel):
    """Schema for dividend safety analysis."""

    metrics: DividendMetrics = Field(
        description="Key dividend metrics extracted from the filing"
    )

    dividend_policy: str = Field(
        description="Company's stated dividend policy from the filing. "
        "Include any capital allocation priorities mentioned."
    )

    cash_flow_analysis: str = Field(
        description="Assessment of free cash flow coverage. "
        "Include FCF amounts and trend over recent years."
    )

    balance_sheet_strength: str = Field(
        description="Assessment of debt levels and liquidity. "
        "Include debt-to-equity, interest coverage, and cash position."
    )

    earnings_stability: str = Field(
        description="Analysis of earnings consistency. "
        "Cyclical or stable? Growing or declining?"
    )

    risks_to_dividend: List[str] = Field(
        description="Top 3-5 risks that could cause a dividend cut"
    )

    safety_score: int = Field(
        ge=0, le=100,
        description="Dividend safety score 0-100: "
        "0-30=High cut risk, 31-50=Some risk, 51-70=Relatively safe, "
        "71-85=Very safe, 86-100=Extremely safe"
    )

    growth_potential: Literal["None", "Low", "Moderate", "High"] = Field(
        description="Potential for future dividend increases"
    )

    recommendation: Literal[
        "Avoid - High cut risk",
        "Caution - Monitor closely",
        "Hold - Adequate for income",
        "Buy - Attractive income opportunity"
    ] = Field(
        description="Investment recommendation for income investors"
    )

    summary: str = Field(
        description="2-3 sentence summary of dividend attractiveness and safety"
    )


class DividendSafetyAnalyzer(CustomWorkflow):
    """Analyzes dividend safety and sustainability."""

    name = "Dividend Safety Analyzer"
    description = "Evaluate dividend sustainability, payout safety, and growth potential"
    icon = "💰"
    min_years = 1
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        return """
You are an income-focused investment analyst evaluating {ticker} for fiscal year {year}.

Your goal is to assess the SAFETY and SUSTAINABILITY of the dividend.

### ANALYSIS FRAMEWORK

1. **DIVIDEND METRICS**
   - Current dividend per share and any recent changes
   - Payout ratio (Dividends / Net Income)
   - FCF Payout ratio (Dividends / Free Cash Flow) - MORE IMPORTANT
   - Historical dividend growth rate
   - Consecutive years of increases (Dividend Aristocrat status?)

2. **CASH FLOW COVERAGE**
   - Free Cash Flow trend (growing, stable, declining?)
   - FCF margin and consistency
   - Capital expenditure requirements
   - Working capital needs

3. **BALANCE SHEET STRENGTH**
   - Debt-to-Equity ratio
   - Interest coverage ratio
   - Cash and liquid investments
   - Debt maturity schedule
   - Credit rating if mentioned

4. **EARNINGS QUALITY**
   - Earnings stability (cyclical or stable?)
   - Revenue diversity (concentrated or diversified?)
   - Competitive position (moat strength)
   - Growth trajectory

5. **DIVIDEND POLICY**
   - Stated policy (% of earnings, % of FCF, absolute amount?)
   - Management commitment to dividend
   - Share buyback competition for capital

### SCORING GUIDE (Safety Score)

- 86-100: Fortress balance sheet, FCF payout <50%, growing earnings
- 71-85: Strong coverage, FCF payout 50-70%, stable earnings
- 51-70: Adequate coverage, FCF payout 70-90%, some cyclicality
- 31-50: Stretched coverage, FCF payout >90%, cyclical/declining
- 0-30: Dividend at risk, FCF doesn't cover, deteriorating business

### IMPORTANT

- Focus on FREE CASH FLOW, not accounting earnings
- A dividend can be unsafe even if "covered" by earnings
- Look for warning signs: rising debt, declining FCF, one-time items
- Quote specific dollar amounts and percentages
"""

    @property
    def schema(self):
        return DividendAnalysisResult
```

---

## Need Help?

- **Example workflows**: See `custom_workflows/examples/`
- **Base class**: See `custom_workflows/base.py`
- **Discovery logic**: See `custom_workflows/__init__.py`
- **Integration**: See `fintel/ui/services/analysis_service.py`

Happy analyzing! 🎯
