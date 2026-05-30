#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contrarian Hunter - Hidden Gem Investment Scanner.

Port of the standalone ``contrarian_hunter`` script to an EON custom workflow.

Instead of using the 10-K filing text that EON normally feeds the prompt with,
this workflow reads a pre-computed "success factors" JSON file for the ticker
from a hardcoded folder (``FACTORS_DIR`` below) and sends that JSON to Gemini.

Place per-ticker factor files at:
    <FACTORS_DIR>/<TICKER>_success_factors.json

The output schema mirrors the original 6-category alpha scoring used by the
standalone script so the rankings compiler / CSV exporter remains compatible.
"""

import json
from pathlib import Path
from typing import List, Literal, Type

from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow


# --------------------------------------------------------------------------- #
# Hardcoded input path (edit this to wherever you import the factor JSONs to)
# --------------------------------------------------------------------------- #
FACTORS_DIR = Path("/home/user/eon/data/random_company_factors")


# --------------------------------------------------------------------------- #
# Output schema - matches the JSON shape produced by the original script
# --------------------------------------------------------------------------- #
class ContrarianScores(BaseModel):
    """Six-category alpha scoring (0-100 each)."""

    strategic_anomaly: int = Field(
        ge=0, le=100,
        description=(
            "How unconventional is the company's strategy vs. industry playbook? "
            "0-20 standard, 21-40 minor deviations, 41-60 unconventional w/ unclear rationale, "
            "61-80 clear contrarian strategy with logic, 81-100 bold counterintuitive moves."
        ),
    )
    asymmetric_resources: int = Field(
        ge=0, le=100,
        description=(
            "Concentration of resources on a single bet. "
            "0-20 evenly spread, 41-60 moderate (10-25%), 61-80 major (25-50%), "
            "81-100 all-in bet on transformative opportunity."
        ),
    )
    contrarian_positioning: int = Field(
        ge=0, le=100,
        description=(
            "How opposite is positioning vs. industry consensus? "
            "0-20 following trends, 61-80 clear opposite positioning on key assumptions, "
            "81-100 entire model contradicts core industry beliefs."
        ),
    )
    cross_industry_dna: int = Field(
        ge=0, le=100,
        description=(
            "Importing playbooks/leadership from other industries. "
            "0-20 only same-industry experience, 61-80 actively importing foreign practices, "
            "81-100 fundamentally operating like a different industry."
        ),
    )
    early_infrastructure: int = Field(
        ge=0, le=100,
        description=(
            "Building capabilities for markets that don't yet exist. "
            "0-20 current market only, 61-80 building for 3-5 years out, "
            "81-100 infrastructure for markets that don't exist yet."
        ),
    )
    intellectual_capital: int = Field(
        ge=0, le=100,
        description=(
            "Hidden/undervalued IP and technical moats. "
            "0-20 standard well-recognized IP, 61-80 significant hidden technical moats, "
            "81-100 game-changing IP completely unrecognized by market."
        ),
    )


class ContrarianHunterResult(BaseModel):
    """Output schema for the contrarian hunter analysis."""

    ticker: str = Field(description="Company ticker symbol.")
    company_name: str = Field(description="Company name.")
    overall_alpha_score: int = Field(
        ge=0, le=100,
        description=(
            "Overall hidden-gem alpha score. Most companies 20-50, good 51-70, "
            "exceptional 71-85, truly revolutionary 86-100."
        ),
    )
    scores: ContrarianScores = Field(
        description="Per-category 0-100 scores; see ContrarianScores."
    )
    key_insights: List[str] = Field(
        description=(
            "2-5 specific factual observations citing data points. "
            "Concrete evidence of differentiation or lack thereof."
        ),
    )
    investment_thesis: str = Field(
        description=(
            "Objective 2-3 sentence assessment of the opportunity based on evidence."
        ),
    )
    risk_factors: List[str] = Field(
        description=(
            "Top execution / market risks with probability assessment. "
            "Be honest about what could invalidate the thesis."
        ),
    )
    catalyst_timeline: str = Field(
        description="Realistic timeframe for thesis validation or invalidation."
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence rating based on data quality and evidence strength."
    )


# --------------------------------------------------------------------------- #
# Workflow definition
# --------------------------------------------------------------------------- #
class ContrarianHunter(CustomWorkflow):
    """
    Score companies against six alpha factors using pre-computed
    'success factor' JSON files instead of the raw 10-K text.
    """

    name = "Contrarian Hunter (Hidden Gems)"
    description = (
        "Six-factor alpha scoring (strategic anomaly, asymmetric resources, "
        "contrarian positioning, cross-industry DNA, early infrastructure, "
        "intellectual capital). Reads pre-computed success-factor JSONs from a "
        "hardcoded folder instead of using the 10-K text."
    )
    icon = "🕵️"
    min_years = 1
    category = "asymmetric"

    @property
    def prompt_template(self) -> str:
        return """
