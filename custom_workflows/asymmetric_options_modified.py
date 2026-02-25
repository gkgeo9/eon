#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Asymmetric Options Analyzer V4.

Evidence-gated, temporally isolated, prestige-blind screener for identifying
mispriced volatility candidates in the 1-24 month LEAPS horizon.

Schema design principles (Gemini structured output compatibility):
    - Flat structure where possible: no deeply nested wrapper objects.
    - Scored dimensions use parallel flat fields (score + evidence) to avoid
      nesting ScoredDimension objects inside the root model.
    - Optional/nullable fields are minimized; sentinel values used instead
      (e.g., -1.0) to avoid anyOf null patterns unsupported by Gemini.
    - Catalyst sub-objects are one level deep only.
    - Total nesting depth: root -> CatalystV4 (2 levels). Safe.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from custom_workflows.base import CustomWorkflow


class CatalystV4(BaseModel):
    """
    A specific, near-term catalyst with an explicit filing-stated timeline.
    Only include catalysts where the filing states a timeline within 24 months.
    """
    catalyst_type: Literal[
        "Regulatory/FDA",
        "Legal/Litigation",
        "Financial/Debt Maturity",
        "M&A/Spin-off",
        "Operational/Customer Loss",
        "Technology/Product Launch",
        "Other"
    ] = Field(description="Category of catalyst.")

    event_description: str = Field(
        description=(
            "Specific description referencing a named entity, dollar amount, "
            "date, or regulatory body. Example: 'Phase 3 PDUFA date for Drug X "
            "expected Q2 2025.' NOT: 'May face regulatory risk.'"
        )
    )

    filing_evidence: str = Field(
        description=(
            "Direct quote or close paraphrase from the filing that confirms "
            "the catalyst AND its timeline. If no explicit timeline exists in "
            "the filing, do not include this catalyst."
        )
    )

    months_to_event: int = Field(
        ge=1, le=24,
        description=(
            "Months from filing date to this event, based only on information "
            "in the filing. Do NOT estimate if the filing does not state a "
            "timeline. Exclude this catalyst instead."
        )
    )

    direction: Literal["Gap Up", "Gap Down", "Bidirectional Gap"] = Field(
        description="Likely price movement direction if this catalyst triggers."
    )


