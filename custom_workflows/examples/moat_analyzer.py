#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Competitive Moat Analyzer Workflow.

Identifies and rates durable competitive advantages using
Warren Buffett's moat framework.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class MoatSource(BaseModel):
    """A single source of competitive advantage."""
    type: Literal[
        "Network Effects", "Switching Costs", "Cost Advantages",
        "Intangible Assets", "Efficient Scale", "None Identified"
    ] = Field(description="Type of competitive advantage")
    strength: Literal["None", "Weak", "Moderate", "Strong", "Very Strong"] = Field(
        description="How strong is this moat source?"
    )
    evidence: str = Field(
        description="Specific evidence from the filing supporting this assessment"
    )
    durability: str = Field(
        description="How long is this advantage likely to persist? What could erode it?"
    )


class MoatAnalysisResult(BaseModel):
    """Schema for competitive moat analysis."""

    summary: str = Field(
        description="2-3 sentence summary of the company's competitive position"
    )

    moat_sources: List[MoatSource] = Field(
        description="Analysis of each potential moat source"
    )

    primary_moat: Optional[str] = Field(
        description="The single strongest competitive advantage, or None if no moat"
    )

    moat_width: Literal["None", "Narrow", "Wide"] = Field(
        description="Overall moat width: None (no advantage), Narrow (some advantages), Wide (durable advantages)"
    )

    moat_trend: Literal["Eroding", "Stable", "Strengthening"] = Field(
        description="Is the moat getting stronger or weaker over time?"
    )

    financial_evidence: str = Field(
        description="Financial metrics that support the moat assessment: "
        "ROIC, margins, market share, pricing power evidence"
    )

    threats_to_moat: List[str] = Field(
        description="Top 3-5 factors that could erode the competitive advantage"
    )

    management_investment: str = Field(
        description="Is management investing to maintain/extend the moat? "
        "R&D, brand building, capacity expansion, etc."
    )

    moat_score: int = Field(
        ge=0, le=100,
        description="Moat strength score 0-100: "
        "0-20=No moat, 21-40=Weak, 41-60=Narrow, 61-80=Solid, 81-100=Wide moat"
    )

    investment_implications: str = Field(
        description="What does this moat analysis mean for investment decisions?"
    )


class MoatAnalyzer(CustomWorkflow):
    """Identifies and rates competitive moats using Buffett's framework."""

    name = "Competitive Moat Analyzer"
    description = "Identify durable competitive advantages using Warren Buffett's moat framework"
    icon = "🏰"
    min_years = 1
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        return """
You are a value investing analyst in the style of Warren Buffett and Charlie Munger analyzing {ticker} for fiscal year {year}.

Your goal is to identify whether this company has durable competitive advantages ("economic moats").

### MOAT FRAMEWORK

Analyze each of the five moat sources:

1. **NETWORK EFFECTS**
   - Does the product/service become more valuable with more users?
   - Examples: Marketplaces, social networks, payment networks
   - Look for: User counts, engagement metrics, marketplace liquidity

2. **SWITCHING COSTS**
   - How difficult/costly is it for customers to switch to competitors?
   - Examples: Enterprise software, banking relationships, embedded systems
   - Look for: Customer retention rates, contract lengths, integration depth

3. **COST ADVANTAGES**
   - Does the company have structural cost benefits competitors can't match?
   - Examples: Scale economies, process advantages, unique assets
   - Look for: Gross margins vs. peers, cost per unit trends, capacity utilization

4. **INTANGIBLE ASSETS**
   - Patents, brands, licenses, regulatory approvals
   - Examples: Pharma patents, consumer brands, spectrum licenses
   - Look for: R&D spending, brand value references, regulatory barriers

5. **EFFICIENT SCALE**
   - Is the market too small for multiple profitable competitors?
   - Examples: Utilities, regional monopolies, niche markets
   - Look for: Market size, competitor count, entry barriers

### FINANCIAL EVIDENCE

The following metrics indicate moat presence:
- **ROIC > 15%** sustained over 5+ years = strong moat indicator
- **Gross margin > industry average** = pricing power
- **Stable or growing market share** = competitive strength
- **Pricing ahead of inflation** = customer captivity

### MOAT THREATS

Consider what could erode the moat:
- Technology disruption
- Regulatory changes
- New entrants with different business models
- Customer behavior shifts
- Management complacency

### OUTPUT REQUIREMENTS

- Be SPECIFIC: Quote financial metrics and specific examples
- Be HONEST: Most companies don't have wide moats - it's okay to say so
- Be FORWARD-LOOKING: Consider how the moat might evolve
- Avoid false moats: Brand awareness alone is not a moat without pricing power
"""

    @property
    def schema(self):
        return MoatAnalysisResult