You are an objective investment analyst. Analyze this company's data without bias toward company size, market cap, or industry popularity. Be brutally honest - most companies will score poorly on these metrics, and that's expected.

You are analyzing {ticker} for fiscal year {year}. The data block below is a pre-computed "success factors" JSON for this company (not the raw 10-K). Score based on what's in it.

**SCORING FRAMEWORK (0-100 scale):**

1. **STRATEGIC ANOMALY SCORE (0-100)**
   - 0-20: Standard industry playbook, no unusual decisions
   - 21-40: Minor deviations from industry norm, low-risk moves
   - 41-60: Some unconventional decisions with unclear rationale
   - 61-80: Clear contrarian strategy with logical reasoning
   - 81-100: Bold, counterintuitive moves that could redefine their space

2. **ASYMMETRIC RESOURCE ALLOCATION (0-100)**
   - 0-20: Resources spread evenly across standard business areas
   - 21-40: Slight concentration in 1-2 areas, typical allocation
   - 41-60: Moderate bet on specific initiative (10-25% of resources)
   - 61-80: Major bet on single opportunity (25-50% of resources)
   - 81-100: All-in bet risking company on transformative opportunity

3. **CONTRARIAN POSITIONING (0-100)**
   - 0-20: Following exact industry trends and consensus
   - 21-40: Minor differentiation, mostly following pack
   - 41-60: Some opposite moves but hedging bets
   - 61-80: Clear opposite positioning on key industry assumptions
   - 81-100: Completely inverse strategy to industry orthodoxy

4. **CROSS-INDUSTRY DNA (0-100)**
   - 0-20: Management with only same-industry experience
   - 21-40: Some outside hires but maintaining industry norms
   - 41-60: Applying select concepts from other industries
   - 61-80: Leadership actively importing foreign industry practices
   - 81-100: Fundamentally operating like a different industry

5. **EARLY INFRASTRUCTURE BUILDER (0-100)**
   - 0-20: Building for current market needs only
   - 21-40: Minor investments in next-generation capabilities
   - 41-60: Significant R&D for 2-3 year market evolution
   - 61-80: Building for markets 3-5 years out
   - 81-100: Creating infrastructure for markets that don't exist yet

6. **UNDERVALUED INTELLECTUAL CAPITAL (0-100)**
   - 0-20: Standard IP portfolio, no hidden technical advantages
   - 21-40: Decent IP but well-recognized by market
   - 41-60: Some overlooked technical capabilities or patents
   - 61-80: Significant hidden technical moats or IP value
   - 81-100: Game-changing IP/capabilities completely unrecognized

**CRITICAL INSTRUCTIONS:**
- Primary focus: Score based on EVIDENCE from the JSON data, management actions, and concrete business decisions.
- Secondary consideration: Include forward-looking execution capability only when supported by track record.
- Only award high scores (60+) with specific justification citing data points.
- Company size, age, market cap, or industry power is irrelevant - judge actions relative to their available resources.
- Score distribution expectation: Most companies 20-50, good companies 51-70, exceptional companies 71-85, truly revolutionary companies 86-100.
- Be objective: don't inflate scores for potential alone, but don't ignore demonstrated execution ability.
- Use the `ticker` field value "{ticker}" in your output.
"""

    @property
    def schema(self) -> Type[BaseModel]:
        return ContrarianHunterResult

    # ----------------------------------------------------------------- #
    # Override the default `analyze` so we ignore the 10-K text and feed
    # the pre-computed success-factors JSON to Gemini instead.
    # ----------------------------------------------------------------- #
    def analyze(self, ticker: str, year: int, text: str, provider) -> BaseModel:
        factors_path = FACTORS_DIR / f"{ticker}_success_factors.json"

        if not factors_path.exists():
            raise FileNotFoundError(
                f"Contrarian Hunter requires pre-computed success factors at "
                f"{factors_path}. Import the JSON file for {ticker} and retry."
            )

        with factors_path.open("r") as f:
            company_data = json.load(f)

        prompt = self.format_prompt(ticker, year)
        full_prompt = (
            f"{prompt}\n\n**COMPANY DATA (success factors JSON):**\n"
            f"{json.dumps(company_data, indent=2)}"
        )

        return provider.generate_with_retry(
            prompt=full_prompt,
            schema=self.schema,
            max_retries=3,
            retry_delay=10,
        )
