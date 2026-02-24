#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Asymmetric Options Analyzer V2.

Deep semantic extraction of tail risks, binary events, and financial fragility 
designed to be cross-referenced with quantitative options data (e.g., FactSet).
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class CatalystAnalysis(BaseModel):
    """Specific event or risk that could drive massive price action."""
    catalyst_type: Literal["Regulatory/FDA", "Legal/Litigation", "Financial/Debt", "M&A/Spin-off", "Operational/Customer", "Other"] = Field(
        description="Categorization of the event."
    )
    event_description: str = Field(description="Specific description (e.g., 'DOJ antitrust probe', 'Phase 3 trial results', '2025 Convertible Note Maturity')")
    timeline: str = Field(description="Expected timeline if explicitly mentioned (e.g., 'Q3 2024', 'Within 12 months')")
    estimated_impact_direction: Literal["Gap Up", "Gap Down", "Bidirectional Gap"] = Field(
        description="The likely direction of the stock price gap if this event triggers."
    )

class AsymmetricOptionsResult(BaseModel):
    """Schema for asymmetric options trade generation."""

    # --- CATEGORICAL CLASSIFICATION ---
    directional_bias: Literal["Call Bias (Upside Tail)", "Put Bias (Downside Tail)", "Straddle Bias (Binary)", "No Edge (Skip)"] = Field(
        description="Primary direction of the mispriced volatility based on filing evidence."
    )

    # --- STRICT BOUNDED SCORING (0-100) ---
    binary_event_score: int = Field(
        ge=0, le=100,
        description="Score 0-100 for a single-day gap event. 0-20: Business as usual. 40-60: Standard earnings risk. 80-100: 'Bet the company' FDA, lawsuit, or M&A event."
    )
    
    financial_distress_score: int = Field(
        ge=0, le=100,
        description="Score 0-100 for liquidity/debt risks. 0-20: Cash rich. 40-60: Standard leverage. 80-100: Imminent debt walls, going concern warnings, or covenant breaches."
    )

    opacity_score: int = Field(
        ge=0, le=100,
        description="Score 0-100 for disclosure complexity. 0-20: Simple, clear business model. 80-100: Highly convoluted off-balance sheet entities, complex derivatives, or evasive language."
    )

    operational_fragility_score: int = Field(
        ge=0, le=100,
        description="Score 0-100 for concentration risk. 0-20: Highly diversified. 80-100: Extreme reliance on 1-2 customers, a single supplier, or a single patent."
    )

    composite_asymmetry_score: int = Field(
        ge=0, le=100,
        description="Overall score. ONLY score > 80 if there is a severe mismatch between the company's stable facade and actual underlying tail risks."
    )

    # --- QUANTITATIVE EXTRACTIONS ---
    max_customer_concentration_pct: Optional[float] = Field(
        ge=0.0, le=100.0,
        default=None,
        description="Highest percentage of revenue from a single customer, if stated. Format as 0.0 to 100.0. Return null if not explicitly stated."
    )

    imminent_debt_wall_year: Optional[int] = Field(
        ge=2024, le=2050,
        default=None,
        description="The specific year of the most dangerously large impending debt maturity, if mentioned. Return null if debt is easily manageable."
    )

    # --- QUALITATIVE CONTEXT ---
    catalysts: List[CatalystAnalysis] = Field(
        description="Top 1-3 specific binary events, risks, or catalysts found in the filing."
    )

    hidden_risks_extracted: List[str] = Field(
        description="Bullet points of specific, non-boilerplate risks discovered deep in the filing (e.g., obscure footnotes, changing accounting standards, specific lost contracts)."
    )

    thesis_summary: str = Field(
        description="A 2-3 sentence summary of why an asymmetric options opportunity exists here."
    )


class AsymmetricOptionsAnalyzer(CustomWorkflow):
    """Hunts for mispriced volatility and asymmetric options setups."""

    name = "Asymmetric Options Deep Scanner"
    description = "Scans for binary events, debt walls, and fragility with strict 0-100 scoring for quantitative screening."
    icon = "⚖️"
    min_years = 1 
    category = "derivatives"

    @property
    def prompt_template(self) -> str:
        return """
You are an elite quantitative derivatives trader and forensic accountant analyzing {ticker} for fiscal year {year}.

Your objective is to extract highly specific tail-risk data from this SEC filing. This output will be fed into a quantitative screening model alongside Implied Volatility (IV) data to identify mathematically mispriced options.

We are hunting for ASYMMETRY: situations where the filing reveals explosive potential energy (upside or downside) that the broader market may be ignoring.

### SCORING RUBRICS (STRICT ADHERENCE REQUIRED)

You must score four dimensions from 0 to 100. Do NOT cluster your scores around 70. Use the full spectrum based on these strict guidelines:

1. **BINARY EVENT SCORE (Gap Risk)**
   - 0-20: Utility-like stability. No major catalysts.
   - 40-60: Standard product launches, routine litigation.
   - 80-100: "Bet the company" events. Imminent FDA PDUFA dates, existential antitrust rulings, hostile takeovers, or massive binary legal settlements.

2. **FINANCIAL DISTRESS SCORE (Credit/Liquidity Risk)**
   - 0-20: Net cash position, generates massive free cash flow.
   - 40-60: Standard corporate leverage, staggered maturities.
   - 80-100: "Going concern" warnings, severe covenant threshold breaches, massive debt coming due within 12-24 months in a high-interest rate environment, bleeding cash.

3. **OPACITY SCORE (Information Asymmetry)**
   - 0-20: Transparent, simple reporting (e.g., simple retail).
   - 80-100: Enron-level complexity. Massive off-balance sheet arrangements, opaque VIEs (Variable Interest Entities), complex Level 3 asset valuations, unexplained changes in auditors, or highly evasive MD&A language.

4. **OPERATIONAL FRAGILITY SCORE (Single Point of Failure)**
   - 0-20: Millions of customers, diversified supply chain.
   - 80-100: 40%+ of revenue from one customer (e.g., Apple dependency), single-source supplier for critical components, or a single patent expiration destroying the moat.

### INSTRUCTIONS FOR EXTRACTION

- **Ignore Boilerplate:** Do NOT extract generic risks like "COVID-19 impacts," "general economic downturns," or "currency fluctuations." We only want IDIOSYNCRATIC, company-specific risks.
- **Extract Hard Numbers:** If they mention a customer makes up 43% of revenue, put `43.0` in `max_customer_concentration_pct`. If they have a massive convertible note due in 2026, put `2026` in `imminent_debt_wall_year`.
- **Be Ruthless:** If the company is a boring, stable mega-cap, score them LOW on all volatility metrics and set directional bias to "No Edge (Skip)". Do not manufacture a trade where one does not exist.

Analyze {ticker} now and format your response exactly to the schema.
"""

    @property
    def schema(self):
        return AsymmetricOptionsResult