class AsymmetricOptionsV4(BaseModel):
    """
    Evidence-gated asymmetric options screening result.

    Flat structure for Gemini structured output compatibility.
    All scores above 50 must have a corresponding evidence field citing
    specific filing text. Designed for cross-referencing with IV rank
    and short interest data.
    """

    # --- Primary classification ---
    directional_bias: Literal[
        "Call Bias (Upside Tail)",
        "Put Bias (Downside Tail)",
        "Straddle Bias (Binary)",
        "No Edge (Skip)"
    ] = Field(
        description=(
            "Default is 'No Edge (Skip)'. Override only if the filing contains "
            "explicit, specific evidence of near-term asymmetric risk or upside. "
            "'Interesting industry' or 'growth potential' do not qualify."
        )
    )

    # --- Binary event dimension ---
    binary_event_score: int = Field(
        ge=0, le=100,
        description=(
            "Gap risk from a named, near-term event. "
            "0-20: No named catalysts, utility-like stability. "
            "21-40: Standard product cycles, routine earnings risk. "
            "41-60: Named litigation or regulatory process, no clear timeline. "
            "61-80: Named event with filing-stated timeline within 24 months. "
            "81-100: 'Bet the company' event with explicit near-term timeline "
            "(FDA PDUFA date, existential antitrust ruling, binary settlement)."
        )
    )
    binary_event_evidence: str = Field(
        description=(
            "If score > 50: exact quote or close paraphrase from the filing "
            "with section context. "
            "If score <= 50: write 'Below threshold: [brief reason]'."
        )
    )

    # --- Financial distress dimension ---
    financial_distress_score: int = Field(
        ge=0, le=100,
        description=(
            "Liquidity, solvency, and debt risk. "
            "0-20: Net cash, strong FCF, no material debt. "
            "21-40: Standard investment-grade leverage, staggered maturities. "
            "41-60: Elevated leverage, some refinancing risk noted. "
            "61-80: Filing explicitly mentions refinancing risk, covenant "
            "thresholds, or a debt wall within 36 months. "
            "81-100: Going concern language, covenant breach, imminent "
            "maturity the company cannot service, or auditor doubt. "
            "Must quote the filing."
        )
    )
    financial_distress_evidence: str = Field(
        description=(
            "If score > 50: exact quote or close paraphrase from the filing "
            "with section context. "
            "If score <= 50: write 'Below threshold: [brief reason]'."
        )
    )

    # --- Opacity dimension ---
    opacity_score: int = Field(
        ge=0, le=100,
        description=(
            "Disclosure complexity and information asymmetry. "
            "0-20: Simple, transparent business and financials. "
            "21-40: Standard corporate complexity. "
            "41-60: Notable related-party transactions or off-balance sheet items. "
            "61-80: Multiple VIEs, complex derivatives, or unexplained auditor change. "
            "81-100: Massive unexplained off-balance sheet entities, Level 3 "
            "revaluations, evasive MD&A, or auditor resignation with concerns."
        )
    )
    opacity_evidence: str = Field(
        description=(
            "If score > 50: exact quote or close paraphrase from the filing "
            "with section context. "
            "If score <= 50: write 'Below threshold: [brief reason]'."
        )
    )

    # --- Operational fragility dimension ---
    operational_fragility_score: int = Field(
        ge=0, le=100,
        description=(
            "Single-point-of-failure concentration risk. "
            "0-20: Highly diversified customers, suppliers, geographies. "
            "21-40: Moderate concentration, no dominant single dependency. "
            "41-60: One customer or supplier at 20-35% of revenue or supply. "
            "61-80: One customer or supplier at 35-50%, or a single patent "
            "is the primary revenue driver. "
            "81-100: 50%+ revenue from one customer, single-source critical "
            "supplier with no alternative, or single patent whose expiry is "
            "the company's primary existential risk. Must quote the filing."
        )
    )
    operational_fragility_evidence: str = Field(
        description=(
            "If score > 50: exact quote or close paraphrase from the filing "
            "with section context. "
            "If score <= 50: write 'Below threshold: [brief reason]'."
        )
    )

    # --- Composite score ---
    composite_asymmetry_score: int = Field(
        ge=0, le=100,
        description=(
            "Weighted composite: (binary_event * 0.35) + "
            "(financial_distress * 0.30) + (operational_fragility * 0.20) + "
            "(opacity * 0.15). Round to nearest integer. "
            "Only exceed 80 if multiple dimensions independently score above "
            "70 with strong filing evidence. A single high dimension should "
            "not push the composite above 70."
        )
    )

    # --- Hard quantitative extractions ---
    imminent_debt_wall_year: int = Field(
        ge=0,
        description=(
            "The specific year of the largest near-term debt maturity that "
            "the filing explicitly flags as a refinancing concern. "
            "Use 0 if debt is manageable or no specific concern is cited."
        )
    )

    cash_runway_months: int = Field(
        ge=0,
        description=(
            "If the filing states or implies a cash runway "
            "(e.g., 'sufficient to fund operations for 18 months'), "
            "state the number of months. Use 0 if not stated."
        )
    )

    # --- Catalysts (near-term, explicit timeline only) ---
    catalysts: List[CatalystV4] = Field(
        description=(
            "1-3 catalysts with EXPLICIT timelines in the filing within "
            "24 months of the filing date. Return empty list if none qualify. "
            "Do NOT infer timelines not stated in the filing. "
            "A catalyst must plausibly cause a single-day gap of 5%+ if it "
            "triggers. Routine operational milestones, lease commencements, "
            "and standard product launches do not qualify unless the filing "
            "explicitly ties them to existential or outsized financial risk."
        )
    )

    # --- Hidden risks ---
    hidden_risks: List[str] = Field(
        description=(
            "2-5 specific, non-boilerplate risks from footnotes, MD&A, or "
            "legal proceedings. Each must name a specific entity, dollar "
            "amount, date, or contract. "
            "EXCLUDE generic risks present in most 10-Ks: general economic "
            "downturn, interest rate risk, FX risk, vague cybersecurity, "
            "climate change, pandemic. If none exist, return empty list."
        )
    )

    # --- Summary ---
    thesis_summary: str = Field(
        description=(
            "2-3 sentences citing specific filing evidence for the bias and "
            "score. If 'No Edge (Skip)', explain why the filing does not "
            "support asymmetry. No stock history, analyst ratings, or "
            "information from outside the filing."
        )
    )

    leaps_horizon_fit: Literal[
        "Strong (multiple explicit near-term catalysts)",
        "Moderate (one explicit catalyst or strong distress signal)",
        "Weak (implied risk only, no explicit timeline)",
        "None (no actionable asymmetry found)"
    ] = Field(
        description=(
            "Fit for a 1-24 month LEAPS strategy based on evidence quality "
            "and catalyst timeline specificity in the filing."
        )
    )


