#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Warren Buffett's value investing lens - Pydantic models.

EXACT Field descriptions from standardized_sec_ai/ppee.py
Following the pattern: Field descriptions ARE the prompt guidance.
"""

from typing import List
from pydantic import BaseModel, Field


class BuffettAnalysis(BaseModel):
    """
    Warren Buffett's Investment Philosophy.

    Focus on: Quality businesses, economic moats, great management,
    and buying at a margin of safety.
    """
    business_understanding: str = Field(
        description="Explain this business in one simple paragraph. What do they actually sell? How do they make money? If you can't explain it simply, that's a red flag."
    )
    economic_moat: str = Field(
        description="What is their SPECIFIC competitive advantage? Choose from: Brand Power (pricing premium), Network Effects (more users = more value), Switching Costs (expensive to leave), Cost Advantage (structural), Regulatory Moat (licenses/barriers). PROVE it with numbers: margins vs competitors, market share trends, customer retention rates. Don't be vague."
    )
    moat_rating: str = Field(
        description="Wide (10+ years sustainable) / Narrow (3-5 years) / None (commodity). Be honest about durability."
    )
    management_quality: str = Field(
        description="Capital allocation track record over 3-5 years: What did they do with excess cash (buybacks, M&A, dividends)? Did those decisions create value? Insider ownership: Do executives have meaningful stock ownership (not just options)? Give dollar amounts and percentages. Grade them A-F."
    )
    pricing_power: str = Field(
        description="The ultimate test: Can they raise prices 10% without losing 10% of customers? Show evidence from the filing - have they raised prices? What happened to volume? Look for pricing strategy mentions, competitive dynamics, margin trends."
    )
    return_on_invested_capital: str = Field(
        description="Calculate ROIC = NOPAT / (Debt + Equity - Cash) for last 5 years if possible. Compare to 10% benchmark. Is it improving (compounding machine) or declining (value destruction)? Show the trend with numbers."
    )
    free_cash_flow_quality: str = Field(
        description="FCF = Operating Cash Flow - Capex. Show 5-year growth rate. Calculate FCF conversion ratio (FCF/Net Income - should be >80%). Is FCF growing faster than revenue? That's operating leverage. Be specific with dollars."
    )
    business_tailwinds: List[str] = Field(
        description="3-5 secular trends (10+ year duration) that benefit this business. Be specific - not 'digitalization' but 'enterprise cloud migration driving 20%+ annual SaaS spending growth'. Show how THIS company benefits."
    )
    intrinsic_value_estimate: str = Field(
        description="Estimate normalized owner earnings (Net Income + D&A - Maintenance Capex). Apply 8-12x multiple. Compare to current market cap. Calculate margin of safety: (Intrinsic Value - Market Cap) / Market Cap. Buffett wants 30%+ upside."
    )
    buffett_verdict: str = Field(
        description="BUY (wide moat + great management + 30% margin of safety) / HOLD (good business, fair price) / PASS (no moat, bad management, or overvalued). Explain in 2-3 sentences with clear logic."
    )


__all__ = ['BuffettAnalysis']
