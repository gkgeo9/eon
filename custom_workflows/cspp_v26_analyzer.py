#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSPP v2.6 -- Causal Substrate Propagation Protocol Analyzer.

============================================================================
WHY THIS FILE LOOKS THE WAY IT DOES
============================================================================

The CSPP v2.6 framework defines 17 scored components across 5 domains plus
a dozen unscored diagnostic modules, a 10-gap audit, scenario projection,
and several required output tables. The previous version of this workflow
tried to express the entire framework as a single ~106 KB Pydantic schema
sent to Gemini in one call. That was 28x larger than the working
Buffett / Taleb / Contrarian schemas (~3.8 KB each) and failed often:
when any one of ~200 required fields drifted, Pydantic validation failed
and the whole analysis was lost (analysis_service silently logs and moves
on -- no partial recovery).

This file therefore splits the analysis into FOUR sequential Gemini calls,
each with a small Buffett-shaped sub-schema. After all four succeed, an
internal merge step assembles the partial results into the original
CSPPv26AnalysisResult shape, so DB storage and UI rendering require no
change. If any single call fails, the merge produces a degraded result
with _partial=True and _failed_call set, instead of losing the entire
analysis.

The four calls:

    Call 1: ORIENT     -- identification, doc completeness, thesis
                          classification, module diagnostics, three clocks
    Call 2: MAP        -- latent pressure table, capital actor table
    Call 3: SCORE      -- all 17 component scores (flat list) plus
                          supporting numerical context
    Call 4: SYNTHESIZE -- anti-hindsight checklist, 8-category pre-mortem,
                          decision rule, kill check, master score,
                          scenarios, falsifiers, gap audit, signal ranking,
                          executive summary

The schema property of CSPPv26Analyzer still returns the merged
CSPPv26AnalysisResult so anything that introspects workflows by their
declared schema sees the original shape.

============================================================================
DESIGN RULES OBSERVED
============================================================================

  - Every sub-schema mirrors the proven Buffett shape: mostly flat,
    all-required, no Optional, no Field defaults, no single-value Literal,
    minimal nesting.
  - The file is 100% ASCII -- no emoji, no em-dash. (Per user direction;
    Buffett/Taleb keep their emoji because they work, but this workflow
    is intentionally stripped down.)
  - Domain totals and master_score are recomputed in Python from the
    model's component scores rather than trusting the model's arithmetic.
  - Kill conditions are determined by Python from the raw scores so the
    audit cannot drift from the actual values.
