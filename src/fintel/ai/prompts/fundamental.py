#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prompt templates for fundamental analysis of 10-K filings.

Templates use .format() with {company_name} and {year} placeholders.
"""

# Default comprehensive 10-K analysis prompt
DEFAULT_10K_PROMPT = """
You are analyzing the 10-K filing of {company_name} for fiscal year {year}.
Provide a comprehensive analysis synthesizing this company's operations and performance.
Identify the good, bad, and ugly.

Your response will be validated against a structured schema, so ensure all required fields are provided.
"""

# Deep dive prompt focused on revenue and operational metrics
DEEP_DIVE_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} with focus on revenue composition and operational metrics.

Focus on:
- Revenue segments and their growth trends
- Geographic breakdown and international expansion
- Capital allocation (capex trends, acquisitions)
- R&D intensity and innovation investments
- Competitive moats and barriers to entry

Be specific with numbers from the filing. Quote actual figures where available.
"""

# Focused analysis on business model sustainability
FOCUSED_ANALYSIS_PROMPT = """
Analyze {company_name}''s 10-K for fiscal year {year} focusing on long-term sustainability.

Key areas:
- Business model sustainability and resilience
- Competitive positioning vs peers
- Financial health (debt, cash flow, margins)
- Risk assessment (operational, market, regulatory)
- Management quality and capital allocation

Be honest about weaknesses. Identify potential threats to the business model.
"""

# Industry-specific prompt for EV manufacturers
EV_MANUFACTURER_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} from an EV manufacturer perspective.

Focus on:
- Vehicle production capacity (current and planned expansions)
- Battery technology and supply chain (in-house vs partnerships)
- Charging infrastructure strategy
- R&D spending and technological priorities
- Government incentive dependencies
- Key operational metrics (deliveries, ASP, gross margins)

Be specific with production numbers, capacity figures, and financial metrics.
"""

# All available prompts mapped by name
PROMPTS = {
    'default': DEFAULT_10K_PROMPT,
    'deep_dive': DEEP_DIVE_PROMPT,
    'focused': FOCUSED_ANALYSIS_PROMPT,
    'ev_manufacturer': EV_MANUFACTURER_PROMPT,
}


def get_prompt(name: str = 'default') -> str:
    """
    Get a prompt template by name.

    Args:
        name: Prompt name (default, deep_dive, focused, ev_manufacturer)

    Returns:
        Prompt template string

    Raises:
        KeyError: If prompt name not found
    """
    if name not in PROMPTS:
        available = ', '.join(PROMPTS.keys())
        raise KeyError(f"Prompt '{name}' not found. Available: {available}")

    return PROMPTS[name]


def format_prompt(
    prompt_template: str,
    company_name: str,
    year: int
) -> str:
    """
    Format a prompt template with company name and year.

    Args:
        prompt_template: Template string with {company_name} and {year}
        company_name: Company name or ticker
        year: Fiscal year

    Returns:
        Formatted prompt string
    """
    return prompt_template.format(company_name=company_name, year=year)
