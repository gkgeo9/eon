#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Options Strategy Analyzer Workflow.

Analyzes filings to identify volatility drivers, catalysts, and 
structural setups for options trading strategies (volatility, directional, income).
"""

from typing import List, Literal
from pydantic import BaseModel, Field

# Assuming the base class exists in this location based on your previous files
from custom_workflows.base import CustomWorkflow


class OptionsAnalysisResult(BaseModel):
    """Schema for options strategy and volatility analysis."""

    volatility_regime: str = Field(
        description="Assessment of the expected volatility environment based on "
        "fundamental risks. Is the company entering a period of high stability "
        "(low vol) or high uncertainty (high vol)? Define if the trade should be "
        "Long Vega (buying vol) or Short Vega (selling vol)."
    )

    catalyst_calendar: List[str] = Field(
        description="List of specific upcoming events mentioned in the filing "
        "that could cause price gaps (e.g., FDA rulings, litigation dates, "
        "product launches, debt maturity cliffs). These are 'Binary Events'."
    )

    liquidity_impact: str = Field(
        description="Analysis of share supply/demand dynamics. "
        "Buybacks (floor under price/bullish flow) vs. Dilution/SBC "
        "(ceiling over price/selling pressure). How does this affect "
        "pinning risk or directional bias?"
    )

    bull_case_strategy: str = Field(
        description="The ideal option structure if bullish. "
        "(e.g., 'Long LEAPS calls due to secular growth', 'Bull Put Spread due to high IV'). "
        "Include reasoning based on skew and time horizon."
    )

    bear_case_strategy: str = Field(
        description="The ideal option structure if bearish. "
        "(e.g., 'Long Puts for bankruptcy risk', 'Bear Call Spread for valuation compression'). "
        "Include reasoning."
    )

    neutral_income_strategy: str = Field(
        description="The ideal strategy for sideways movement. "
        "(e.g., 'Iron Condor', 'Covered Calls'). Is the stock suitable for "
        "income generation (stable cash flows)?"
    )

    skew_assessment: Literal["Call Skew", "Put Skew", "Balanced"] = Field(
        description="Based on the 'Risk Factors' section, is the tail risk "
        "weighted to the upside (surprise breakout) or downside (catastrophic failure)?"
    )

    key_levels_support_resistance: str = Field(
        description="Identify fundamental price levels mentioned. "
        "(e.g., 'Cash per share is $10', 'Debt covenants trigger at X ratio'). "
        "These act as fundamental support/resistance for strike selection."
    )

    confidence_score: int = Field(
        ge=0, le=100,
        description="Confidence score (0-100) in the clarity of the directional signal."
    )


class OptionsStrategyAnalyzer(CustomWorkflow):
    """
    Analyzes volatility drivers and catalysts to suggest options structures.
    """

    name = "Options Strategy Analyzer"
    description = "Identify volatility catalysts, skew, and optimal option structures"
    icon = "🎯"
    min_years = 1
    category = "derivatives"

    @property
    def prompt_template(self) -> str:
        return """
You are a Senior Derivatives Strategist at a proprietary trading desk. 
You are analyzing {ticker} for fiscal year {year} to formulate an options trading plan.

Your goal is NOT just to analyze the stock, but to analyze the **Volatility** and **Probability Distribution** of outcomes.

Analyze the filing text focusing on these 4 dimensions:

1. CATALYSTS (Theta/Gamma Events):
   - Scan for specific upcoming dates: Regulatory decisions, patent expirations, debt refinancing deadlines, or major product launches.
   - These are events that cause "Gaps" (jumps in price).

2. VOLATILITY REGIME (Vega):
   - Read the "Risk Factors" and "MD&A". 
   - Is the business stable and predictable (Sell Volatility / Income Strategies)?
   - Or is it binary and uncertain (Buy Volatility / Straddles)?
   - Look for "Material Weakness" in controls or pending litigation.

3. SUPPLY/DEMAND (Flow):
   - Check "Share Repurchases": Aggressive buybacks often create a "soft floor" for stock prices (Support for Short Puts).
   - Check "Stock Based Compensation" and Dilution: Heavy dilution creates a "soft ceiling" (Resistance for Calls).

4. SKEW (Tail Risk):
   - Where is the "Fat Tail"? 
   - Downside Skew: Bankruptcy risk, lawsuit loss, regulatory ban.
   - Upside Skew: FDA approval, buyout rumors, explosive growth.

Based on this, propose specific option structures:
- If Stable: Propose Income trades (Iron Condors, Covered Calls).
- If Volatile: Propose Long Volatility trades (Straddles, debit spreads).
- If Directional: Propose Vertical Spreads or LEAPS.

IMPORTANT:
- Do not provide specific strike prices (as you don't have real-time market data).
- Instead, describe the *type* of structure and the *fundamental logic* behind it.
- Quote specific numbers regarding cash positions, debt walls, or buyback authorizations to support your thesis.
"""

    @property
    def schema(self):
        return OptionsAnalysisResult