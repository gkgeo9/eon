#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example: Growth Analyzer Workflow

Analyzes company growth patterns and sustainability.
This serves as a template for creating your own custom workflows.
"""

from typing import List
from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow


class GrowthAnalysisResult(BaseModel):
    """Schema for growth analysis output."""

    revenue_growth_analysis: str = Field(
        description="Analysis of revenue growth trends over the period. "
        "Include CAGR calculation and key drivers."
    )

    growth_sustainability: str = Field(
        description="Assessment of whether current growth rate is sustainable. "
        "Consider market size, competitive dynamics, and execution capacity."
    )

    growth_quality_score: int = Field(
        ge=0, le=100,
        description="Score from 0-100 rating the quality of growth "
        "(organic vs acquired, profitable vs unprofitable)"
    )

    key_growth_drivers: List[str] = Field(
        description="Top 3-5 factors driving growth"
    )

    growth_risks: List[str] = Field(
        description="Top 3-5 risks to continued growth"
    )

    verdict: str = Field(
        description="Overall assessment: 'Accelerating', 'Sustainable', "
        "'Decelerating', or 'Unsustainable'"
    )


class GrowthAnalyzer(CustomWorkflow):
    """Analyzes company growth patterns and sustainability."""

    name = "Growth Analyzer"
    description = "Analyze revenue growth patterns, sustainability, and quality"
    icon = "📈"
    min_years = 3  # Need multiple years to see trends
    category = "growth"

    @property
    def prompt_template(self) -> str:
        return """
You are a growth investing analyst analyzing {ticker} for fiscal year {year}.

Analyze the company's growth characteristics focusing on:

1. REVENUE GROWTH ANALYSIS
   - Calculate year-over-year growth rates
   - Identify organic vs inorganic (M&A) growth
   - Break down growth by segment/geography if available

2. GROWTH SUSTAINABILITY
   - Market size and penetration (TAM/SAM/SOM)
   - Competitive position and market share trends
   - Customer acquisition and retention metrics

3. GROWTH QUALITY
   - Is growth profitable? (unit economics)
   - Is growth capital efficient? (CAC payback, LTV/CAC)
   - Is growth diversified or concentrated?

4. KEY DRIVERS & RISKS
   - What's driving growth? (products, markets, pricing)
   - What could derail growth? (competition, saturation, execution)

Be specific with numbers and percentages. Use data from the filing.
"""

    @property
    def schema(self):
        return GrowthAnalysisResult
