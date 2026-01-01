#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management Quality Analyzer Workflow.

Evaluates management quality, capital allocation track record,
and corporate governance from SEC filings.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class CompensationAnalysis(BaseModel):
    """Executive compensation breakdown."""
    ceo_total_comp: Optional[float] = Field(
        default=None,
        description="CEO total compensation in millions USD"
    )
    comp_vs_peers: Literal["Below", "In-Line", "Above", "Excessive"] = Field(
        description="How does compensation compare to similar-sized peers?"
    )
    pay_for_performance: str = Field(
        description="Assessment of whether pay is tied to actual performance"
    )
    red_flags: List[str] = Field(
        description="Any concerning compensation practices"
    )


class CapitalAllocationRecord(BaseModel):
    """Track record of capital allocation decisions."""
    acquisition_history: str = Field(
        description="Assessment of M&A track record. Were acquisitions value-creating?"
    )
    dividend_policy: str = Field(
        description="Dividend policy and history. Consistent? Growing?"
    )
    buyback_effectiveness: str = Field(
        description="Have buybacks been done at reasonable valuations?"
    )
    capex_discipline: str = Field(
        description="Is capital expenditure generating adequate returns?"
    )
    overall_rating: Literal["Poor", "Mixed", "Good", "Excellent"] = Field(
        description="Overall capital allocation rating"
    )


class ManagementAnalysisResult(BaseModel):
    """Schema for management quality analysis."""

    summary: str = Field(
        description="2-3 sentence summary of management quality"
    )

    leadership_assessment: str = Field(
        description="Assessment of CEO and key executives. "
        "Background, tenure, track record, communication style."
    )

    insider_ownership: str = Field(
        description="Analysis of insider ownership levels and recent transactions. "
        "Are executives aligned with shareholders?"
    )

    compensation: CompensationAnalysis = Field(
        description="Executive compensation analysis"
    )

    capital_allocation: CapitalAllocationRecord = Field(
        description="Track record of capital allocation"
    )

    governance_quality: str = Field(
        description="Board composition, independence, and governance practices"
    )

    shareholder_friendliness: Literal["Hostile", "Neutral", "Friendly", "Very Friendly"] = Field(
        description="How shareholder-friendly is the management?"
    )

    communication_quality: str = Field(
        description="Quality of management communication. "
        "Transparent or evasive? Honest about challenges?"
    )

    succession_planning: str = Field(
        description="Evidence of succession planning and bench strength"
    )

    red_flags: List[str] = Field(
        description="Concerning patterns or behaviors identified"
    )

    green_flags: List[str] = Field(
        description="Positive indicators of management quality"
    )

    management_score: int = Field(
        ge=0, le=100,
        description="Management quality score 0-100: "
        "0-30=Poor, 31-50=Below Average, 51-70=Average, 71-85=Good, 86-100=Excellent"
    )

    would_you_partner: Literal["No", "Hesitant", "Yes", "Enthusiastically"] = Field(
        description="If you had to partner with this management team for 10 years, would you?"
    )


class ManagementAnalyzer(CustomWorkflow):
    """Evaluates management quality and corporate governance."""

    name = "Management Quality Analyzer"
    description = "Evaluate leadership, capital allocation, and governance"
    icon = "👔"
    min_years = 1
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        return """
You are an institutional investor evaluating {ticker} for fiscal year {year}.

Your goal is to assess management quality - because even a great business can be destroyed by poor management.

### ANALYSIS FRAMEWORK

1. **LEADERSHIP QUALITY**
   - CEO background and tenure
   - Executive team depth and experience
   - Board composition and independence
   - Have they managed through difficult periods?

2. **CAPITAL ALLOCATION TRACK RECORD**

   Analyze how management has deployed capital:

   - **M&A**: Were acquisitions sensible? Prices paid? Integration success?
   - **Dividends**: Consistent policy? Sustainable payout?
   - **Buybacks**: Done at attractive valuations or just EPS manipulation?
   - **Capex**: Generating adequate returns on invested capital?
   - **Debt**: Conservative or aggressive leverage?

3. **ALIGNMENT WITH SHAREHOLDERS**
   - Insider ownership levels
   - Recent insider buying/selling
   - Stock-based compensation (creating or destroying value?)
   - Related-party transactions

4. **COMPENSATION ANALYSIS**
   - Total CEO compensation vs. company size
   - Pay tied to actual performance or just tenure?
   - Perquisites and hidden compensation
   - "Golden parachute" provisions

5. **COMMUNICATION QUALITY**
   - Transparency about challenges
   - Consistency of message over time
   - Overpromising and underdelivering?
   - Response to adversity

6. **CORPORATE GOVERNANCE**
   - Board independence
   - Audit committee quality
   - Shareholder rights (dual-class stock? Poison pills?)
   - ESG practices

### RED FLAGS TO WATCH FOR

- Aggressive accounting or frequent restatements
- High executive turnover
- Excessive related-party transactions
- Compensation disconnected from performance
- History of overpaying for acquisitions
- Blaming external factors for poor results
- Opaque financial disclosures

### GREEN FLAGS

- Significant insider ownership
- Management buying stock in open market
- Consistent capital allocation philosophy
- Honest acknowledgment of mistakes
- Long executive tenures with good results
- Conservative accounting practices

### BUFFETT'S TEST

Warren Buffett asks: "Would I want to be in business with these people for 20 years?"

Apply this test to your assessment.
"""

    @property
    def schema(self):
        return ManagementAnalysisResult
