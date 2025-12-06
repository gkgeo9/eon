#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prompt templates for basic fundamental analysis of 10-K filings.

Templates use .format() with {company_name} and {year} placeholders.
"""

# Default comprehensive 10-K analysis prompt
DEFAULT_10K_PROMPT = """
You are analyzing the 10-K filing of {company_name} for fiscal year {year}.
Provide a comprehensive analysis synthesizing this company's operations and performance.
Identify the good, bad, and ugly.

CRITICAL ANALYSIS GUIDELINES:
- Base your analysis exclusively on the information provided in the 10-K filing
- Present a balanced assessment that includes both favorable and unfavorable aspects
- Support observations with specific data points and metrics whenever possible
- Do not assume the company is either successful or unsuccessful - analyze objectively
- Avoid subjective judgments unless directly supported by evidence
- Identify both strengths and weaknesses with equal attention to detail

Your response will be validated against a structured Pydantic schema, so ensure all required fields are provided.
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

CRITICAL: Provide evidence-based analysis. Every claim must be supported by data from the filing.
"""

# Focused analysis on business model sustainability
FOCUSED_ANALYSIS_PROMPT = """
Analyze {company_name}'s 10-K for fiscal year {year} focusing on long-term sustainability.

Key areas:
- Business model sustainability and resilience
- Competitive positioning vs peers
- Financial health (debt, cash flow, margins)
- Risk assessment (operational, market, regulatory)
- Management quality and capital allocation

Be honest about weaknesses. Identify potential threats to the business model.

CRITICAL: Balance positive and negative findings. Do not cherry-pick only good or only bad aspects.
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

CRITICAL: Use actual data from the filing. Avoid speculation or assumptions.
"""


__all__ = [
    'DEFAULT_10K_PROMPT',
    'DEEP_DIVE_PROMPT',
    'FOCUSED_ANALYSIS_PROMPT',
    'EV_MANUFACTURER_PROMPT',
]