class AsymmetricOptionsV4Analyzer(CustomWorkflow):
    """
    Evidence-gated, temporally isolated asymmetric options screener.

    Flat Pydantic schema for Gemini structured output compatibility.
    Designed for bulk 10-K screening cross-referenced with IV rank
    and short interest data from FactSet.
    """

    name = "Asymmetric Options V4 (Evidence-Gated)"
    description = (
        "Identifies mispriced volatility via explicit filing evidence. "
        "Temporally isolated, prestige-blind. Built for LEAPS screening."
    )
    icon = "⚖️"
    min_years = 1
    category = "derivatives"

    @property
    def prompt_template(self) -> str:
        return """
================================================================================
OPERATING INSTRUCTIONS
================================================================================

You are a forensic financial analyst. You are reading a single SEC 10-K filing.

RULE 1 - TEMPORAL ISOLATION
You are reading this document on the day it was filed. You have zero knowledge
of events after this filing date: no stock moves, earnings, FDA outcomes,
lawsuits settled, acquisitions, or bankruptcies. If you notice yourself using
post-filing knowledge about this company, discard it. Work only from the text.

RULE 2 - SIZE AND PRESTIGE BLINDNESS
Market cap, brand, S&P 500 membership, credit ratings, analyst coverage, and
perceived prestige do not exist for this analysis. A going concern warning in a
$500B company scores identically to the same warning in a $5M company.
Treat every filing as if the company name is redacted.

RULE 3 - NULL HYPOTHESIS
Your default output is "No Edge (Skip)" with a composite score of 0-25.
You must find affirmative, specific, citable text in the filing to deviate.
"Interesting industry" or "growth potential" are not sufficient. You need
explicit filing text tied to a near-term, named, measurable event or risk.

================================================================================
EVIDENCE RULES
================================================================================

VALID evidence for a score above 50:
  - A named event with a specific date or quarter in the filing
  - A specific dollar amount tied to a risk or obligation
  - A named counterparty in litigation or a material contract
  - A percentage explicitly stated (e.g., "Customer A is 47% of revenue")
  - A going concern paragraph or auditor substantial doubt language
  - A specific covenant threshold with stated current proximity
  - A debt maturity date with explicit refinancing concern in the filing

INVALID evidence (do not use for high scores):
  - "The company operates in a competitive market"
  - "Regulatory changes could affect our business"
  - "We depend on key personnel"
  - General economic, FX, interest rate, or cybersecurity risk language
  - Any risk factor that appears in identical form across most 10-K filings
  - Any knowledge from your training about this company's post-filing history

================================================================================
SCORING
================================================================================

Apply the rubric in each schema field description exactly.
Use the FULL 0-100 spectrum. Do NOT cluster in the 60-75 range.
Score of 50 = genuinely ambiguous based solely on the filing.
When uncertain, score lower. High scores require strong filing citations.

Composite formula (calculate yourself, do not round until the end):
  (binary_event * 0.35) + (financial_distress * 0.30) +
  (operational_fragility * 0.20) + (opacity * 0.15)

================================================================================
CATALYST GATE
================================================================================

A catalyst qualifies ONLY if the filing explicitly states or strongly implies
(within one logical step) a timeline within 24 months of the filing date.
"Litigation is ongoing" with no stated timeline = NOT a qualifying catalyst.
If zero catalysts qualify, return an empty list. Do not populate it with
vague or indefinite risks.

================================================================================
BEGIN ANALYSIS
================================================================================

Analyze the 10-K filing for {ticker}, fiscal year {year}.
Apply all rules above. Output must match the schema exactly.
"""

    @property
    def schema(self):
        return AsymmetricOptionsV4