#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Options Strategy Analyzer Workflow.

Analyzes filings to identify volatility drivers, catalysts, and 
structural setups for options trading strategies.

UPDATES:
- Split Bull/Bear strategies into 'Tactical' (Gamma/Event) and 'Structural' (Delta/LEAPS).
- Enhanced Prompt to focus on fundamental support for long-duration trades.
"""

from typing import List, Literal
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class OptionsAnalysisResult(BaseModel):
    """
    Schema for options strategy and volatility analysis.
    Captures the volatility regime, binary events, and structural trade setups.
    """

    volatility_regime: str = Field(
        description="Detailed assessment of the volatility environment. "
        "Is the company in a high-uncertainty (Long Vega) or stable (Short Vega) regime? "
        "Cite specific risks (litigation, competitive erosion, pipeline binary events) "
        "or stability factors (cash cow business, low competition)."
    )

    catalyst_calendar: List[str] = Field(
        description="A list of specific binary events with dates extracted from the filing. "
        "Include PDUFA dates, court hearings, debt maturities, product launches, "
        "or regulatory decision deadlines. Format: 'Date: Event description'."
    )

    liquidity_impact: str = Field(
        description="Analysis of the supply/demand dynamics for the stock. "
        "Evaluate Share Repurchases (support/floor), Stock-Based Compensation (dilution/ceiling), "
        "and Insider buying/selling. Mention specific dollar amounts authorized vs utilized."
    )

    bull_case_tactical: str = Field(
        description="Short-term (0-90 days) bullish strategy focused on specific upcoming binary events (Gamma/Event Vol). "
        "Example: 'Long Call Spread expiring immediately after the PDUFA date'. "
        "If no immediate events exist, state 'No near-term tactical setup'."
    )

    bull_case_structural: str = Field(
        description="Long-term (>1 year) bullish strategy focused on fundamental business inflection (Delta/Secular Growth). "
        "Example: 'Long LEAPS Calls (Jan 2027) to capture the commercial ramp of new products'. "
        "Explain WHY the balance sheet (Cash/Runway) supports holding this duration."
    )

    bear_case_tactical: str = Field(
        description="Short-term (0-90 days) bearish strategy focused on negative binary events or shocks. "
        "Example: 'Long Put Spread targeting the patent court ruling'. "
        "Focus on 'Gamma' events that could cause a sharp drop."
    )

    bear_case_structural: str = Field(
        description="Long-term (>1 year) bearish strategy focused on secular decline or erosion. "
        "Example: 'Long LEAPS Puts to profit from slow revenue bleed due to patent cliffs'. "
        "Focus on 'Delta' moves driven by fundamental decay."
    )

    neutral_income_strategy: str = Field(
        description="The optimal strategy for sideways/range-bound movement. "
        "Example: 'Iron Condor' or 'Covered Calls'. "
        "If the stock is too volatile for income, explicitly state that."
    )

    skew_assessment: Literal["Call Skew", "Put Skew", "Balanced"] = Field(
        description="Assessment of the tail risk distribution. "
        "'Put Skew' if downside risks (bankruptcy, litigation) outweigh upside. "
        "'Call Skew' if potential for explosive growth/buyout exists."
    )

    key_levels_support_resistance: str = Field(
        description="Fundamental price levels derived from the balance sheet. "
        "Mention Cash per share, Debt walls, or Buyback support levels. "
        "Do NOT use technical analysis (chart patterns)."
    )

    confidence_score: int = Field(
        ge=0, le=100,
        description="Confidence score (0-100) in the clarity of the trade setup based on the filing data."
    )


class OptionsStrategyAnalyzer(CustomWorkflow):
    """
    Analyzes volatility drivers, binary catalysts, and flow dynamics 
    to suggest professional options trading structures.
    """

    name = "Options Strategy Analyzer"
    description = "Identify volatility catalysts, skew, and optimal option structures"
    # FIX 1: Changed text to an actual emoji
    icon = "⚡" 
    min_years = 1
    category = "derivatives"

    @property
    def prompt_template(self) -> str:
        # FIX 2: Doubled the curly braces {{ }} around the JSON example 
        # so Python treats them as text, not variables.
        return """
You are a Senior Derivatives Strategist at a top-tier proprietary trading desk. 
You are analyzing {ticker} for fiscal year {year} to formulate an options trading plan.

Your goal is to analyze the **Volatility Surface** and **Probability Distribution** of outcomes based on fundamental data.

### ANALYSIS FRAMEWORK

1. **VOLATILITY REGIME (Vega)**:
   - *High Vol/Long Vega*: Biotech binaries, distressed debt, litigation outcomes.
   - *Low Vol/Short Vega*: Utilities, mature staples, consistent compounders.
   - *Action*: Determine if we should be Buying Volatility (Straddles/Spreads) or Selling It (Income).

2. **CATALYSTS (Gamma/Event Risk)**:
   - Scrape the filing for **Specific Dates**: PDUFA dates, Trial outcomes, Debt maturities, Spin-offs.
   - These are "Hard Catalysts" that cause gaps.

3. **FLOW & LIQUIDITY (Pinning)**:
   - **Buybacks**: Act as a "Put Wall" (Support). Are they active? (Check Cash Flow statement).
   - **Dilution/SBC**: Acts as a "Call Wall" (Resistance). Heavy issuance caps upside.

4. **STRATEGY SELECTION (Tactical vs. Structural)**:
   - **Tactical (Gamma)**: Trades lasting <90 days. Focus on *Events*. (e.g., "Buy Calls before the FDA ruling").
   - **Structural (Delta)**: Trades lasting >1 year (LEAPS). Focus on *Trends*. (e.g., "Buy LEAPS because Cash > Debt and the new product is launching").

5. **SKEW (Tail Risk)**:
   - **Put Skew**: Fear of ruin (Bankruptcy, Patent Loss).
   - **Call Skew**: FOMO / Lottery Ticket (Buyout, Blockbuster drug).

### EXAMPLE OUTPUT FORMAT
(Use this level of detail and tone)

{{
  "volatility_regime": "High volatility regime. The company faces binary outcomes from the Phase 3 data readout expected in Q3 2025. Revenue is eroding (-15% YoY), increasing the desperation for pipeline success.",
  "catalyst_calendar": [
    "August 30, 2025: FDA PDUFA date for Lead Asset X.",
    "November 15, 2025: District Court Patent Ruling."
  ],
  "bull_case_tactical": "Long Call Spread expiring Oct 2025. Targets the FDA approval event. Limits Vega risk if IV crushes post-event.",
  "bull_case_structural": "Long Jan 2027 LEAPS Calls. The company has $2B in cash (3 years of runway), providing a floor while the new commercial launch ramps up over the next 18 months.",
  "skew_assessment": "Put Skew"
}}

### INSTRUCTIONS

- Be **Quantitative**: Quote cash balances, burn rates, and debt amounts.
- Be **Specific**: Do not say "regulatory approval"; say "PDUFA date in August".
- **No Technical Analysis**: Do not mention moving averages or RSI. Use *Fundamental* Support/Resistance (e.g., Net Cash per share).
- **Tactical vs Structural**: Clearly distinguish between short-term event bets and long-term investment theses.

Analyze {ticker} now.
"""

    @property
    def schema(self):
        return OptionsAnalysisResult