"""

from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow
from eon.core import get_logger
from eon.core.exceptions import AIProviderError


logger = get_logger(__name__)


# ===========================================================================
# CONSTANTS
# ---------------------------------------------------------------------------
# Component metadata in ONE place. Used by:
#   - the SCORE call's prompt (lists which codes to score)
#   - the merge step (groups scores into the right domain object,
#     applies the right weight, computes weighted_contribution)
#   - the kill-condition check (knows which codes carry caps)
# ===========================================================================

COMPONENT_CODES = [
    "1A", "1B", "1C", "1D", "1E",
    "2A", "2B", "2C", "2D",
    "3A", "3B", "3C",
    "4A", "4B", "4C",
    "5A", "5B", "5C", "5D",
]

COMPONENT_NAMES = {
    "1A": "Substrate Truth",
    "1B": "Economic Capture Truth",
    "1C": "Financial Survival Truth",
    "1D": "Valuation Entry Truth",
    "1E": "Reflexive System Truth",
    "2A": "Latent Pressure Stage Positioning",
    "2B": "Evidence Observability",
    "2C": "Anti-Hindsight Integrity",
    "2D": "Pre-Mortem Discipline",
    "3A": "Physicalization Constraint Depth",
    "3B": "Power and Energy Position",
    "3C": "Strategic Scarcity Quality",
    "4A": "Capital Concentration Alignment",
    "4B": "Institutional Capture Favorability",
    "4C": "Hyper Mobile Capital Flow Fragility",
    "5A": "Liquidity Independence",
    "5B": "Sovereign and Trust Stability",
    "5C": "Commoditization Resistance",
    "5D": "Cost of Capital Reappearance Sensitivity",
}

# 1.0 for the three full-weight Truth Layers; 0.5 for everything else.
# With 19 components and weights 3*1.0 + 16*0.5 = 11.0, raw_total can
# theoretically reach 110, but the existing master-score cap at 100 in
# the merge step clamps it cleanly (kill conditions cap it lower still).
COMPONENT_WEIGHTS = {code: (1.0 if code in ("1A", "1B", "1C") else 0.5)
                     for code in COMPONENT_CODES}

# Which domain object each component belongs to in the final merged result.
COMPONENT_DOMAIN = {
    "1A": "i", "1B": "i", "1C": "i", "1D": "i", "1E": "i",
    "2A": "ii", "2B": "ii", "2C": "ii", "2D": "ii",
    "3A": "iii", "3B": "iii", "3C": "iii",
    "4A": "iv", "4B": "iv", "4C": "iv",
    "5A": "v", "5B": "v", "5C": "v", "5D": "v",
}

# Field name inside each Domain object that holds the ComponentScore.
COMPONENT_FIELD = {
    "1A": "substrate_truth_1A",
    "1B": "economic_capture_truth_1B",
    "1C": "financial_survival_truth_1C",
    "1D": "valuation_entry_truth_1D",
    "1E": "reflexive_system_truth_1E",
    "2A": "latent_pressure_stage_2A",
    "2B": "evidence_observability_2B",
    "2C": "anti_hindsight_integrity_2C",
    "2D": "pre_mortem_discipline_2D",
    "3A": "physicalization_constraint_3A",
    "3B": "power_and_energy_position_3B",
    "3C": "strategic_scarcity_3C",
    "4A": "capital_concentration_alignment_4A",
    "4B": "institutional_capture_favorability_4B",
    "4C": "hyper_mobile_capital_flow_4C",
    "5A": "liquidity_independence_5A",
    "5B": "sovereign_and_trust_stability_5B",
    "5C": "commoditization_resistance_5C",
    "5D": "cost_of_capital_reappearance_5D",
}

# Domain max totals. Domain IV bumped to 15 (was 10) for the addition of
# 4C; Domain V bumped to 20 (was 15) for the addition of 5D.
DOMAIN_MAX = {"i": 40, "ii": 20, "iii": 15, "iv": 15, "v": 20}


# ===========================================================================
# SUB-SCHEMA 1 of 4: ORIENT
# ---------------------------------------------------------------------------
# Flat fields only. Mirrors Buffett's shape. ~25 top-level fields.
# ===========================================================================


class OrientResult(BaseModel):
    """Call 1 output: identification + completeness + classification + diagnostics."""

    # Identification
    company_name: str = Field(
        description="Full legal company name from the 10-K cover page."
    )
    fiscal_year: int = Field(
        description="Fiscal year of the 10-K being analyzed."
    )
    primary_exchange: str = Field(
        description="Primary listing exchange (e.g. NASDAQ, NYSE). 'n/a' if unclear."
    )
    primary_thesis: str = Field(
        description=(
            "One short paragraph stating the core CSPP thesis you will be "
            "scoring. Probabilistic language, no inevitability claims."
        )
    )

    # Document completeness self-report
    full_doc: bool = Field(
        description=(
            "TRUE if you were able to read and use the ENTIRE 10-K provided. "
            "FALSE if any section appeared truncated, missing, or garbled."
        )
    )
    sections_visible: List[str] = Field(
        description=(
            "List the 10-K sections you could clearly read "
            "(e.g. 'Item 1 Business', 'Item 1A Risk Factors', 'Item 7 MD&A')."
        )
    )
    sections_missing_or_partial: List[str] = Field(
        description=(
            "List any 10-K sections that appeared missing, truncated, or "
            "garbled. Empty list if the document was clean."
        )
    )
    completeness_note: str = Field(
        description=(
            "1-3 sentences explaining your completeness assessment. If "
            "full_doc is FALSE, explain what was missing and which scores "
            "are most affected."
        )
    )

    # Thesis classification (Dual Track + 8-type typology)
    thesis_primary_track: Literal[
        "Market Visible", "Latent Civilization Pressure", "Both",
    ] = Field(
        description=(
            "Which CSPP track dominates? Market Visible = already in "
            "earnings/multiples. Latent = depends on slow variables "
            "markets have not priced. Both = genuine mix."
        )
    )
    thesis_types: List[
        Literal[
            "Real structural transformation",
            "Temporary disruption",
            "Liquidity amplified narrative",
            "Genuine scarcity repricing",
            "Pull forward demand",
            "Strategic scarcity",
            "Capital topology effect",
            "AI infrastructure effect",
        ]
    ] = Field(
        description=(
            "Which thesis archetype(s) from the CSPP typology apply? Pick "
            "all that genuinely fit, usually 1-3. Don't reach."
        )
    )
    classification_rationale: str = Field(
        description="2-4 sentences explaining the archetype choice, citing disclosures."
    )

    # Three Clocks Module
    three_clocks_physical: str = Field(
        description=(
            "Physical clock: what real-world adaptation, capex, capacity, "
            "or deployment is actually happening per the 10-K. The "
            "physical clock leads."
        )
    )
    three_clocks_financial: str = Field(
        description=(
            "Financial clock: how the physical change is expressed in "
            "earnings, margins, segment results, cash flow. Lags physical."
        )
    )
    three_clocks_narrative: str = Field(
        description=(
            "Narrative clock: how the market frames the thesis. Use "
            "'unknown - outside 10-K' if you cannot infer this."
        )
    )
    three_clocks_divergence: str = Field(
        description=(
            "Where the three clocks diverge and what that implies for "
            "stage positioning (large physical-leading-narrative gap = "
            "early stage = high 2A; narrative overshoot = crowded = low "
            "2A and low 1D)."
        )
    )

    # Module diagnostics (10 short text notes, each informing scored components)
    diagnostic_bottleneck_inflation: str = Field(
        description=(
            "Bottleneck Inflation Module (informs 1A/3A). Is the company "
            "SITTING AT a bottleneck (pricing power) or SUFFERING input-"
            "cost inflation from one (margin compression)? Cite disclosures."
        )
    )
    diagnostic_continuity_infrastructure: str = Field(
        description=(
            "Continuity Infrastructure Module (informs 1A/1B). Is the "
            "company essential infrastructure under stress (recurring, "
            "mission-critical, regulated) or discretionary?"
        )
    )
    diagnostic_capex_arms_race: str = Field(
        description=(
            "Capex Arms Race Module (informs 5C). Is capex OFFENSIVE "
            "(creating durable separation) or DEFENSIVE (keeping up, "
            "eroding ROIC)?"
        )
    )
    diagnostic_asset_holder_policy: str = Field(
        description=(
            "Asset Holder Policy Bias Module (informs 4B). Is the company "
            "an explicit beneficiary of asset-price-stabilizing policy "
            "(housing finance, REIT tax, buyback-friendly regimes)?"
        )
    )
    diagnostic_private_market_opacity: str = Field(
        description=(
            "Private Market Opacity Module (informs 4B/5B). Does the "
            "company rely on private credit, mark-to-model assets, or "
            "illiquid funding that could delay price discovery in stress?"
        )
    )
    diagnostic_sovereign_industrial_compute: str = Field(
        description=(
            "Sovereign Industrial Compute Module (informs 3B/4A). "
            "Exposure to export controls, sovereign compute buildout "
            "programs, or geographic manufacturing dependencies?"
        )
    )
    diagnostic_jurisdictional_arbitrage: str = Field(
        description=(
            "Jurisdictional Arbitrage Module (informs 4A). Is the company "
            "benefiting from or threatened by capital, labor, tax, or "
            "regulatory arbitrage between jurisdictions?"
        )
    )
    diagnostic_trust_asset_failure: str = Field(
        description=(
            "Trust Asset Failure Module (informs 5B). Is any portion of "
            "value dependent on trust rather than productive cash flow "
            "(sovereign credit, GSE wrap, deposit insurance, licensure)?"
        )
    )
    diagnostic_energy_security: str = Field(
        description=(
            "Energy Security Module (informs 3B). Is energy supply "
            "physically secure, dispatchable, geopolitically insulated, "
            "and backed up?"
        )
    )

    # AI infrastructure trigger (controls whether the AI INFRA 5th call runs).
    # CSPP v2.6 carries five dedicated AI modules (Physicalization, Power
    # First, Capex Arms Race, Model Commoditization, Sovereign Industrial
    # Compute). Collapsing them into 3B alone misses what makes v2.6
    # distinct, but they're irrelevant for most companies, so they're
    # gated behind this trigger.
    ai_infrastructure_relevant: bool = Field(
        description=(
            "TRUE if this company is directly in the AI infrastructure "
            "stack: semiconductor designers / fabs (NVDA, AMD, TSM, ASML), "
            "data center operators / REITs (EQIX, DLR), power infrastructure "
            "tied to AI load (VST, CEG, GEV, VRT), hyperscaler cloud (MSFT, "
            "AMZN, GOOGL, META, ORCL), AI software / model providers, AI "
            "networking hardware (ANET). TRUE also if AI capex / compute "
            "is a stated >10% of revenue or capex driver. FALSE otherwise. "
            "Only ~5-10% of US-listed companies should be TRUE."
        )
    )
    ai_infrastructure_rationale: str = Field(
        description=(
            "1-2 sentences explaining the ai_infrastructure_relevant flag. "
            "If TRUE, name the specific AI-stack role. If FALSE, write "
            "'Not in AI infrastructure stack.'"
        )
    )


# ===========================================================================
# SUB-SCHEMA 2 of 4: MAP
# ---------------------------------------------------------------------------
# Two lists of flat objects. moat_analyzer-shaped.
# ===========================================================================


class LatentPressureRow(BaseModel):
    """One row of the required Latent Pressure Table."""

    pressure: str = Field(
        description="The latent pressure (e.g. 'grid saturation', 'aging demographics')."
    )
    registry_category: Literal[
        "Physical", "Supply chain", "Technology", "Human",
        "Financial / institutional",
    ] = Field(description="Which Pressure Registry category this belongs to.")
    observable: bool = Field(description="Is the pressure directly observable today?")
    inductable: bool = Field(description="Is it reasonably inferable from current data?")
    flows_affected: str = Field(
        description=(
            "Which flow systems does this pressure propagate through "
            "(energy, material, human, capital, trust, liquidity, etc.)?"
        )
    )
    activation_threshold: str = Field(
        description=(
            "What level or event would activate it financially (e.g. "
            "'PJM interconnect queue exceeds 5 years')?"
        )
    )
    sectors_benefit: str = Field(
        description="Which sectors / company types BENEFIT when this activates?"
    )
    sectors_suffer: str = Field(
        description="Which sectors / company types SUFFER when this activates?"
    )
    falsifier: str = Field(
        description="What specific observation would FALSIFY this pressure's relevance?"
    )
    false_positive_risk: str = Field(
        description=(
            "Closest historical analogue from the False Positive Library "
            "(clean tech 2007, 3D printing, SPACs, metaverse, commodity "
            "supercycle) and one sentence on why this case differs or "
            "does not."
        )
    )
    financial_expression: str = Field(
        description="How would this first show up in THIS company's results?"
    )


class CapitalActorRow(BaseModel):
    """One row of the required Capital Actor Table."""

    actor: str = Field(
        description="Capital actor (e.g. 'passive index funds', 'sovereign wealth funds')."
    )
    incentive: str = Field(description="What motivates this actor's allocation.")
    flow_direction: Literal["Inflow", "Outflow", "Neutral", "Mixed"] = Field(
        description="Net direction of this actor's flow into the company / sector."
    )
    assets_affected: str = Field(description="Which assets / instruments the flow most affects.")
    political_influence: str = Field(description="The actor's political or regulatory leverage.")
    fragility_created: str = Field(
        description="What fragility (if any) this actor's flow introduces."
    )


class MapResult(BaseModel):
    """Call 2 output: latent pressure table + capital actor table."""

    latent_pressure_table: List[LatentPressureRow] = Field(
        description=(
            "At least 3 latent pressures relevant to this company, drawing "
            "from at least 2 different Pressure Registry categories. Each "
            "row must answer all of its 10 fields."
        )
    )
    capital_actor_table: List[CapitalActorRow] = Field(
        description=(
            "At least 2 capital actors most influential to this company / "
            "sector. Each row must answer all 6 fields."
        )
    )


# ===========================================================================
# SUB-SCHEMA 3 of 4: SCORE
# ---------------------------------------------------------------------------
# 17 component scores in a single flat list + supporting numerical context.
# This is the heaviest call. ComponentScoreFlat is one shape, repeated 17
# times -- much friendlier to the model than the previous 25 distinct nested
# classes.
# ===========================================================================


class ComponentScoreFlat(BaseModel):
    """One scored CSPP component. Flat shape; the merge step adds the
    weight and weighted_contribution from COMPONENT_WEIGHTS so the model
    cannot drift on arithmetic."""

    code: Literal[
        "1A", "1B", "1C", "1D", "1E",
        "2A", "2B", "2C", "2D",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C", "5D",
    ] = Field(description="CSPP component code.")
    raw_score: int = Field(
        ge=0, le=10,
        description=(
            "Raw score 0-10 per the component rubric. Score conservatively "
            "when evidence is thin -- the framework rewards calibrated "
            "uncertainty over false precision."
        )
    )
    evidence_classification: Literal[
        "Observable", "Inductable", "Weakly inferable", "Hindsight only", "Unknown",
    ] = Field(description="Real Time Evidence Standard classification of the evidence.")
    reasoning: str = Field(
        description=(
            "2-6 sentences of explicit reasoning citing specific 10-K "
            "disclosures. Probabilistic tone, never 'obviously' or 'clearly'."
        )
    )
    supporting_evidence: List[str] = Field(
        description=(
            "List of specific verifiable evidence items from the 10-K "
            "(financial figures, contract disclosures, risk factor "
            "language, segment data). Distinguish facts from inferences."
        )
    )


class ScoreResult(BaseModel):
    """Call 3 output: 17 component scores + supporting numerical context.

    The 17 scores are returned as ONE flat list (component_scores) rather
    than nested into 5 domain objects. The merge step re-nests them. This
    is the single biggest reliability improvement over the previous
    schema -- Gemini handles flat repeating shapes far better than deeply
    nested heterogeneous structures.
    """

    component_scores: List[ComponentScoreFlat] = Field(
        description=(
            "Exactly 17 entries, one per CSPP component code: "
            "1A, 1B, 1C, 1D, 1E, 2A, 2B, 2C, 2D, 3A, 3B, 3C, 4A, 4B, "
            "5A, 5B, 5C. Score every code -- do not skip any."
        )
    )

    # Domain I supporting numbers
    net_debt_to_ebitda: str = Field(
        description="Net debt / EBITDA. 'n/a' if not derivable. Justifies 1C."
    )
    interest_coverage: str = Field(
        description="EBIT / interest expense. 'n/a' if not derivable. Justifies 1C."
    )
    fcf_yield: str = Field(
        description=(
            "Free cash flow yield (FCF / market cap or FCF / EV; say "
            "which). 'unknown - outside 10-K' if market cap is unknown."
        )
    )
    nearest_debt_maturity: str = Field(
        description="Year and approximate size of nearest major debt maturity."
    )
    liquidity_buffer: str = Field(
        description="Cash + marketable securities + undrawn revolver."
    )
    current_multiple: str = Field(
        description=(
            "Best single multiple ('EV/EBITDA 14x', 'P/E 28x'). "
            "'unknown - outside 10-K' if market data unavailable."
        )
    )
    peer_multiple_range: str = Field(
        description="Peer multiple range or 'unknown - outside 10-K'."
    )
    analyst_coverage_skew: str = Field(
        description="Coverage skew ('mostly bullish' etc) or 'unknown - outside 10-K'."
    )
    valuation_stage_implication: str = Field(
        description="1-2 sentences tying the multiple vs peers vs narrative clock to 1D."
    )

    # Domain III supporting context
    primary_physical_constraint: str = Field(
        description=(
            "Dominant physical bottleneck the company sits at or depends "
            "on, or 'None - purely digital'."
        )
    )
    capex_to_revenue_pct: str = Field(
        description="Capex as % of revenue for the latest fiscal year, or 'n/a'."
    )
    disclosed_energy_agreements: List[str] = Field(
        description=(
            "Specific PPAs, captive generation, or grid agreements "
            "disclosed in the filing. Empty list if none."
        )
    )
    scarcity_type: str = Field(
        description=(
            "Scarcity type (geopolitical / regulatory / physical / "
            "technological) or 'No structural scarcity'."
        )
    )
    substitution_risks: List[str] = Field(
        description="Disclosed or evident substitution threats to the scarcity."
    )

    # Domain IV supporting context
    largest_disclosed_holders: List[str] = Field(
        description=(
            "Largest beneficial owners as disclosed in the 10-K (cover "
            "page lists >5% holders and named officer ownership). 13F-level "
            "detail is NOT in 10-K; if missing, list what is in-filing."
        )
    )
    insider_ownership_pct: str = Field(
        description="Aggregate insider/officer/director ownership %, or 'n/a'."
    )
    institutional_ownership_signal: str = Field(
        description=(
            "Qualitative signal from filing references; otherwise "
            "'unknown - outside 10-K'."
        )
    )
    key_regulatory_disclosures: List[str] = Field(
        description="Specific regulatory items from Item 1 and Item 1A that drive 4B."
    )
    government_revenue_pct: str = Field(
        description="% of revenue from government counterparties, or 'n/a'."
    )

    # Domain V supporting context
    geographic_revenue_concentration: str = Field(
        description=(
            "Concentration by jurisdiction (e.g. 'US 78%, EMEA 14%, "
            "APAC 8%'). Note primary jurisdiction sovereign rating if "
            "discernible."
        )
    )
    gross_margin_trend_3yr: str = Field(
        description="3-year gross margin trajectory, or 'insufficient history'."
    )
    roic_trend_3yr: str = Field(
        description="3-year ROIC trajectory, or 'insufficient history'."
    )
    primary_commoditization_risk: str = Field(
        description="The single most credible commoditization or substitution risk."
    )

    # Domain II supporting (the stage classification)
    primary_latent_pressure: str = Field(
        description="The single most important latent pressure for this thesis."
    )
    estimated_stage: Literal[
        "Stage 0 - Ignored",
        "Stage 1 - Niche",
        "Stage 2 - Early Capital",
        "Stage 3 - Rerating",
        "Stage 4 - Consensus",
        "Stage 5 - Crowded",
    ] = Field(description="Current recognition stage of the primary latent pressure.")

    # Domain IV / V additions (4C and 5D context)
    capital_mobility_profile: str = Field(
        description=(
            "1-3 sentences on the mobility of the capital holding this "
            "stock: which pools, fast or sticky, retail-driven or "
            "institutional, ETF-amplified, yield-chasing. Used for 4C."
        )
    )
    rate_sensitivity_profile: str = Field(
        description=(
            "1-3 sentences on this business's structural sensitivity to "
            "the cost of capital: refinancing dependence, duration of "
            "the cash flow profile, valuation tie to near-zero rates, "
            "pricing power through rate cycles. Used for 5D."
        )
    )

    # Chunk Laws check (CSPP v2.6 framework requires that the 11 Chunk
    # Laws be screened for every analysis). The model returns the IDs
    # of any laws that materially apply. The SCORE prompt enumerates
    # all 11 and instructs the model to ground each scored component
    # in any relevant law.
    chunk_laws_triggered: List[
        Literal[
            "Chunk 1 - Correct but overcapitalized",
            "Chunk 2 - Real expansion, unstable leverage",
            "Chunk 3 - Trust-dependent liquidity, nonlinear failure",
            "Chunk 4 - Low rates push capital to duration / platforms",
            "Chunk 5 - Passive flows + network effects = reflexive concentration",
            "Chunk 6 - Essentiality without supply discipline",
            "Chunk 7 - Quality growth becomes crowded",
            "Chunk 8 - Continuity infrastructure rerates in breakdown",
            "Chunk 9 - Restart economy: real bottleneck + false liquidity value",
            "Chunk 10 - Optionality without cash flow reprices when capital has a price",
            "Chunk 11 - Digital capability becomes infrastructure on physical collision",
        ]
    ] = Field(
        description=(
            "Which Chunk Laws materially apply to THIS company / thesis? "
            "Empty list is allowed if none apply, but be honest -- Chunks "
            "1, 6, and 10 in particular apply to large fractions of the "
            "listed universe. Reference any triggered law in the reasoning "
            "for the affected component score(s)."
        )
    )


# ===========================================================================
# SUB-SCHEMA 4 of 4: SYNTHESIZE
# ---------------------------------------------------------------------------
# Anti-hindsight + pre-mortem + decision rule + master synthesis.
# This is intentionally the last call so the model has the 17 scores
# from Call 3 to anchor its synthesis.
# ===========================================================================


class PreMortemScenarioFlat(BaseModel):
    """One failure-category pre-mortem scenario."""

    failure_mode: str = Field(
        description=(
            "How the thesis fails in this category given the 10-K. If the "
            "category genuinely doesn't apply, say 'Not applicable - ' "
            "followed by why."
        )
    )
    probability_pct: int = Field(
        ge=0, le=100,
        description="Estimated probability (0-100) within a 5-year horizon."
    )
    early_warning_signals: List[str] = Field(
        description="Concrete signals that this failure is unfolding."
    )
    kill_condition: str = Field(
        description=(
            "Specific measurable kill condition (e.g. 'gross margin below "
            "35% for two consecutive quarters')."
        )
    )


class ProbabilisticScenarioFlat(BaseModel):
    """One of Bull / Base / Bear."""

    name: Literal["Bull", "Base", "Bear"] = Field(description="Scenario label.")
    narrative: str = Field(description="What has to be true for this scenario.")
    probability_pct: int = Field(
        ge=0, le=100,
        description="Probability for this scenario. The three should sum to ~100."
    )
    price_target_or_outcome: str = Field(
        description="Qualitative or quantitative outcome (e.g. 'fair value +30%')."
    )
    key_drivers: List[str] = Field(
        description="2-4 drivers that distinguish this scenario."
    )


class SynthesizeResult(BaseModel):
    """Call 4 output: epistemic discipline + final synthesis."""

    # Anti-hindsight checklist (all 7 mandatory)
    ah_what_was_observable_then: str = Field(
        description="What was directly observable at the time of this 10-K?"
    )
    ah_what_was_inferable_then: str = Field(
        description="What was reasonably inferable but not directly observable?"
    )
    ah_what_was_unknowable: str = Field(
        description="What was fundamentally unknowable?"
    )
    ah_alternative_futures: List[str] = Field(
        description="At least 2 plausible alternative futures, not just the base."
    )
    ah_contradicting_signals: List[str] = Field(
        description="Specific disclosures in the 10-K that CONTRADICT the thesis."
    )
    ah_likely_blind_spots: List[str] = Field(
        description="What this analysis is likely to miss."
    )
    ah_historical_false_positives: List[str] = Field(
        description=(
            "Historical analogues from the False Positive Library that "
            "resemble this thesis, with a note on why each is or isn't different."
        )
    )

    # Pre-mortem: 8 named required categories
    pre_mortem_technology: PreMortemScenarioFlat = Field(description="Technology failure mode.")
    pre_mortem_financing: PreMortemScenarioFlat = Field(description="Financing failure mode.")
    pre_mortem_economic_capture: PreMortemScenarioFlat = Field(description="Economic capture failure mode.")
    pre_mortem_valuation: PreMortemScenarioFlat = Field(description="Valuation failure mode.")
    pre_mortem_policy: PreMortemScenarioFlat = Field(description="Policy failure mode.")
    pre_mortem_substitution: PreMortemScenarioFlat = Field(description="Substitution failure mode.")
    pre_mortem_timing: PreMortemScenarioFlat = Field(description="Timing failure mode.")
    pre_mortem_regulatory: PreMortemScenarioFlat = Field(description="Regulatory failure mode.")

    # Decision rule (all 7 mandatory)
    dr_entry_conditions: str = Field(
        description="Specific price level or evidence event to trigger initial entry."
    )
    dr_evidence_thresholds: str = Field(
        description="Further evidence that would justify scaling the position."
    )
    dr_position_sizing_guidance: str = Field(
        description="Position size relative to portfolio survivability and Domain V fragility."
    )
    dr_kill_conditions: str = Field(
        description="Position-level kill conditions distinct from score-level kills."
    )
    dr_valuation_discipline: str = Field(
        description="Maximum multiple at which to start trimming, regardless of thesis confirmation."
    )
    dr_survivability_assumptions: str = Field(
        description="What the position assumes about the company surviving stress."
    )
    dr_monitoring_signals: List[str] = Field(
        description="Measurable signals to track ongoing."
    )

    # Scenarios. (allocation_tier and capital_bucket are computed from the
    # final master_score in Python during the merge step, so we don't ask
    # the model for them -- removes ~1 KB of Literal enums from the schema
    # and prevents the model's tier choice from disagreeing with the
    # recomputed master score.)
    probabilistic_scenarios: List[ProbabilisticScenarioFlat] = Field(
        description="Exactly 3 scenarios: Bull, Base, Bear. Probabilities sum ~100."
    )

    # Thesis statement + falsifiers
    key_thesis_statement: str = Field(
        description=(
            "One paragraph stating the core causal thesis. Probabilistic. "
            "Distinguish observable / inductable / unknowable elements."
        )
    )
    primary_falsifiers: List[str] = Field(
        description=(
            "Exactly 3 specific future-observable signals that would "
            "materially reduce this score if they appeared."
        )
    )

    # Gap Safeguards Audit (all 10). 1-3 sentence audit note per gap.
    gap_quantification: str = Field(description="Were major claims quantified with disclosed numbers?")
    gap_branch_control: str = Field(description="Were alternative causal branches considered?")
    gap_narrative_psychology: str = Field(description="Did the analysis guard against narrative intoxication?")
    gap_reflexivity: str = Field(description="Were reflexive dynamics modeled explicitly?")
    gap_institutional_power: str = Field(description="Were lobbying / regulatory capture modeled?")
    gap_substitution_systems: str = Field(description="Was substitution modeled across time horizons?")
    gap_topology_analysis: str = Field(description="Was capital topology mapped beyond the company itself?")
    gap_temporal_dynamics: str = Field(description="Were the three clocks distinguished and analyzed?")
    gap_market_structure: str = Field(description="Were passive flows / ETF concentration / options gamma considered?")
    gap_civilization_hierarchy: str = Field(description="Were slow latent pressures placed above fast variables?")

    # Signal ranking
    top_signals: List[str] = Field(
        description=(
            "3-5 most causally important signals from the framework's "
            "24-signal priority list (leverage, liquidity, concentration, "
            "policy, supply, deglobalization, infrastructure, continuity, "
            "substitution, inflation, issuance quality, cost of capital, "
            "energy security, strategic scarcity, sovereign debt, capital "
            "concentration, institutional capture, power bottlenecks, "
            "compute concentration, AI physicalization, capex intensity, "
            "model commoditization)."
        )
    )
    signal_ranking_rationale: str = Field(
        description="2-4 sentences on why these signals dominate for this case."
    )

    # Executive summary
    executive_summary: str = Field(
        description=(
            "4-6 sentences: master score (will be computed by merge), tier, "
            "capital bucket, any kill condition or integrity flag, and the "
            "single most important reason a CSPP allocator would or "
            "would not act. Synthesis only -- no new claims."
        )
    )


# ===========================================================================
# FINAL MERGED RESULT SHAPE (DB / UI compatible)
# ---------------------------------------------------------------------------
# The shape downstream code expects. The merge function below assembles
# the 4 sub-results into an instance of this class. If a sub-call failed,
# the partial result is stored in *_call_raw and _failed_call / _partial
# fields indicate the degraded state.
# ===========================================================================


class ComponentScore(BaseModel):
    """A scored CSPP component as it appears in the merged result.

    Includes the computed weight and weighted_contribution (added by the
    merge step from COMPONENT_WEIGHTS, not trusted to the model).
    """

    code: Literal[
        "1A", "1B", "1C", "1D", "1E",
        "2A", "2B", "2C", "2D",
        "3A", "3B", "3C",
        "4A", "4B", "4C",
        "5A", "5B", "5C", "5D",
    ]
    name: str
    raw_score: int = Field(ge=0, le=10)
    weight: float
    weighted_contribution: float
    evidence_classification: Literal[
        "Observable", "Inductable", "Weakly inferable", "Hindsight only", "Unknown",
    ]
    reasoning: str
    supporting_evidence: List[str]
    kill_condition_triggered: bool


class FinancialSurvivalRatios(BaseModel):
    net_debt_to_ebitda: str
    interest_coverage: str
    fcf_yield: str
    nearest_debt_maturity: str
    liquidity_buffer: str


class ValuationContext(BaseModel):
    current_multiple: str
    peer_multiple_range: str
    analyst_coverage_skew: str
    stage_implication: str


class DomainI_FiveTruthLayers(BaseModel):
    substrate_truth_1A: ComponentScore
    economic_capture_truth_1B: ComponentScore
    financial_survival_truth_1C: ComponentScore
    financial_survival_ratios: FinancialSurvivalRatios
    valuation_entry_truth_1D: ComponentScore
    valuation_context: ValuationContext
    reflexive_system_truth_1E: ComponentScore
    domain_total: float = Field(ge=0, le=40)


class AntiHindsightChecklist(BaseModel):
    what_was_observable_then: str
    what_was_inferable_then: str
    what_was_unknowable: str
    alternative_futures: List[str]
    contradicting_signals: List[str]
    likely_blind_spots: List[str]
    historical_false_positives: List[str]


class PreMortemScenario(BaseModel):
    failure_mode: str
    probability_pct: int = Field(ge=0, le=100)
    early_warning_signals: List[str]
    kill_condition: str


class PreMortemScenarios(BaseModel):
    technology: PreMortemScenario
    financing: PreMortemScenario
    economic_capture: PreMortemScenario
    valuation: PreMortemScenario
    policy: PreMortemScenario
    substitution: PreMortemScenario
    timing: PreMortemScenario
    regulatory: PreMortemScenario


class DecisionRule(BaseModel):
    entry_conditions: str
    evidence_thresholds: str
    position_sizing_guidance: str
    kill_conditions: str
    valuation_discipline: str
    survivability_assumptions: str
    monitoring_signals: List[str]


class DomainII_EpistemicIntegrity(BaseModel):
    latent_pressure_stage_2A: ComponentScore
    primary_latent_pressure: str
    estimated_stage: str
    evidence_observability_2B: ComponentScore
    anti_hindsight_integrity_2C: ComponentScore
    anti_hindsight_checklist: AntiHindsightChecklist
    pre_mortem_discipline_2D: ComponentScore
    pre_mortem_scenarios: PreMortemScenarios
    decision_rule: DecisionRule
    domain_total: float = Field(ge=0, le=20)


class DomainIII_PhysicalRealityAnchor(BaseModel):
    physicalization_constraint_3A: ComponentScore
    primary_physical_constraint: str
    capex_to_revenue_pct: str
    power_and_energy_position_3B: ComponentScore
    disclosed_energy_agreements: List[str]
    strategic_scarcity_3C: ComponentScore
    scarcity_type: str
    substitution_risks: List[str]
    domain_total: float = Field(ge=0, le=15)


class DomainIV_CapitalTopology(BaseModel):
    capital_concentration_alignment_4A: ComponentScore
    largest_disclosed_holders: List[str]
    insider_ownership_pct: str
    institutional_ownership_signal: str
    institutional_capture_favorability_4B: ComponentScore
    key_regulatory_disclosures: List[str]
    government_revenue_pct: str
    hyper_mobile_capital_flow_4C: ComponentScore
    capital_mobility_profile: str
    domain_total: float = Field(ge=0, le=15)


class DomainV_FragilityProfile(BaseModel):
    liquidity_independence_5A: ComponentScore
    sovereign_and_trust_stability_5B: ComponentScore
    geographic_revenue_concentration: str
    commoditization_resistance_5C: ComponentScore
    gross_margin_trend_3yr: str
    roic_trend_3yr: str
    primary_commoditization_risk: str
    cost_of_capital_reappearance_5D: ComponentScore
    rate_sensitivity_profile: str
    domain_total: float = Field(ge=0, le=20)


class KillConditionCheck(BaseModel):
    cap_1A_substrate_triggered: bool
    cap_1C_survival_triggered: bool
    cap_1D_valuation_triggered: bool
    integrity_flag_2C_triggered: bool
    applicable_cap: int = Field(ge=0, le=100)


class ProbabilisticScenario(BaseModel):
    name: Literal["Bull", "Base", "Bear"]
    narrative: str
    probability_pct: int = Field(ge=0, le=100)
    price_target_or_outcome: str
    key_drivers: List[str]


class GapSafeguardsAudit(BaseModel):
    gap_1_quantification: str
    gap_2_branch_control: str
    gap_3_narrative_psychology: str
    gap_4_reflexivity: str
    gap_5_institutional_power: str
    gap_6_substitution_systems: str
    gap_7_topology_analysis: str
    gap_8_temporal_dynamics: str
    gap_9_market_structure: str
    gap_10_civilization_hierarchy: str


class SignalRanking(BaseModel):
    top_signals: List[str]
    ranking_rationale: str


class DocumentCompleteness(BaseModel):
    full_doc: bool
    sections_visible: List[str]
    sections_missing_or_partial: List[str]
    completeness_note: str


class ThesisClassification(BaseModel):
    primary_track: str
    thesis_types: List[str]
    classification_rationale: str


class ThreeClocks(BaseModel):
    physical_clock_state: str
    financial_clock_state: str
    narrative_clock_state: str
    clock_divergence_assessment: str


class ModuleDiagnostics(BaseModel):
    three_clocks: ThreeClocks
    bottleneck_inflation_note: str
    continuity_infrastructure_note: str
    capex_arms_race_note: str
    asset_holder_policy_bias_note: str
    private_market_opacity_note: str
    sovereign_industrial_compute_note: str
    jurisdictional_arbitrage_note: str
    trust_asset_failure_note: str
    energy_security_note: str


class AIInfrastructureAnalysis(BaseModel):
    """Conditional fifth-call output. Present only when the ORIENT call
    flagged ai_infrastructure_relevant=True. Captures the 5 v2.6 AI modules
    that the standard 3A/3B/3C rubrics can't fully express, plus suggested
    raw-score adjustments to 3A/3B/3C that the merge step applies."""

    ai_physicalization_analysis: str
    power_first_analysis: str
    capex_arms_race_analysis: str
    model_commoditization_analysis: str
    sovereign_industrial_compute_analysis: str
    key_findings: List[str]
    score_adjustment_3A: int = Field(ge=-3, le=3)
    score_adjustment_3B: int = Field(ge=-3, le=3)
    score_adjustment_3C: int = Field(ge=-3, le=3)
    adjustment_rationale: str


class CSPPv26AnalysisResult(BaseModel):
    """Final merged CSPP v2.6 analysis result.

    Assembled by _merge_results() from the 4 (or 5) sub-call outputs.
    Downstream DB storage and UI rendering see this shape (compatible
    with the previous single-call schema's top-level shape).

    If a sub-call failed, analysis_partial=True and failed_call identifies
    which call did not complete. The corresponding sections may contain
    placeholder strings.
    """

    # Identification
    company_name: str
    ticker: str
    fiscal_year: int
    primary_exchange: str
    primary_thesis: str

    # Completeness + classification + diagnostics + tables
    document_completeness: DocumentCompleteness
    thesis_classification: ThesisClassification
    module_diagnostics: ModuleDiagnostics
    latent_pressure_table: List[LatentPressureRow]
    capital_actor_table: List[CapitalActorRow]
    chunk_laws_triggered: List[str] = []

    # 5 domains
    domain_i_five_truth_layers: DomainI_FiveTruthLayers
    domain_ii_epistemic_integrity: DomainII_EpistemicIntegrity
    domain_iii_physical_reality_anchor: DomainIII_PhysicalRealityAnchor
    domain_iv_capital_topology: DomainIV_CapitalTopology
    domain_v_fragility_profile: DomainV_FragilityProfile

    # Kill check + master score + tier
    kill_condition_check: KillConditionCheck
    raw_total: float = Field(ge=0, le=110)
    master_score: int = Field(ge=0, le=100)
    allocation_tier: str
    capital_bucket: str

    # Scenarios + thesis + falsifiers + audit + ranking + summary
    probabilistic_scenarios: List[ProbabilisticScenario]
    key_thesis_statement: str
    primary_falsifiers: List[str]
    gap_safeguards_audit: GapSafeguardsAudit
    signal_ranking: SignalRanking
    executive_summary: str

    # AI infrastructure deep-dive (only populated for AI-stack companies;
    # ~5-10% of the universe). When None, the standard 3A/3B/3C scoring
    # from the SCORE call stands without adjustment.
    ai_infrastructure_analysis: Optional[AIInfrastructureAnalysis] = None
    ai_infrastructure_relevant: bool = False

    # Metadata about the multi-call run. These fields are NEVER sent to
    # Gemini (the analyze() override bypasses the default single-call
    # path), so defaults are safe here even though Gemini rejects schemas
    # with Pydantic defaults.
    analysis_partial: bool = False
    failed_call: Optional[str] = None


# ===========================================================================
# PROMPTS (one per sub-call)
# ---------------------------------------------------------------------------
# Each prompt is intentionally short and Buffett-shaped: clear field-name
# references, critical rules at the end, a final note that the response
# will be Pydantic-validated.
#
# Each prompt uses {ticker} and {year} placeholders. The CSPPv26Analyzer
# class's analyze() method calls .format() before each call.
# ===========================================================================


_PROMPT_ORIENT = """
You are applying the CSPP v2.6 (Causal Substrate Propagation Protocol)
framework to {ticker} fiscal year {year} based ONLY on the 10-K filing
provided at the end of this prompt.

This is CALL 1 of 4 (ORIENT). In this call you produce:

  - Identification (company_name, fiscal_year, primary_exchange,
    primary_thesis)
  - Document completeness self-report (full_doc, sections_visible,
    sections_missing_or_partial, completeness_note)
  - Thesis classification (Dual Track + 8-type typology +
    classification_rationale)
  - Three Clocks Module (physical, financial, narrative, divergence)
  - Nine module diagnostic notes (bottleneck_inflation, continuity_
    infrastructure, capex_arms_race, asset_holder_policy, private_
    market_opacity, sovereign_industrial_compute, jurisdictional_
    arbitrage, trust_asset_failure, energy_security)
  - AI infrastructure trigger (ai_infrastructure_relevant +
    ai_infrastructure_rationale)

Later calls will use this orientation to score the 19 CSPP components,
so be thorough here. The Three Clocks output specifically drives the
later 2A (Latent Pressure Stage Positioning) score.

AI INFRASTRUCTURE TRIGGER (important): Set ai_infrastructure_relevant
to TRUE only when this company is directly in the AI infrastructure
stack: semiconductor designers / fabs / equipment makers, data center
operators or REITs, power infrastructure tied to AI compute load,
hyperscaler cloud, AI software / model providers, AI networking gear.
Set TRUE also if AI capex or compute is a stated material (>10%)
revenue or capex driver. Set FALSE otherwise. About 5-10% of US-listed
companies should be TRUE. Examples to flag TRUE: NVDA, AMD, TSM, ASML,
EQIX, DLR, VST, CEG, GEV, VRT, MSFT, AMZN, GOOGL, META, ORCL, ANET.
Examples to flag FALSE: regional banks, restaurant chains, traditional
industrials, REITs not focused on data centers.

CRITICAL RULES:
  1. Be specific. Cite actual disclosures from the 10-K (item number,
     section name, or short quote).
  2. Be honest about full_doc. If any part of the 10-K appeared
     truncated, garbled, or missing, set full_doc to FALSE and list
     what was affected. A FALSE here is more useful than a silently-
     incomplete TRUE.
  3. Be probabilistic. No inevitability language. The CSPP framework's
     Humility Principle is non-negotiable.
  4. For each module diagnostic, write 1-3 short sentences. Use "Not
     applicable - <why>" if the module genuinely doesn't apply.

Your response will be validated against a Pydantic schema (OrientResult).
Ensure all required fields are provided.
"""


_PROMPT_MAP = """
You are continuing the CSPP v2.6 analysis of {ticker} fiscal year {year}.
This is CALL 2 of 4 (MAP). In this call you produce two required tables:

  - latent_pressure_table  (>=3 rows, drawing from >=2 Pressure Registry
                            categories)
  - capital_actor_table    (>=2 rows)

The Latent Civilization Pressure Registry includes:

  PHYSICAL              climate, heat, water, wildfire, agriculture,
                        coastal vulnerability, energy density, grid saturation
  SUPPLY CHAIN          JIT fragility, offshoring, semiconductor sovereignty,
                        single-source, reshoring, maritime chokepoints, trade
                        bloc fragmentation, transformer bottlenecks,
                        advanced packaging
  TECHNOLOGY            AI scaling, EVs, robotics, alt energy, battery cost
                        curves, cyber, space, synbio, quantum, compute
                        concentration, model commoditization
  HUMAN                 aging, fertility decline, migration, labor scarcity,
                        institutional trust decay, polarization, education
                        mismatch
  FINANCIAL/INSTITUTIONAL sovereign debt, passive concentration, central bank
                        dependency, alternative trust systems, insurance
                        withdrawal, private credit, capital concentration,
                        jurisdictional competition, institutional capture,
                        infrastructure financing

For EACH latent pressure row, answer all 11 fields including the 8-question
Latent Pressure Test (observable, inductable, flows_affected, activation_
threshold, sectors_benefit, sectors_suffer, falsifier, false_positive_risk)
plus pressure name, registry_category, and financial_expression.

CSPP STAGE PRIORITY (very important):

The Market Visibility Lag Module classifies every latent pressure by
stage:

  Stage 0 - physically real but ignored
  Stage 1 - niche awareness
  Stage 2 - early capital formation
  Stage 3 - sector rerating
  Stage 4 - consensus narrative
  Stage 5 - overcapitalized or crowded

CSPP exists to find Stage 0 to Stage 2 pressures -- ones the market has
not yet fully priced. A system that reliably finds Stage 3-4 pressures
is redundant with sell-side consensus and produces little asymmetric
value. So:

  - ACTIVELY search for Stage 0-1 pressures relevant to this company.
    Look beyond the consensus narrative. Re-read disclosures (capex
    composition, supplier concentration, energy contracts, customer
    geography, regulatory exposures, technological dependencies,
    workforce concentration) for pressures that ARE physically real
    but NOT yet in the price.
  - If every pressure you identify is already at Stage 3 or higher,
    that is itself a finding -- the thesis has limited forward-looking
    asymmetric value, and you should say so explicitly in the
    financial_expression field of the affected row(s).
  - Stage classification feeds 2A (Latent Pressure Stage Positioning)
    in the next call. Stage 0/1 -> high 2A score (8-10); Stage 4/5 ->
    low 2A score (0-3).

For the capital_actor_table, focus on actors most influential for THIS
company / sector. Examples: passive index funds, sovereign wealth funds,
private credit funds, retail option flow, corporate buybacks, foreign
reserve managers, activist holders, insider holdings.

CRITICAL RULES:
  1. Pull from the registry, but the specific pressures must be
     RELEVANT to this company. Don't list "AI scaling" for a regional
     water utility unless you can justify it.
  2. Every pressure row must have a real falsifier -- something specific
     that, if observed, would prove the pressure is not what you said
     it was. This is required to avoid narrative capture.
  3. For each false_positive_risk, name the closest historical analogue
     (clean tech 2007, 3D printing, SPACs, metaverse, commodity
     supercycle) and say in one sentence why this case differs or does
     not.
  4. At least one pressure row should be at Stage 0-2 if you can
     credibly identify one. If you cannot, the row at the lowest stage
     should explicitly say "Stage 3+ - no genuinely under-priced pressure
     surfaced" in financial_expression.

Your response will be validated against a Pydantic schema (MapResult).
Ensure all required fields are provided.

Earlier orientation output (for context):
{orient_context}
"""


_PROMPT_SCORE = """
You are continuing the CSPP v2.6 analysis of {ticker} fiscal year {year}.
This is CALL 3 of 4 (SCORE). In this call you produce all 19 component
scores plus the supporting numerical context that justifies them.

Return exactly 19 entries in component_scores, one per code:
  1A 1B 1C 1D 1E 2A 2B 2C 2D 3A 3B 3C 4A 4B 4C 5A 5B 5C 5D
For each:
  - code: the CSPP code
  - raw_score: integer 0-10 per the framework rubric below
  - evidence_classification: Observable / Inductable / Weakly inferable /
    Hindsight only / Unknown
  - reasoning: 2-6 sentences citing specific 10-K disclosures
  - supporting_evidence: list of verifiable evidence items

The merge step will add the framework-defined weight and weighted
contribution -- do not compute them yourself.

CHUNK LAW PRE-SCREEN (mandatory before scoring):

Before scoring, work through the 11 CSPP Chunk Laws. For any that
materially apply to THIS company / thesis, add the law's ID to
chunk_laws_triggered and reference it in the affected component
score(s)' reasoning. Empty list is allowed only when none genuinely
apply -- be honest, Chunks 1, 6, and 10 cover large fractions of the
listed universe.

  Chunk 1  - Transformations can be correct but catastrophically
             overcapitalized.       (Lowers 1D when triggered.)
  Chunk 2  - Real expansions can become dangerous through unstable
             leverage.              (Lowers 1C and 5A.)
  Chunk 3  - Trust-dependent liquidity systems can fail nonlinearly.
                                     (Lowers 5B.)
  Chunk 4  - Low rates push capital toward duration and scalable
             platforms.             (Affects 1D, 5D.)
  Chunk 5  - Passive flows and network effects create reflexive
             concentration.         (Affects 4A, 1E.)
  Chunk 6  - Essentiality does not equal pricing power when supply
             discipline collapses. (Lowers 1B.)
  Chunk 7  - Quality growth can become crowded.       (Lowers 1D, 2A.)
  Chunk 8  - Continuity infrastructure rerates when normal
             coordination breaks. (Raises 1B for continuity infra.)
  Chunk 9  - Restart economies create real bottleneck value and false
             liquidity value simultaneously.  (Affects 3A, 4C.)
  Chunk 10 - When capital has a price again, optionality without cash
             flow reprices violently. (Lowers 1D, 5D.)
  Chunk 11 - Digital capability becomes investable infrastructure when
             it collides with physical constraints.   (Raises 3A.)

STAGE 0-2 PRIORITY (carries over from MAP):

CSPP seeks Stage 0-2 pressures. Score 2A high (8-10) only when the
primary latent pressure is genuinely at Stage 0-1 (physically real but
unrecognized). Score 2A low (0-3) when the pressure is at Stage 4-5
(consensus or crowded). The estimated_stage field you set drives 2A.

RUBRICS (abbreviated -- score conservatively when evidence is thin):

  Domain I (Five Truth Layers)
    1A Substrate Truth (w=1.0)        0=narrative; 10=irreversible & quantified
                                      KILL if raw<=2 (caps master at 40)
    1B Economic Capture (w=1.0)       0=commodity; 10=near-monopolistic capture
                                      (Apply Chunk 6, Chunk 8.)
    1C Financial Survival (w=1.0)     0=insolvency risk; 10=fortress / anti-fragile
                                      KILL if raw<=2 (caps master at 50)
                                      Populate the 5 financial_survival ratio
                                      fields with actual numbers.
                                      (Apply Chunk 2.)
    1D Valuation Entry (w=0.5)        0=crowded/priced-for-perfection; 10=deeply
                                      undercapitalized. If you lack market data,
                                      score 4-6 and say so in reasoning.
                                      KILL if raw<=1 (caps master at 60)
                                      (Apply Chunks 1, 4, 7, 10.)
    1E Reflexive System (w=0.5)       0=destructive reflexivity; 10=constructive
                                      feedback loop                (Apply Chunk 5.)

  Domain II (Epistemic Integrity)
    2A Latent Pressure Stage (w=0.5)  Stage 0/1 = 8-10; Stage 2/3 = 5-7;
                                      Stage 4 = 3-4; Stage 5 = 0-2.
    2B Evidence Observability (w=0.5) % of claims directly visible in 10-K
    2C Anti-Hindsight Integrity (w=0.5) Will be set after Call 4 fills the
                                      checklist; in this call score the
                                      ANALYSIS DISCIPLINE -- be conservative
                                      (5-7 typical). raw<=1 = integrity flag.
    2D Pre-Mortem Discipline (w=0.5)  Will be set after Call 4 produces the
                                      pre-mortem; in this call score 5-7
                                      pending completion.

  Domain III (Physical Reality Anchor)
    3A Physicalization (w=0.5)        0=purely digital with no constraint;
                                      10=hard physical ceiling owned. Pure
                                      SaaS may legitimately be 0-2 -- correct,
                                      not a flaw.                   (Apply Chunk 11.)
    3B Power and Energy (w=0.5)       0=commodity grid consumer; 10=monopoly
                                      power control
    3C Strategic Scarcity (w=0.5)     0=abundant substitutes; 10=absolute
                                      scarcity, fully monetized

  Domain IV (Capital Topology)
    4A Capital Concentration (w=0.5)  Use disclosed beneficial ownership.
                                      13F-level data NOT in 10-K -- if
                                      missing, say so.              (Apply Chunk 5.)
    4B Institutional Capture (w=0.5)  Use Item 1 / Item 1A regulatory
                                      disclosures.
    4C Hyper Mobile Capital Flow (w=0.5)
                                      Score the FRAGILITY of the capital base
                                      holding this stock. Hyper Mobile Capital
                                      Flow Module asks: which pools? fast or
                                      sticky? retail-swarm exposed? ETF
                                      concentration? yield-chasing? Score
                                      0=stock dominated by hot, fast, retail/
                                      yield-chasing flows that reprice
                                      violently (e.g. BDC at large NAV premium
                                      driven by retail yield demand);
                                      10=stock dominated by sticky long-
                                      duration holders insensitive to flow
                                      shocks. Populate capital_mobility_profile
                                      with 1-3 sentences.        (Apply Chunk 9.)

  Domain V (Fragility Profile)
    5A Liquidity Independence (w=0.5) 0=collapses in tight money; 10=anti-
                                      fragile in tight money       (Apply Chunk 2.)
    5B Sovereign / Trust Stability (w=0.5) 0=fully sovereign-dependent;
                                      10=independent / anti-fragile (Apply Chunk 3.)
    5C Commoditization Resistance (w=0.5) Use 3yr GM and ROIC trends.
    5D Cost of Capital Reappearance (w=0.5)
                                      Score STRUCTURAL sensitivity to cost
                                      of capital, distinct from 5A's current-
                                      state snapshot. The Cost of Capital
                                      Reappearance Module asks: does the
                                      business model depend on cheap
                                      refinancing? does the valuation depend
                                      on near-zero rates? does the firm
                                      maintain pricing power through a rate
                                      cycle? Score 0=valuation and viability
                                      collapse without cheap capital (long-
                                      duration cash-burn growth, optionality
                                      without earnings); 10=indifferent to
                                      rate regime (cash-generative, low
                                      duration, pricing power). Populate
                                      rate_sensitivity_profile with 1-3
                                      sentences.                  (Apply Chunks 4, 10.)

ALSO populate all supporting context fields:
  - 5 financial_survival ratio fields (net_debt_to_ebitda, interest_
    coverage, fcf_yield, nearest_debt_maturity, liquidity_buffer)
  - 4 valuation context fields (current_multiple, peer_multiple_range,
    analyst_coverage_skew, valuation_stage_implication)
  - Domain III/IV/V supporting strings (including capital_mobility_profile
    for 4C and rate_sensitivity_profile for 5D)
  - primary_latent_pressure and estimated_stage (used for 2A)
  - chunk_laws_triggered

CRITICAL RULES:
  1. Score every one of the 19 codes -- do not skip.
  2. Use "n/a" or "unknown - outside 10-K" rather than skipping a string
     field. Empty list is fine for ACTUALLY empty fields.
  3. Be honest about uncertainty. Score conservatively when evidence is
     thin. The framework rewards calibrated uncertainty over false precision.
  4. Distinguish 5A (current liquidity snapshot) from 5D (structural
     sensitivity to a higher cost-of-capital regime). A company can
     have $1B in cash today (high 5A) and still be highly 5D-fragile
     if its valuation depends on near-zero rates.

Your response will be validated against a Pydantic schema (ScoreResult).
Ensure all required fields are provided.

Earlier orientation output (for context):
{orient_context}

Earlier mapping output (for context):
{map_context}
"""


_PROMPT_SYNTHESIZE = """
You are completing the CSPP v2.6 analysis of {ticker} fiscal year {year}.
This is CALL 4 of 4 (SYNTHESIZE). The orientation, mapping, and scoring
have all been done. You now produce:

  - Anti-hindsight checklist (all 7 questions answered)
  - Pre-mortem across all 8 failure categories (technology, financing,
    economic_capture, valuation, policy, substitution, timing, regulatory)
  - Decision rule (all 7 fields: entry_conditions, evidence_thresholds,
    position_sizing_guidance, kill_conditions, valuation_discipline,
    survivability_assumptions, monitoring_signals)
  - Bull/Base/Bear scenarios (exactly 3; probabilities sum ~100)
  - Allocation tier and capital bucket (based on the projected master
    score in the supplied context)
  - Key thesis statement (probabilistic, distinguishing observable /
    inductable / unknowable)
  - Exactly 3 primary falsifiers
  - Gap Safeguards Audit (all 10 gaps with short notes)
  - Signal Ranking (3-5 top signals from the framework's 24-signal list,
    plus rationale)
  - Executive summary (4-6 sentences, synthesis only)

The master score and kill-condition booleans are recomputed by the merge
step from the raw scores in Call 3 -- you do not need to compute them.
But your allocation_tier and capital_bucket choices should be consistent
with the master_score_projection provided in the context below.

CRITICAL RULES:
  1. The anti-hindsight checklist must include real CONTRADICTING
     signals from the 10-K and real HISTORICAL FALSE POSITIVES with
     honest differentiation. This is what 2C tests for.
  2. Every pre-mortem category must be addressed. If a category truly
     doesn't apply, write "Not applicable - <why>" in failure_mode and
     give probability 1-5%.
  3. Decision rule kill_conditions are POSITION-level (when to fully
     exit the position), distinct from the framework's score-level
     kill conditions.
  4. Exactly 3 falsifiers, each specific, future-observable, and
     measurable.
  5. The executive_summary is synthesis ONLY -- do not introduce new
     claims beyond what is in the earlier calls.

Your response will be validated against a Pydantic schema (SynthesizeResult).
Ensure all required fields are provided.

Earlier orientation output:
{orient_context}

Earlier mapping output:
{map_context}

Earlier scoring output (and projected master score):
{score_context}
"""


_PROMPT_AI_INFRA = """
You are running the AI INFRASTRUCTURE deep-dive for {ticker} fiscal year
{year}. This call ONLY runs when the ORIENT call flagged
ai_infrastructure_relevant=TRUE, so {ticker} is in the AI infrastructure
stack (semiconductors, data centers, AI power, hyperscaler cloud, AI
software / model providers, AI networking).

The standard 3A/3B/3C rubrics in the SCORE call use a one-size-fits-all
energy-and-physicalization framing. For AI-stack companies that framing
misses what makes CSPP v2.6 distinctive: the AI Physicalization, Power
First, Capex Arms Race, Model Commoditization, and Sovereign Industrial
Compute modules. Your job in this call is to apply those five modules
specifically and then suggest small adjustments to the 3A/3B/3C raw
scores.

You must produce paragraph-length analyses for all five modules. Each
should cite specific 10-K disclosures and answer the module's framework
questions directly:

AI PHYSICALIZATION MODULE (ai_physicalization_analysis):
  What physical inputs does the digital system require? Which inputs
  are bottlenecked? Who owns those bottlenecks? Can supply scale at
  software speed? Where does the bottleneck migrate next?
  CSPP Law: Digital capability becomes investable infrastructure when
  it collides with physical constraints.

POWER FIRST MODULE (power_first_analysis):
  Is power available? Is it dispatchable? Is it cheap enough? Is
  interconnection available? Who pays for grid upgrades? Is the load
  politically acceptable?
  CSPP Law: For AI infrastructure, power access can become more
  strategic than software access.

CAPEX ARMS RACE MODULE (capex_arms_race_analysis):
  Is capex offensive or defensive? Are firms investing for returns or
  survival? Are returns measurable? Does competition commoditize
  output? Who bears stranded asset risk?
  CSPP Law: Strategic capex can be rational individually and excessive
  collectively.

MODEL COMMODITIZATION MODULE (model_commoditization_analysis):
  Are models differentiating or converging? Is value moving toward
  infrastructure, workflow, data, or distribution? Does open source
  compress margins? Can customers switch providers easily? Who owns
  the workflow?
  CSPP Law: In AI, capability alone may not equal durable economic
  capture.

SOVEREIGN INDUSTRIAL COMPUTE MODULE (sovereign_industrial_compute_analysis):
  Is compute becoming nationally strategic? Are export controls
  reshaping supply? Are governments subsidizing capacity? Which
  countries control chips, fabs, and energy? Could compute access
  become geopolitical leverage?
  CSPP Law: Compute is becoming a sovereign industrial asset, not
  merely a corporate input.

Then:

  - key_findings: 3-5 bullet-point findings synthesizing the modules.
  - score_adjustment_3A: integer -3 to +3. Suggest an adjustment to
    raise or lower the 3A (Physicalization) raw score from the SCORE
    call, based on Chunk 11. Positive when the AI physical collision
    is owned / monetizable (3A under-scores it); negative when the
    company is exposed to but does not own the physical bottleneck.
  - score_adjustment_3B: integer -3 to +3. Adjust 3B (Power and
    Energy) based on the Power First module. Positive when power is
    a structural advantage (long PPAs, dispatchable behind-the-meter,
    interconnection control); negative when power dependency is
    fragile (uncontracted, grid-constrained, politically contested).
  - score_adjustment_3C: integer -3 to +3. Adjust 3C (Strategic
    Scarcity) based on Capex Arms Race + Model Commoditization +
    Sovereign Industrial Compute. Positive when the company controls
    a sovereign-relevant scarce asset (export-controlled fabs, EUV
    monopoly); negative when capex is defensive / commoditizing /
    geopolitically exposed.
  - adjustment_rationale: 2-4 sentences justifying the three numbers
    so the merge step's audit trail makes sense.

Adjustments are clamped to keep the final 3A/3B/3C raw_scores within
[0, 10]. Stay conservative -- the typical adjustment is -1, 0, or +1.
Use larger magnitudes only when one module dominates the thesis.

CRITICAL RULES:
  1. Cite specific 10-K disclosures in each module analysis. Capex
     amounts, named suppliers, power agreements, segment revenue mix,
     export-control language, capital commitments.
  2. Score adjustments must be supported by the module text above
     them. Do not invent positives or negatives without grounding.
  3. Probabilistic language. No "AI will" claims.

Your response will be validated against a Pydantic schema
(AIInfrastructureAnalysis). Ensure all required fields are provided.

Earlier orientation output:
{orient_context}

Earlier scoring output (so you can calibrate adjustments against the
3A/3B/3C scores already given):
{score_context}
"""


# ===========================================================================
# WORKFLOW CLASS
# ---------------------------------------------------------------------------
# Overrides CustomWorkflow.analyze() to orchestrate the 4 calls and merge
# the partial results into a CSPPv26AnalysisResult instance.
# ===========================================================================


class CSPPv26Analyzer(CustomWorkflow):
    """CSPP v2.6 multi-part 10-K analyzer.

    Splits the analysis into 4 sequential Gemini calls (ORIENT / MAP /
    SCORE / SYNTHESIZE), each with a small Buffett-shaped schema. Merges
    the four partial results into a single CSPPv26AnalysisResult.

    The schema property returns CSPPv26AnalysisResult for downstream
    compatibility, but the framework's default single-call flow is
    bypassed in favor of the overridden analyze() method.
    """

    name = "CSPP v2.6 - Causal Substrate Propagation"
    description = (
        "Apply the Causal Substrate Propagation Protocol v2.6 to one "
        "fiscal year of a 10-K. Runs as 4 sequential Gemini calls "
        "(orient / map / score / synthesize) plus a conditional 5th "
        "call (AI infrastructure deep-dive) for AI-stack companies, "
        "and merges the results into a 0-100 master score with 19 "
        "component scores, Chunk Law checks, kill condition audit, "
        "scenarios, gap audit, and allocation tier."
    )
    icon = "[CSPP]"
    min_years = 1
    max_years = 1
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        # Required by the base class. Not used by the orchestrated
        # analyze() path -- each sub-call uses its own prompt below.
        # We return the ORIENT prompt as a sensible default so the
        # validation in CustomWorkflow.validate_workflow() passes.
        return _PROMPT_ORIENT

    @property
    def schema(self):
        # Downstream code introspects this; we keep it as the final
        # merged shape for DB/UI compatibility.
        return CSPPv26AnalysisResult

    # ---- orchestrated multi-call analysis ---------------------------------

    def analyze(self, ticker: str, year: int, text: str, provider) -> CSPPv26AnalysisResult:
        """Run the 4 sub-calls and merge into a CSPPv26AnalysisResult.

        Each sub-call is independent -- if one fails, the others still run
        and the merge produces a degraded result with _partial=True and
        _failed_call set, so downstream code can surface the partial
        analysis rather than silently losing the run.
        """
        filing_block = f"\n\nHere's the filing content:\n\n{text}"

        # --- Call 1: ORIENT ----------------------------------------------
        orient_obj: Optional[OrientResult] = None
        orient_err: Optional[str] = None
        try:
            prompt = _PROMPT_ORIENT.format(ticker=ticker, year=year) + filing_block
            orient_obj = provider.generate_with_retry(
                prompt=prompt, schema=OrientResult,
                max_retries=3, retry_delay=10,
            )
            logger.info(f"CSPP ORIENT call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            orient_err = str(e)
            logger.error(f"CSPP ORIENT call failed for {ticker} {year}: {e}")

        # --- Call 2: MAP -------------------------------------------------
        map_obj: Optional[MapResult] = None
        map_err: Optional[str] = None
        try:
            orient_ctx = (orient_obj.model_dump_json(indent=2) if orient_obj
                          else "(ORIENT call failed; proceed without it)")
            prompt = _PROMPT_MAP.format(
                ticker=ticker, year=year, orient_context=orient_ctx,
            ) + filing_block
            map_obj = provider.generate_with_retry(
                prompt=prompt, schema=MapResult,
                max_retries=3, retry_delay=10,
            )
            logger.info(f"CSPP MAP call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            map_err = str(e)
            logger.error(f"CSPP MAP call failed for {ticker} {year}: {e}")

        # --- Call 3: SCORE -----------------------------------------------
        score_obj: Optional[ScoreResult] = None
        score_err: Optional[str] = None
        try:
            orient_ctx = (orient_obj.model_dump_json(indent=2) if orient_obj
                          else "(ORIENT call failed)")
            map_ctx = (map_obj.model_dump_json(indent=2) if map_obj
                       else "(MAP call failed)")
            prompt = _PROMPT_SCORE.format(
                ticker=ticker, year=year,
                orient_context=orient_ctx, map_context=map_ctx,
            ) + filing_block
            score_obj = provider.generate_with_retry(
                prompt=prompt, schema=ScoreResult,
                max_retries=3, retry_delay=10,
            )
            logger.info(f"CSPP SCORE call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            score_err = str(e)
            logger.error(f"CSPP SCORE call failed for {ticker} {year}: {e}")

        # --- Call 4 (conditional): AI INFRASTRUCTURE deep-dive ----------
        # Only runs when ORIENT flagged this company as AI-stack relevant
        # (~5-10% of US-listed companies). For the other 92-95%, the
        # ai_infrastructure_analysis section stays None in the final
        # result and no extra Gemini cost is incurred.
        ai_infra_obj: Optional[AIInfrastructureAnalysis] = None
        ai_infra_relevant = bool(
            orient_obj and orient_obj.ai_infrastructure_relevant
        )
        if ai_infra_relevant and score_obj is not None:
            try:
                orient_ctx = orient_obj.model_dump_json(indent=2)
                score_ctx = score_obj.model_dump_json(indent=2)
                prompt = _PROMPT_AI_INFRA.format(
                    ticker=ticker, year=year,
                    orient_context=orient_ctx, score_context=score_ctx,
                ) + filing_block
                ai_infra_obj = provider.generate_with_retry(
                    prompt=prompt, schema=AIInfrastructureAnalysis,
                    max_retries=3, retry_delay=10,
                )
                logger.info(f"CSPP AI_INFRA call succeeded for {ticker} {year}")
            except (AIProviderError, Exception) as e:
                # Non-fatal -- AI infra is supplementary, not required.
                logger.warning(
                    f"CSPP AI_INFRA call failed for {ticker} {year}: {e}. "
                    f"Falling back to base 3A/3B/3C scores."
                )

        # --- Call 5: SYNTHESIZE -----------------------------------------
        synth_obj: Optional[SynthesizeResult] = None
        synth_err: Optional[str] = None
        try:
            orient_ctx = (orient_obj.model_dump_json(indent=2) if orient_obj
                          else "(ORIENT call failed)")
            map_ctx = (map_obj.model_dump_json(indent=2) if map_obj
                       else "(MAP call failed)")
            # Project master score from the (possibly adjusted) Call 3 +
            # AI INFRA so Call 5 can pick a consistent allocation tier.
            if score_obj is not None:
                projected_master = _compute_master_score_from_components(
                    score_obj.component_scores,
                    ai_infra=ai_infra_obj,
                )
                score_ctx = (
                    score_obj.model_dump_json(indent=2)
                    + f"\n\n[projected master_score from raw component scores "
                    + f"(includes AI INFRA adjustments if applicable): "
                    + f"{projected_master}]"
                )
            else:
                score_ctx = "(SCORE call failed; do your best to synthesize without component scores)"
            prompt = _PROMPT_SYNTHESIZE.format(
                ticker=ticker, year=year,
                orient_context=orient_ctx, map_context=map_ctx,
                score_context=score_ctx,
            ) + filing_block
            synth_obj = provider.generate_with_retry(
                prompt=prompt, schema=SynthesizeResult,
                max_retries=3, retry_delay=10,
            )
            logger.info(f"CSPP SYNTHESIZE call succeeded for {ticker} {year}")
        except (AIProviderError, Exception) as e:
            synth_err = str(e)
            logger.error(f"CSPP SYNTHESIZE call failed for {ticker} {year}: {e}")

        # --- Merge -------------------------------------------------------
        failed = []
        if orient_obj is None:
            failed.append("ORIENT")
        if map_obj is None:
            failed.append("MAP")
        if score_obj is None:
            failed.append("SCORE")
        if synth_obj is None:
            failed.append("SYNTHESIZE")

        if not failed:
            merged = _merge_results(
                ticker, orient_obj, map_obj, score_obj, synth_obj,
                ai_infra=ai_infra_obj,
            )
            return merged

        # Degraded merge -- fill missing parts with placeholders so the
        # final shape still validates and the user gets *something*.
        if score_obj is None and synth_obj is None:
            # Both heavy calls failed -- raise so the analysis service
            # logs a clean failure rather than producing near-empty output.
            raise AIProviderError(
                "CSPP v2.6: both SCORE and SYNTHESIZE calls failed; "
                "cannot produce a meaningful result. "
                f"Errors: SCORE={score_err}; SYNTHESIZE={synth_err}"
            )

        merged = _merge_results(
            ticker, orient_obj, map_obj, score_obj, synth_obj,
            ai_infra=ai_infra_obj,
            partial=True, failed_calls=failed,
        )
        return merged


# ===========================================================================
# MERGE HELPERS
# ---------------------------------------------------------------------------
# Pure functions that take the 4 sub-call outputs and assemble a
# CSPPv26AnalysisResult. All arithmetic happens here (not in the model)
# so it cannot drift.
# ===========================================================================


def _placeholder_component(code: str) -> ComponentScore:
    """Build a placeholder ComponentScore for a code when SCORE failed."""
    return ComponentScore(
        code=code,
        name=COMPONENT_NAMES[code],
        raw_score=0,
        weight=COMPONENT_WEIGHTS[code],
        weighted_contribution=0.0,
        evidence_classification="Unknown",
        reasoning="Score call failed; placeholder generated by merge step.",
        supporting_evidence=[],
        kill_condition_triggered=False,
    )


def _apply_ai_infra_adjustment(
    raw_score: int,
    adjustment: int,
) -> int:
    """Apply an AI INFRA adjustment to a 3A/3B/3C raw score, clamped to [0, 10]."""
    return max(0, min(10, raw_score + adjustment))


def _adjusted_raw_score(
    flat: ComponentScoreFlat,
    ai_infra: Optional["AIInfrastructureAnalysis"],
) -> int:
    """Return the raw_score for a flat ComponentScoreFlat, applying any
    AI infrastructure adjustment for 3A/3B/3C. Other codes pass through."""
    if ai_infra is None:
        return flat.raw_score
    if flat.code == "3A":
        return _apply_ai_infra_adjustment(flat.raw_score, ai_infra.score_adjustment_3A)
    if flat.code == "3B":
        return _apply_ai_infra_adjustment(flat.raw_score, ai_infra.score_adjustment_3B)
    if flat.code == "3C":
        return _apply_ai_infra_adjustment(flat.raw_score, ai_infra.score_adjustment_3C)
    return flat.raw_score


def _compute_master_score_from_components(
    flats: List[ComponentScoreFlat],
    ai_infra: Optional["AIInfrastructureAnalysis"] = None,
) -> int:
    """Pre-compute the master score for use in the SYNTHESIZE prompt context.
    Applies AI INFRA adjustments to 3A/3B/3C if provided."""
    by_code = {c.code: c for c in flats}
    raw_total = 0.0
    for code in COMPONENT_CODES:
        if code in by_code:
            rs = _adjusted_raw_score(by_code[code], ai_infra)
            raw_total += rs * COMPONENT_WEIGHTS[code]
    cap = _compute_cap(by_code)
    return int(round(min(raw_total, cap)))


def _compute_cap(by_code: Dict[str, ComponentScoreFlat]) -> int:
    """Determine the lowest applicable master-score cap from raw scores."""
    cap = 100
    s1A = by_code.get("1A")
    s1C = by_code.get("1C")
    s1D = by_code.get("1D")
    if s1A and s1A.raw_score <= 2:
        cap = min(cap, 40)
    if s1C and s1C.raw_score <= 2:
        cap = min(cap, 50)
    if s1D and s1D.raw_score <= 1:
        cap = min(cap, 60)
    return cap


def _tier_from_score(score: int) -> str:
    if score >= 85:
        return "Exceptional (85-100)"
    if score >= 70:
        return "High conviction (70-84)"
    if score >= 55:
        return "Moderate conviction (55-69)"
    if score >= 40:
        return "Low conviction (40-54)"
    if score >= 25:
        return "Speculative (25-39)"
    return "Reject (0-24)"


def _bucket_from_score(score: int) -> str:
    if score >= 85:
        return "Core capital"
    if score >= 70:
        return "Defensive growth"
    if score >= 55:
        return "Transition capital"
    if score >= 40:
        return "Watchlist capital"
    if score >= 25:
        return "Optionality capital"
    return "Avoid capital"


def _flat_to_full(
    flat: ComponentScoreFlat,
    ai_infra: Optional["AIInfrastructureAnalysis"] = None,
) -> ComponentScore:
    """Convert a Call-3 flat score to the merged ComponentScore shape.

    If ai_infra is provided AND the code is 3A/3B/3C, the raw_score is
    adjusted within [0, 10] per the AI INFRA call's recommendation and
    a short note is appended to the reasoning so the audit trail shows
    what changed."""
    weight = COMPONENT_WEIGHTS[flat.code]
    adjusted = _adjusted_raw_score(flat, ai_infra)
    adjustment_note = ""
    if ai_infra is not None and flat.code in ("3A", "3B", "3C"):
        adj = {"3A": ai_infra.score_adjustment_3A,
               "3B": ai_infra.score_adjustment_3B,
               "3C": ai_infra.score_adjustment_3C}[flat.code]
        if adj != 0:
            adjustment_note = (
                f" [AI INFRA adjustment {adj:+d}: base {flat.raw_score} -> "
                f"adjusted {adjusted}.]"
            )
    weighted = round(adjusted * weight, 2)
    kill = (
        (flat.code == "1A" and adjusted <= 2)
        or (flat.code == "1C" and adjusted <= 2)
        or (flat.code == "1D" and adjusted <= 1)
        or (flat.code == "2C" and adjusted <= 1)
    )
    return ComponentScore(
        code=flat.code,
        name=COMPONENT_NAMES[flat.code],
        raw_score=adjusted,
        weight=weight,
        weighted_contribution=weighted,
        evidence_classification=flat.evidence_classification,
        reasoning=flat.reasoning + adjustment_note,
        supporting_evidence=flat.supporting_evidence,
        kill_condition_triggered=kill,
    )


def _placeholder_pre_mortem(reason: str) -> PreMortemScenario:
    return PreMortemScenario(
        failure_mode=f"Not analyzed - {reason}",
        probability_pct=0,
        early_warning_signals=[],
        kill_condition="n/a",
    )


def _merge_results(
    ticker: str,
    orient: Optional[OrientResult],
    map_r: Optional[MapResult],
    score: Optional[ScoreResult],
    synth: Optional[SynthesizeResult],
    ai_infra: Optional[AIInfrastructureAnalysis] = None,
    partial: bool = False,
    failed_calls: Optional[List[str]] = None,
) -> CSPPv26AnalysisResult:
    """Assemble the 4 (or 5) sub-results into a CSPPv26AnalysisResult."""

    # --- 1. Identification + completeness + classification + diagnostics ---
    if orient is not None:
        company_name = orient.company_name
        fiscal_year = orient.fiscal_year
        primary_exchange = orient.primary_exchange
        primary_thesis = orient.primary_thesis
        doc_completeness = DocumentCompleteness(
            full_doc=orient.full_doc,
            sections_visible=orient.sections_visible,
            sections_missing_or_partial=orient.sections_missing_or_partial,
            completeness_note=orient.completeness_note,
        )
        thesis_classification = ThesisClassification(
            primary_track=orient.thesis_primary_track,
            thesis_types=list(orient.thesis_types),
            classification_rationale=orient.classification_rationale,
        )
        module_diagnostics = ModuleDiagnostics(
            three_clocks=ThreeClocks(
                physical_clock_state=orient.three_clocks_physical,
                financial_clock_state=orient.three_clocks_financial,
                narrative_clock_state=orient.three_clocks_narrative,
                clock_divergence_assessment=orient.three_clocks_divergence,
            ),
            bottleneck_inflation_note=orient.diagnostic_bottleneck_inflation,
            continuity_infrastructure_note=orient.diagnostic_continuity_infrastructure,
            capex_arms_race_note=orient.diagnostic_capex_arms_race,
            asset_holder_policy_bias_note=orient.diagnostic_asset_holder_policy,
            private_market_opacity_note=orient.diagnostic_private_market_opacity,
            sovereign_industrial_compute_note=orient.diagnostic_sovereign_industrial_compute,
            jurisdictional_arbitrage_note=orient.diagnostic_jurisdictional_arbitrage,
            trust_asset_failure_note=orient.diagnostic_trust_asset_failure,
            energy_security_note=orient.diagnostic_energy_security,
        )
    else:
        company_name = ticker
        fiscal_year = 0
        primary_exchange = "n/a"
        primary_thesis = "ORIENT call failed; thesis not generated."
        doc_completeness = DocumentCompleteness(
            full_doc=False,
            sections_visible=[],
            sections_missing_or_partial=["ORIENT call failed"],
            completeness_note="The ORIENT sub-call did not return a result.",
        )
        thesis_classification = ThesisClassification(
            primary_track="Both",
            thesis_types=[],
            classification_rationale="ORIENT call failed.",
        )
        module_diagnostics = ModuleDiagnostics(
            three_clocks=ThreeClocks(
                physical_clock_state="n/a",
                financial_clock_state="n/a",
                narrative_clock_state="n/a",
                clock_divergence_assessment="ORIENT call failed.",
            ),
            bottleneck_inflation_note="ORIENT call failed.",
            continuity_infrastructure_note="ORIENT call failed.",
            capex_arms_race_note="ORIENT call failed.",
            asset_holder_policy_bias_note="ORIENT call failed.",
            private_market_opacity_note="ORIENT call failed.",
            sovereign_industrial_compute_note="ORIENT call failed.",
            jurisdictional_arbitrage_note="ORIENT call failed.",
            trust_asset_failure_note="ORIENT call failed.",
            energy_security_note="ORIENT call failed.",
        )

    # --- 2. Tables --------------------------------------------------------
    if map_r is not None:
        latent_pressure_table = map_r.latent_pressure_table
        capital_actor_table = map_r.capital_actor_table
    else:
        latent_pressure_table = []
        capital_actor_table = []

    # --- 3. Scores --------------------------------------------------------
    component_lookup: Dict[str, ComponentScore] = {}
    if score is not None:
        for flat in score.component_scores:
            component_lookup[flat.code] = _flat_to_full(flat, ai_infra=ai_infra)
    # Fill any missing codes with placeholders so the final shape validates.
    for code in COMPONENT_CODES:
        if code not in component_lookup:
            component_lookup[code] = _placeholder_component(code)

    def get_score(code: str) -> ComponentScore:
        return component_lookup[code]

    # Domain I
    if score is not None:
        financial_survival_ratios = FinancialSurvivalRatios(
            net_debt_to_ebitda=score.net_debt_to_ebitda,
            interest_coverage=score.interest_coverage,
            fcf_yield=score.fcf_yield,
            nearest_debt_maturity=score.nearest_debt_maturity,
            liquidity_buffer=score.liquidity_buffer,
        )
        valuation_context = ValuationContext(
            current_multiple=score.current_multiple,
            peer_multiple_range=score.peer_multiple_range,
            analyst_coverage_skew=score.analyst_coverage_skew,
            stage_implication=score.valuation_stage_implication,
        )
    else:
        financial_survival_ratios = FinancialSurvivalRatios(
            net_debt_to_ebitda="n/a", interest_coverage="n/a",
            fcf_yield="n/a", nearest_debt_maturity="n/a",
            liquidity_buffer="n/a",
        )
        valuation_context = ValuationContext(
            current_multiple="n/a", peer_multiple_range="n/a",
            analyst_coverage_skew="n/a",
            stage_implication="SCORE call failed.",
        )

    domain_i_total = sum(
        get_score(c).weighted_contribution for c in ("1A", "1B", "1C", "1D", "1E")
    )
    domain_i = DomainI_FiveTruthLayers(
        substrate_truth_1A=get_score("1A"),
        economic_capture_truth_1B=get_score("1B"),
        financial_survival_truth_1C=get_score("1C"),
        financial_survival_ratios=financial_survival_ratios,
        valuation_entry_truth_1D=get_score("1D"),
        valuation_context=valuation_context,
        reflexive_system_truth_1E=get_score("1E"),
        domain_total=round(min(domain_i_total, DOMAIN_MAX["i"]), 2),
    )

    # Domain II (depends on SYNTHESIZE for checklists/pre-mortem/decision rule)
    if synth is not None:
        anti_hindsight = AntiHindsightChecklist(
            what_was_observable_then=synth.ah_what_was_observable_then,
            what_was_inferable_then=synth.ah_what_was_inferable_then,
            what_was_unknowable=synth.ah_what_was_unknowable,
            alternative_futures=synth.ah_alternative_futures,
            contradicting_signals=synth.ah_contradicting_signals,
            likely_blind_spots=synth.ah_likely_blind_spots,
            historical_false_positives=synth.ah_historical_false_positives,
        )
        pre_mortem = PreMortemScenarios(
            technology=PreMortemScenario(**synth.pre_mortem_technology.model_dump()),
            financing=PreMortemScenario(**synth.pre_mortem_financing.model_dump()),
            economic_capture=PreMortemScenario(**synth.pre_mortem_economic_capture.model_dump()),
            valuation=PreMortemScenario(**synth.pre_mortem_valuation.model_dump()),
            policy=PreMortemScenario(**synth.pre_mortem_policy.model_dump()),
            substitution=PreMortemScenario(**synth.pre_mortem_substitution.model_dump()),
            timing=PreMortemScenario(**synth.pre_mortem_timing.model_dump()),
            regulatory=PreMortemScenario(**synth.pre_mortem_regulatory.model_dump()),
        )
        decision_rule = DecisionRule(
            entry_conditions=synth.dr_entry_conditions,
            evidence_thresholds=synth.dr_evidence_thresholds,
            position_sizing_guidance=synth.dr_position_sizing_guidance,
            kill_conditions=synth.dr_kill_conditions,
            valuation_discipline=synth.dr_valuation_discipline,
            survivability_assumptions=synth.dr_survivability_assumptions,
            monitoring_signals=synth.dr_monitoring_signals,
        )
    else:
        anti_hindsight = AntiHindsightChecklist(
            what_was_observable_then="SYNTHESIZE call failed.",
            what_was_inferable_then="SYNTHESIZE call failed.",
            what_was_unknowable="SYNTHESIZE call failed.",
            alternative_futures=[],
            contradicting_signals=[],
            likely_blind_spots=[],
            historical_false_positives=[],
        )
        pre_mortem = PreMortemScenarios(
            technology=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            financing=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            economic_capture=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            valuation=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            policy=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            substitution=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            timing=_placeholder_pre_mortem("SYNTHESIZE call failed"),
            regulatory=_placeholder_pre_mortem("SYNTHESIZE call failed"),
        )
        decision_rule = DecisionRule(
            entry_conditions="SYNTHESIZE call failed.",
            evidence_thresholds="SYNTHESIZE call failed.",
            position_sizing_guidance="SYNTHESIZE call failed.",
            kill_conditions="SYNTHESIZE call failed.",
            valuation_discipline="SYNTHESIZE call failed.",
            survivability_assumptions="SYNTHESIZE call failed.",
            monitoring_signals=[],
        )

    primary_latent_pressure = (score.primary_latent_pressure
                               if score is not None else "n/a")
    estimated_stage = (score.estimated_stage
                       if score is not None else "Stage 0 - Ignored")

    domain_ii_total = sum(
        get_score(c).weighted_contribution for c in ("2A", "2B", "2C", "2D")
    )
    domain_ii = DomainII_EpistemicIntegrity(
        latent_pressure_stage_2A=get_score("2A"),
        primary_latent_pressure=primary_latent_pressure,
        estimated_stage=estimated_stage,
        evidence_observability_2B=get_score("2B"),
        anti_hindsight_integrity_2C=get_score("2C"),
        anti_hindsight_checklist=anti_hindsight,
        pre_mortem_discipline_2D=get_score("2D"),
        pre_mortem_scenarios=pre_mortem,
        decision_rule=decision_rule,
        domain_total=round(min(domain_ii_total, DOMAIN_MAX["ii"]), 2),
    )

    # Domain III
    domain_iii_total = sum(
        get_score(c).weighted_contribution for c in ("3A", "3B", "3C")
    )
    domain_iii = DomainIII_PhysicalRealityAnchor(
        physicalization_constraint_3A=get_score("3A"),
        primary_physical_constraint=(score.primary_physical_constraint
                                     if score else "n/a"),
        capex_to_revenue_pct=(score.capex_to_revenue_pct if score else "n/a"),
        power_and_energy_position_3B=get_score("3B"),
        disclosed_energy_agreements=(list(score.disclosed_energy_agreements)
                                     if score else []),
        strategic_scarcity_3C=get_score("3C"),
        scarcity_type=(score.scarcity_type if score else "n/a"),
        substitution_risks=(list(score.substitution_risks) if score else []),
        domain_total=round(min(domain_iii_total, DOMAIN_MAX["iii"]), 2),
    )

    # Domain IV (now includes 4C: Hyper Mobile Capital Flow Fragility)
    domain_iv_total = sum(
        get_score(c).weighted_contribution for c in ("4A", "4B", "4C")
    )
    domain_iv = DomainIV_CapitalTopology(
        capital_concentration_alignment_4A=get_score("4A"),
        largest_disclosed_holders=(list(score.largest_disclosed_holders)
                                   if score else []),
        insider_ownership_pct=(score.insider_ownership_pct if score else "n/a"),
        institutional_ownership_signal=(score.institutional_ownership_signal
                                        if score else "n/a"),
        institutional_capture_favorability_4B=get_score("4B"),
        key_regulatory_disclosures=(list(score.key_regulatory_disclosures)
                                    if score else []),
        government_revenue_pct=(score.government_revenue_pct if score else "n/a"),
        hyper_mobile_capital_flow_4C=get_score("4C"),
        capital_mobility_profile=(score.capital_mobility_profile
                                  if score else "n/a"),
        domain_total=round(min(domain_iv_total, DOMAIN_MAX["iv"]), 2),
    )

    # Domain V (now includes 5D: Cost of Capital Reappearance Sensitivity)
    domain_v_total = sum(
        get_score(c).weighted_contribution for c in ("5A", "5B", "5C", "5D")
    )
    domain_v = DomainV_FragilityProfile(
        liquidity_independence_5A=get_score("5A"),
        sovereign_and_trust_stability_5B=get_score("5B"),
        geographic_revenue_concentration=(score.geographic_revenue_concentration
                                          if score else "n/a"),
        commoditization_resistance_5C=get_score("5C"),
        gross_margin_trend_3yr=(score.gross_margin_trend_3yr
                                if score else "n/a"),
        roic_trend_3yr=(score.roic_trend_3yr if score else "n/a"),
        primary_commoditization_risk=(score.primary_commoditization_risk
                                      if score else "n/a"),
        cost_of_capital_reappearance_5D=get_score("5D"),
        rate_sensitivity_profile=(score.rate_sensitivity_profile
                                  if score else "n/a"),
        domain_total=round(min(domain_v_total, DOMAIN_MAX["v"]), 2),
    )

    # --- Kill conditions + master score (recomputed in Python) ----------
    s1A = get_score("1A").raw_score
    s1C = get_score("1C").raw_score
    s1D = get_score("1D").raw_score
    s2C = get_score("2C").raw_score
    cap_1A = s1A <= 2
    cap_1C = s1C <= 2
    cap_1D = s1D <= 1
    flag_2C = s2C <= 1
    applicable_cap = 100
    if cap_1A:
        applicable_cap = min(applicable_cap, 40)
    if cap_1C:
        applicable_cap = min(applicable_cap, 50)
    if cap_1D:
        applicable_cap = min(applicable_cap, 60)

    raw_total = round(
        domain_i.domain_total + domain_ii.domain_total
        + domain_iii.domain_total + domain_iv.domain_total
        + domain_v.domain_total,
        2,
    )
    master_score = int(round(min(raw_total, applicable_cap)))
    kill_check = KillConditionCheck(
        cap_1A_substrate_triggered=cap_1A,
        cap_1C_survival_triggered=cap_1C,
        cap_1D_valuation_triggered=cap_1D,
        integrity_flag_2C_triggered=flag_2C,
        applicable_cap=applicable_cap,
    )

    # Allocation tier and capital bucket are deterministic from
    # master_score per the framework, so compute them in Python rather
    # than asking the model. This guarantees they never disagree with
    # the Python-recomputed master score.
    allocation_tier = _tier_from_score(master_score)
    capital_bucket = _bucket_from_score(master_score)

    # --- Scenarios, falsifiers, audit, signal ranking, exec summary -----
    if synth is not None:
        scenarios = [
            ProbabilisticScenario(
                name=s.name, narrative=s.narrative,
                probability_pct=s.probability_pct,
                price_target_or_outcome=s.price_target_or_outcome,
                key_drivers=s.key_drivers,
            )
            for s in synth.probabilistic_scenarios
        ]
        key_thesis_statement = synth.key_thesis_statement
        primary_falsifiers = synth.primary_falsifiers
        gap_audit = GapSafeguardsAudit(
            gap_1_quantification=synth.gap_quantification,
            gap_2_branch_control=synth.gap_branch_control,
            gap_3_narrative_psychology=synth.gap_narrative_psychology,
            gap_4_reflexivity=synth.gap_reflexivity,
            gap_5_institutional_power=synth.gap_institutional_power,
            gap_6_substitution_systems=synth.gap_substitution_systems,
            gap_7_topology_analysis=synth.gap_topology_analysis,
            gap_8_temporal_dynamics=synth.gap_temporal_dynamics,
            gap_9_market_structure=synth.gap_market_structure,
            gap_10_civilization_hierarchy=synth.gap_civilization_hierarchy,
        )
        signal_ranking = SignalRanking(
            top_signals=synth.top_signals,
            ranking_rationale=synth.signal_ranking_rationale,
        )
        executive_summary = synth.executive_summary
    else:
        scenarios = []
        key_thesis_statement = "SYNTHESIZE call failed."
        primary_falsifiers = []
        gap_audit = GapSafeguardsAudit(
            **{f: "SYNTHESIZE call failed."
               for f in (
                   "gap_1_quantification", "gap_2_branch_control",
                   "gap_3_narrative_psychology", "gap_4_reflexivity",
                   "gap_5_institutional_power", "gap_6_substitution_systems",
                   "gap_7_topology_analysis", "gap_8_temporal_dynamics",
                   "gap_9_market_structure", "gap_10_civilization_hierarchy",
               )}
        )
        signal_ranking = SignalRanking(
            top_signals=[], ranking_rationale="SYNTHESIZE call failed.",
        )
        executive_summary = "SYNTHESIZE call failed; analysis incomplete."

    # Chunk Laws triggered comes straight from SCORE (cast Literal -> str).
    chunk_laws_list: List[str] = (
        [str(c) for c in score.chunk_laws_triggered]
        if score is not None else []
    )

    # AI infrastructure relevance: TRUE only if ORIENT flagged it AND we
    # actually have an AI infra result. If ORIENT flagged but the 5th
    # call failed, we surface the flag but leave the analysis section
    # None so the caller can see the trigger fired without seeing stale
    # synthetic content.
    ai_infra_flag = bool(
        orient is not None and orient.ai_infrastructure_relevant
    )

    # --- Assemble final ----------------------------------------------------
    result = CSPPv26AnalysisResult(
        company_name=company_name,
        ticker=ticker,
        fiscal_year=fiscal_year,
        primary_exchange=primary_exchange,
        primary_thesis=primary_thesis,
        document_completeness=doc_completeness,
        thesis_classification=thesis_classification,
        module_diagnostics=module_diagnostics,
        latent_pressure_table=latent_pressure_table,
        capital_actor_table=capital_actor_table,
        chunk_laws_triggered=chunk_laws_list,
        domain_i_five_truth_layers=domain_i,
        domain_ii_epistemic_integrity=domain_ii,
        domain_iii_physical_reality_anchor=domain_iii,
        domain_iv_capital_topology=domain_iv,
        domain_v_fragility_profile=domain_v,
        kill_condition_check=kill_check,
        raw_total=raw_total,
        master_score=master_score,
        allocation_tier=allocation_tier,
        capital_bucket=capital_bucket,
        probabilistic_scenarios=scenarios,
        key_thesis_statement=key_thesis_statement,
        primary_falsifiers=primary_falsifiers,
        gap_safeguards_audit=gap_audit,
        signal_ranking=signal_ranking,
        executive_summary=executive_summary,
        ai_infrastructure_relevant=ai_infra_flag,
        ai_infrastructure_analysis=ai_infra,
    )
    if partial:
        result.analysis_partial = True
        result.failed_call = ",".join(failed_calls or [])
    return result
