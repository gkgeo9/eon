#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSPP v2.6 — Causal Substrate Propagation Protocol Analyzer.

Applies the full CSPP v2.6 analytical framework to a single fiscal year's
10-K filing and produces a structured master score (0-100) across 15 scored
components organized into 5 domains, including kill condition checks,
allocation tier, scenario probabilities, and required disclosure tables.

Single-year workflow: uses the most recent 10-K only.

Schema design notes (Gemini structured output compatibility, 2026):
  - Field(ge=, le=) on int is supported (used by existing example workflows).
  - Literal with multiple string values is supported; single-value Literal is
    avoided because it triggers a schema validation bug.
  - Field default values are NOT used because the Gemini API rejects
    response schemas that carry Pydantic defaults.
  - Optional/Union (anyOf) is used sparingly and only where the model
    genuinely may have no value to report.
  - Nested BaseModel and List[BaseModel] are fully supported.
"""

from typing import List, Literal
from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow


# ---------------------------------------------------------------------------
# Document completeness — lets the model self-report whether it processed
# the entire 10-K or only part of it. Sits at the top of the result so it
# is easy to find in downstream code.
# ---------------------------------------------------------------------------


class DocumentCompleteness(BaseModel):
    """Model's self-assessment of whether it analyzed the complete 10-K."""

    full_doc: bool = Field(
        description=(
            "TRUE if you (the model) were able to read and analyze the ENTIRE 10-K "
            "filing that was provided in the prompt. FALSE if any portion of the "
            "filing appeared truncated, missing, unreadable, or if you had to skip "
            "sections due to length. Be honest — a FALSE here is critical metadata."
        )
    )
    sections_visible: List[str] = Field(
        description=(
            "List the major 10-K sections you could clearly see and use "
            "(e.g. 'Item 1 Business', 'Item 1A Risk Factors', 'Item 7 MD&A', "
            "'Item 7A Quantitative and Qualitative Disclosures', "
            "'Item 8 Financial Statements', 'Item 9A Controls', "
            "'Exhibits / Subsidiaries'). Use the actual item numbers from the "
            "filing."
        )
    )
    sections_missing_or_partial: List[str] = Field(
        description=(
            "List any 10-K sections that appeared missing, truncated, garbled, "
            "or only partially extractable. Empty list if everything was clean."
        )
    )
    completeness_note: str = Field(
        description=(
            "Short note (1-3 sentences) explaining your completeness assessment. "
            "If full_doc is FALSE, explain specifically what was missing and how "
            "that limits the analysis."
        )
    )


# ---------------------------------------------------------------------------
# Generic score block reused across all 15 scored components.
# ---------------------------------------------------------------------------


class ComponentScore(BaseModel):
    """A single scored CSPP component (one of the 15)."""

    code: Literal[
        "1A", "1B", "1C", "1D", "1E",
        "2A", "2B", "2C", "2D",
        "3A", "3B", "3C",
        "4A", "4B",
        "5A", "5B", "5C",
    ] = Field(description="CSPP component code from the framework")
    name: str = Field(description="Component name (e.g. 'Substrate Truth')")
    raw_score: int = Field(
        ge=0, le=10,
        description="Raw score 0-10 per the component rubric in the framework."
    )
    weight: float = Field(
        description=(
            "Weight applied to the raw score per the framework "
            "(1.0 for 1A/1B/1C; 0.5 for all others)."
        )
    )
    weighted_contribution: float = Field(
        description="raw_score * weight. Contributes to the master score."
    )
    evidence_classification: Literal[
        "Observable", "Inductable", "Weakly inferable", "Hindsight only", "Unknown"
    ] = Field(
        description=(
            "Per the Real Time Evidence Standard, classify the strength of "
            "evidence supporting this component score."
        )
    )
    reasoning: str = Field(
        description=(
            "Explicit reasoning for the score, citing specific disclosures from "
            "the 10-K (item, section, or page-level reference where possible). "
            "2-6 sentences."
        )
    )
    supporting_evidence: List[str] = Field(
        description=(
            "Bulleted list of specific, verifiable evidence items from the 10-K "
            "that anchor this score (financial figures, contract disclosures, "
            "risk factor language, segment data, etc.). Distinguish observable "
            "facts from inferences in the bullet text."
        )
    )
    kill_condition_triggered: bool = Field(
        description=(
            "TRUE only for components 1A (raw<=2), 1C (raw<=2), 1D (raw<=1), "
            "or 2C (raw<=1) when the threshold is crossed. FALSE otherwise, "
            "including for components that have no kill condition."
        )
    )


# ---------------------------------------------------------------------------
# Domain I — Five Truth Layers (40 pts)
# Each layer carries extra structured fields where the rubric calls for them.
# ---------------------------------------------------------------------------


class FinancialSurvivalRatios(BaseModel):
    """Disclosed balance-sheet ratios that drive the 1C score."""

    net_debt_to_ebitda: str = Field(
        description="Net debt / EBITDA. Use 'n/a' if not disclosed/derivable."
    )
    interest_coverage: str = Field(
        description="EBIT / interest expense. Use 'n/a' if not derivable."
    )
    fcf_yield: str = Field(
        description=(
            "Free cash flow yield (FCF / market cap or FCF / enterprise value, "
            "noting which). Use 'n/a' if market cap is unknown."
        )
    )
    nearest_debt_maturity: str = Field(
        description="Year and approximate size of the nearest major debt maturity."
    )
    liquidity_buffer: str = Field(
        description="Cash + undrawn revolver disclosed in the filing."
    )


class ValuationContext(BaseModel):
    """Market context used to score 1D (Valuation Entry Truth)."""

    current_multiple: str = Field(
        description=(
            "Best single multiple for this company "
            "(e.g. 'EV/EBITDA 14x', 'P/E 28x', 'P/S 6x'). "
            "Use 'unknown — outside 10-K' if market data is unavailable."
        )
    )
    peer_multiple_range: str = Field(
        description=(
            "Peer multiple range for context, or 'unknown — outside 10-K' if "
            "no reliable peer set is available without additional data."
        )
    )
    analyst_coverage_skew: str = Field(
        description=(
            "Qualitative skew of analyst coverage "
            "(e.g. 'mostly bullish', 'split', 'hostile'). "
            "Use 'unknown — outside 10-K' if not inferable."
        )
    )


class DomainI_FiveTruthLayers(BaseModel):
    """Domain I — Five Truth Layers (max 40 weighted pts)."""

    substrate_truth_1A: ComponentScore = Field(
        description="1A — Substrate Truth (weight 1.0). KILL: raw<=2 caps master at 40."
    )
    economic_capture_truth_1B: ComponentScore = Field(
        description="1B — Economic Capture Truth (weight 1.0)."
    )
    financial_survival_truth_1C: ComponentScore = Field(
        description="1C — Financial Survival Truth (weight 1.0). KILL: raw<=2 caps master at 50."
    )
    financial_survival_ratios: FinancialSurvivalRatios = Field(
        description="Disclosed ratios that justify the 1C score."
    )
    valuation_entry_truth_1D: ComponentScore = Field(
        description="1D — Valuation Entry Truth (weight 0.5). KILL: raw<=1 caps master at 60."
    )
    valuation_context: ValuationContext = Field(
        description="Market context used for 1D scoring."
    )
    reflexive_system_truth_1E: ComponentScore = Field(
        description="1E — Reflexive System Truth (weight 0.5)."
    )
    domain_total: float = Field(
        ge=0, le=40,
        description="Sum of weighted contributions in Domain I (max 40)."
    )


# ---------------------------------------------------------------------------
# Domain II — Epistemic Integrity (20 pts)
# Includes the anti-hindsight discipline, pre-mortem, false positive library.
# ---------------------------------------------------------------------------


class AntiHindsightChecklist(BaseModel):
    """Required answers to the seven anti-hindsight discipline questions."""

    what_was_observable_then: str = Field(
        description="What was directly observable at the time of this 10-K?"
    )
    what_was_inferable_then: str = Field(
        description="What was reasonably inferable but not directly observable?"
    )
    what_was_unknowable: str = Field(
        description="What was fundamentally unknowable at the time of this 10-K?"
    )
    alternative_futures: List[str] = Field(
        description="At least 2 plausible alternative futures, not just the base thesis."
    )
    contradicting_signals: List[str] = Field(
        description="Specific disclosures or data points in the filing that contradict the thesis."
    )
    likely_blind_spots: List[str] = Field(
        description="What this protocol applied to this filing is likely to miss."
    )
    historical_false_positives: List[str] = Field(
        description=(
            "Historical analogues from the False Positive Library (clean tech 2007, "
            "3D printing, SPACs, metaverse, commodity supercycle, etc.) that resemble "
            "this thesis, with a short note on why this case is or is not different."
        )
    )


class PreMortemScenario(BaseModel):
    """One of the eight failure-category scenarios required for full pre-mortem credit."""

    category: Literal[
        "Technology", "Financing", "Economic capture", "Valuation",
        "Policy", "Substitution", "Timing", "Regulatory",
    ] = Field(description="Failure category from the Pre-Mortem Module.")
    failure_mode: str = Field(
        description="How the thesis fails in this category, given the 10-K disclosures."
    )
    probability_pct: int = Field(
        ge=0, le=100,
        description="Estimated probability (0-100) of this failure mode materializing."
    )
    early_warning_signals: List[str] = Field(
        description="Concrete signals that would indicate this failure is unfolding."
    )
    kill_condition: str = Field(
        description=(
            "Specific, measurable kill condition tied to this failure mode "
            "(e.g. 'gross margin falls below 35% for two consecutive quarters')."
        )
    )


class DecisionRule(BaseModel):
    """Decision Rule Module output — required for Pre-Mortem score >7."""

    entry_conditions: str = Field(description="What price / evidence triggers entry?")
    evidence_thresholds: str = Field(description="What evidence is required to scale a position?")
    position_sizing_guidance: str = Field(
        description="How large should this position be relative to survivability assumptions?"
    )
    monitoring_signals: List[str] = Field(
        description="Measurable signals to monitor on an ongoing basis."
    )
    valuation_discipline: str = Field(
        description="Maximum multiple or valuation level at which to start trimming."
    )
    survivability_assumptions: str = Field(
        description="What the position assumes about the company surviving stress."
    )


class DomainII_EpistemicIntegrity(BaseModel):
    """Domain II — Epistemic Integrity (max 20 weighted pts)."""

    latent_pressure_stage_2A: ComponentScore = Field(
        description="2A — Latent Pressure Stage Positioning (weight 0.5)."
    )
    primary_latent_pressure: str = Field(
        description="The single most important latent civilization pressure for this thesis."
    )
    estimated_stage: Literal[
        "Stage 0 - Ignored",
        "Stage 1 - Niche",
        "Stage 2 - Early Capital",
        "Stage 3 - Rerating",
        "Stage 4 - Consensus",
        "Stage 5 - Crowded",
    ] = Field(description="Current recognition stage of the primary latent pressure.")
    evidence_observability_2B: ComponentScore = Field(
        description="2B — Evidence Observability (weight 0.5)."
    )
    anti_hindsight_integrity_2C: ComponentScore = Field(
        description="2C — Anti-Hindsight Integrity (weight 0.5). INTEGRITY FLAG: raw<=1."
    )
    anti_hindsight_checklist: AntiHindsightChecklist = Field(
        description="All seven anti-hindsight questions answered (required for 2C > 6)."
    )
    pre_mortem_discipline_2D: ComponentScore = Field(
        description="2D — Pre-Mortem Discipline (weight 0.5)."
    )
    pre_mortem_scenarios: List[PreMortemScenario] = Field(
        description=(
            "Pre-mortem across the eight failure categories. To score 2D above 7, "
            "all eight categories must be represented."
        )
    )
    decision_rule: DecisionRule = Field(
        description="Decision Rule Module output (required for 2D > 7)."
    )
    domain_total: float = Field(
        ge=0, le=20,
        description="Sum of weighted contributions in Domain II (max 20)."
    )


# ---------------------------------------------------------------------------
# Domain III — Physical Reality Anchor (15 pts)
# ---------------------------------------------------------------------------


class DomainIII_PhysicalRealityAnchor(BaseModel):
    """Domain III — Physical Reality Anchor (max 15 weighted pts)."""

    physicalization_constraint_3A: ComponentScore = Field(
        description="3A — Physicalization Constraint Depth (weight 0.5)."
    )
    primary_physical_constraint: str = Field(
        description=(
            "The dominant physical bottleneck the company sits at or depends on "
            "(e.g. 'leading-edge HBM packaging capacity', 'grid interconnect "
            "queue in PJM', 'lithium hydroxide supply'). 'None — purely digital' "
            "if no binding constraint exists."
        )
    )
    capex_to_revenue_pct: str = Field(
        description="Capex as % of revenue (latest fiscal year), or 'n/a'."
    )
    power_and_energy_position_3B: ComponentScore = Field(
        description="3B — Power and Energy Position (weight 0.5)."
    )
    disclosed_energy_agreements: List[str] = Field(
        description=(
            "Specific PPAs, captive generation, hydro / nuclear / grid agreements "
            "disclosed in the filing. Empty list if none disclosed."
        )
    )
    strategic_scarcity_3C: ComponentScore = Field(
        description="3C — Strategic Scarcity Quality (weight 0.5)."
    )
    scarcity_type: str = Field(
        description=(
            "Type of scarcity the company controls or benefits from "
            "(geopolitical, regulatory, physical, technological), or "
            "'No structural scarcity'."
        )
    )
    substitution_risks: List[str] = Field(
        description="Disclosed or evident substitution threats to that scarcity."
    )
    domain_total: float = Field(
        ge=0, le=15,
        description="Sum of weighted contributions in Domain III (max 15)."
    )


# ---------------------------------------------------------------------------
# Domain IV — Capital Topology (10 pts)
# ---------------------------------------------------------------------------


class DomainIV_CapitalTopology(BaseModel):
    """Domain IV — Capital Topology (max 10 weighted pts)."""

    capital_concentration_alignment_4A: ComponentScore = Field(
        description="4A — Capital Concentration Alignment (weight 0.5)."
    )
    largest_disclosed_holders: List[str] = Field(
        description=(
            "Largest beneficial owners disclosed in the filing's proxy / cover-page "
            "/ schedule 13G references. May be limited if only proxy carries this."
        )
    )
    insider_ownership_pct: str = Field(
        description="Aggregate insider/officer/director ownership %, or 'n/a'."
    )
    institutional_ownership_signal: str = Field(
        description=(
            "Qualitative signal of institutional positioning if disclosed or "
            "reasonably inferable; otherwise 'unknown — outside 10-K'."
        )
    )
    institutional_capture_favorability_4B: ComponentScore = Field(
        description="4B — Institutional Capture Favorability (weight 0.5)."
    )
    key_regulatory_disclosures: List[str] = Field(
        description="Specific regulatory items from Item 1 / Item 1A that drive the 4B score."
    )
    government_revenue_pct: str = Field(
        description="% of revenue from government counterparties, or 'n/a'."
    )
    domain_total: float = Field(
        ge=0, le=10,
        description="Sum of weighted contributions in Domain IV (max 10)."
    )


# ---------------------------------------------------------------------------
# Domain V — Fragility Profile (15 pts)
# ---------------------------------------------------------------------------


class DomainV_FragilityProfile(BaseModel):
    """Domain V — Fragility Profile (max 15 weighted pts)."""

    liquidity_independence_5A: ComponentScore = Field(
        description="5A — Liquidity Independence (weight 0.5)."
    )
    sovereign_and_trust_stability_5B: ComponentScore = Field(
        description="5B — Sovereign and Trust Stability (weight 0.5)."
    )
    geographic_revenue_concentration: str = Field(
        description=(
            "Concentration of revenue by jurisdiction "
            "(e.g. 'US 78%, EMEA 14%, APAC 8%')."
        )
    )
    commoditization_resistance_5C: ComponentScore = Field(
        description="5C — Commoditization Resistance (weight 0.5)."
    )
    gross_margin_trend_3yr: str = Field(
        description="Gross margin trajectory over the last 3 disclosed fiscal years."
    )
    roic_trend_3yr: str = Field(
        description="Return on invested capital trajectory over the last 3 disclosed fiscal years."
    )
    primary_commoditization_risk: str = Field(
        description="The single most credible commoditization or substitution risk."
    )
    domain_total: float = Field(
        ge=0, le=15,
        description="Sum of weighted contributions in Domain V (max 15)."
    )


# ---------------------------------------------------------------------------
# Kill condition check, scenarios, required tables, final result.
# ---------------------------------------------------------------------------


class KillConditionCheck(BaseModel):
    """Explicit kill condition audit before computing the master score."""

    cap_1A_substrate_triggered: bool = Field(
        description="TRUE if Score 1A raw <= 2 (master capped at 40)."
    )
    cap_1C_survival_triggered: bool = Field(
        description="TRUE if Score 1C raw <= 2 (master capped at 50)."
    )
    cap_1D_valuation_triggered: bool = Field(
        description="TRUE if Score 1D raw <= 1 (master capped at 60)."
    )
    integrity_flag_2C_triggered: bool = Field(
        description=(
            "TRUE if Score 2C raw <= 1. Does NOT cap the master score, but marks "
            "the entire analysis as structurally unreliable."
        )
    )
    applicable_cap: int = Field(
        ge=0, le=100,
        description=(
            "Lowest cap triggered (40 / 50 / 60), or 100 if no cap applies."
        )
    )


class ProbabilisticScenario(BaseModel):
    """One leg of the bull / base / bear scenario set."""

    name: Literal["Bull", "Base", "Bear"] = Field(description="Scenario label.")
    narrative: str = Field(
        description="What has to be true for this scenario to play out."
    )
    probability_pct: int = Field(
        ge=0, le=100,
        description="Estimated probability for this scenario (the three must sum to ~100)."
    )
    price_target_or_outcome: str = Field(
        description=(
            "Qualitative or quantitative outcome description "
            "(e.g. 'fair value $145, +30% from current', or 'business stagnates, "
            "multiple compresses to 12x')."
        )
    )


class LatentPressureRow(BaseModel):
    """One row of the required Latent Pressure Table."""

    pressure: str = Field(description="The latent pressure (e.g. 'grid saturation').")
    observable: bool = Field(description="Is the pressure directly observable today?")
    inductable: bool = Field(description="Is it reasonably inferable?")
    activation_threshold: str = Field(
        description="What level / event would activate it financially?"
    )
    financial_expression: str = Field(
        description="How would it first show up in this company's results?"
    )
    false_positive_risk: str = Field(
        description="Closest historical false positive and why this differs."
    )


class CapitalActorRow(BaseModel):
    """One row of the required Capital Actor Table."""

    actor: str = Field(
        description="Capital actor (e.g. 'passive index funds', 'sovereign wealth funds')."
    )
    incentive: str = Field(description="What motivates the actor.")
    flow_direction: Literal["Inflow", "Outflow", "Neutral", "Mixed"] = Field(
        description="Net direction of the actor's flow into this company / sector."
    )
    assets_affected: str = Field(description="What assets the flow most affects.")
    political_influence: str = Field(description="The actor's political/regulatory leverage.")
    fragility_created: str = Field(
        description="What fragility the actor's flow introduces (if any)."
    )


# ---------------------------------------------------------------------------
# Top-level result.
# ---------------------------------------------------------------------------


class CSPPv26AnalysisResult(BaseModel):
    """Top-level CSPP v2.6 analysis result for a single fiscal year 10-K."""

    # --- Identification ---
    company_name: str = Field(description="Full legal company name from the 10-K cover.")
    ticker: str = Field(description="Ticker symbol passed into the workflow.")
    fiscal_year: int = Field(description="Fiscal year of the 10-K analyzed.")
    primary_exchange: str = Field(
        description="Primary listing exchange (e.g. 'NASDAQ', 'NYSE')."
    )
    primary_thesis: str = Field(
        description=(
            "One-paragraph statement of the core CSPP thesis being scored. "
            "Must be written probabilistically, not as certainty."
        )
    )

    # --- Document completeness self-report ---
    document_completeness: DocumentCompleteness = Field(
        description="Model's self-report on whether it read the full 10-K."
    )

    # --- The five scoring domains ---
    domain_i_five_truth_layers: DomainI_FiveTruthLayers = Field(
        description="Domain I — Five Truth Layers (40 pts)."
    )
    domain_ii_epistemic_integrity: DomainII_EpistemicIntegrity = Field(
        description="Domain II — Epistemic Integrity (20 pts)."
    )
    domain_iii_physical_reality_anchor: DomainIII_PhysicalRealityAnchor = Field(
        description="Domain III — Physical Reality Anchor (15 pts)."
    )
    domain_iv_capital_topology: DomainIV_CapitalTopology = Field(
        description="Domain IV — Capital Topology (10 pts)."
    )
    domain_v_fragility_profile: DomainV_FragilityProfile = Field(
        description="Domain V — Fragility Profile (15 pts)."
    )

    # --- Kill conditions, master score, allocation ---
    kill_condition_check: KillConditionCheck = Field(
        description="Audit of all four kill / integrity conditions before scoring."
    )
    raw_total: float = Field(
        ge=0, le=100,
        description="Uncapped sum of all five domain totals (max 100)."
    )
    master_score: int = Field(
        ge=0, le=100,
        description=(
            "Final master score = min(raw_total, applicable_cap), rounded to "
            "nearest integer."
        )
    )
    allocation_tier: Literal[
        "Exceptional (85-100)",
        "High conviction (70-84)",
        "Moderate conviction (55-69)",
        "Low conviction (40-54)",
        "Speculative (25-39)",
        "Reject (0-24)",
    ] = Field(description="Tier mapped from the master score.")
    capital_bucket: Literal[
        "Core capital",
        "Defensive growth",
        "Real asset ballast",
        "Transition capital",
        "Optionality capital",
        "Watchlist capital",
        "Avoid capital",
    ] = Field(description="Recommended Barbell Allocation bucket.")

    # --- Scenarios ---
    probabilistic_scenarios: List[ProbabilisticScenario] = Field(
        description="Exactly three scenarios — Bull, Base, Bear — with probabilities summing to ~100."
    )

    # --- Thesis statement and falsifiers ---
    key_thesis_statement: str = Field(
        description=(
            "One-paragraph core causal thesis that this score reflects. MUST NOT be "
            "written as certainty. MUST distinguish observable, inductable, and "
            "unknowable elements."
        )
    )
    primary_falsifiers: List[str] = Field(
        description=(
            "Exactly 3 specific, future-observable signals that would materially "
            "reduce this score if they appeared in a future 10-K or market data."
        )
    )

    # --- Required tables ---
    latent_pressure_table: List[LatentPressureRow] = Field(
        description="Mandatory Latent Pressure Table — at least 3 rows."
    )
    capital_actor_table: List[CapitalActorRow] = Field(
        description="Mandatory Capital Actor Table — at least 2 rows."
    )

    # --- Final analyst summary ---
    executive_summary: str = Field(
        description=(
            "Final 4-6 sentence executive summary: master score, tier, capital "
            "bucket, any kill condition or integrity flag, and the single most "
            "important reason a CSPP allocator would or would not act."
        )
    )


# ---------------------------------------------------------------------------
# Workflow class.
# ---------------------------------------------------------------------------


class CSPPv26Analyzer(CustomWorkflow):
    """CSPP v2.6 single-year 10-K analyzer.

    Applies the full Causal Substrate Propagation Protocol v2.6 framework to
    the most recent fiscal year of a company's 10-K and produces a 0-100
    master score with kill condition checks, allocation tier, scenarios, and
    the required disclosure tables.
    """

    name = "CSPP v2.6 — Causal Substrate Propagation"
    description = (
        "Apply the Causal Substrate Propagation Protocol v2.6 to one fiscal "
        "year of a 10-K. Produces 15 component scores across 5 domains, kill "
        "condition checks, scenarios, and a 0-100 master score."
    )
    icon = "🧭"
    min_years = 1
    max_years = 1  # Single-year framework — most recent 10-K only.
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        return """
You are applying the CSPP v2.6 (Causal Substrate Propagation Protocol)
analytical framework to {ticker} for fiscal year {year}, based ONLY on the
10-K filing provided at the end of this prompt.

CSPP v2.6 is a first-principles causal framework. It exists for real-time
causal inference under uncertainty, NOT for retrospective narrative
construction. Every conclusion you produce must remain probabilistic and
falsifiable.

============================================================================
SCORING ARCHITECTURE (100-point master score)
============================================================================

Domain I    Five Truth Layers            40 pts
Domain II   Epistemic Integrity          20 pts
Domain III  Physical Reality Anchor      15 pts
Domain IV   Capital Topology             10 pts
Domain V    Fragility Profile            15 pts

There are 15 scored components. Each is scored 0-10 raw, then multiplied by
its weight (1.0 for 1A/1B/1C; 0.5 for everything else).

KILL CONDITIONS (apply BEFORE finalizing the master score):
  - 1A Substrate Truth     raw <= 2  -> master capped at 40
  - 1C Financial Survival  raw <= 2  -> master capped at 50
  - 1D Valuation Entry     raw <= 1  -> master capped at 60
  - 2C Anti-Hindsight      raw <= 1  -> INTEGRITY FLAG (no cap, but analysis
                                       is marked structurally unreliable)

Final master_score = round(min(raw_total, applicable_cap)).

Allocation tiers:
  85-100  Exceptional          Flagship allocation
  70-84   High conviction      Meaningful position
  55-69   Moderate conviction  Partial or transition capital
  40-54   Low conviction       Watchlist or optionality only
  25-39   Speculative          Avoid or micro-position only
  0-24    Reject               Short candidate or hard pass

============================================================================
DOMAIN I — FIVE TRUTH LAYERS (40 pts)
============================================================================

1A SUBSTRATE TRUTH (weight 1.0). Is the physical or social transformation
   this company operates within actually real and measurable from disclosed
   data? Score 0 = pure narrative; 10 = irreversible, fully quantified
   transformation provable in the filing. KILL: raw <= 2 caps master at 40.

1B ECONOMIC CAPTURE TRUTH (weight 1.0). Can this company durably capture
   value from the transformation? Use disclosed gross margins, operating
   margins, pricing trends, customer concentration, and competitive moat
   disclosures. 0 = commodity / zero rent; 10 = near-monopolistic capture.

1C FINANCIAL SURVIVAL TRUTH (weight 1.0). Can this company survive a
   severe adverse financing environment? Evaluate net debt / EBITDA,
   interest coverage, free cash flow, debt maturity profile, and disclosed
   liquidity. 0 = insolvency in mild stress; 10 = fortress / anti-fragile.
   KILL: raw <= 2 caps master at 50. Populate financial_survival_ratios
   with the actual numbers from the filing.

1D VALUATION ENTRY TRUTH (weight 0.5). High score = thesis undercapitalized
   (favorable entry). Low score = thesis already crowded. If you do NOT
   have reliable market data beyond the 10-K, score conservatively
   (typically 4-6) and say so explicitly in your reasoning. KILL: raw <= 1
   caps master at 60.

1E REFLEXIVE SYSTEM TRUTH (weight 0.5). Will capital flows into this
   sector reshape reality for or against the thesis? 0 = destructive
   reflexivity (overcapacity already forming); 10 = constructive feedback
   loop accelerating the transformation.

============================================================================
DOMAIN II — EPISTEMIC INTEGRITY (20 pts)
============================================================================

2A LATENT PRESSURE STAGE POSITIONING (weight 0.5). Where in the recognition
   cycle is the primary latent pressure driving the thesis?
     Stage 0 Ignored / Stage 1 Niche / Stage 2 Early capital /
     Stage 3 Rerating / Stage 4 Consensus / Stage 5 Crowded.
   High score = early stage. Low score = crowded.

2B EVIDENCE OBSERVABILITY (weight 0.5). What proportion of your claims
   about this company are directly observable in this 10-K versus inferred?

2C ANTI-HINDSIGHT INTEGRITY (weight 0.5). Does this analysis resist
   retrospective narrative construction? You MUST answer all seven
   anti-hindsight questions in anti_hindsight_checklist:
     1. What was observable then?
     2. What was inferable then?
     3. What was unknowable?
     4. What alternative futures existed?
     5. What contradicted the thesis?
     6. What is this protocol likely to miss?
     7. Which historical false positives resemble this case, and why is it
        different (or not)?
   INTEGRITY FLAG: raw <= 1 marks the entire analysis structurally
   unreliable.

2D PRE-MORTEM DISCIPLINE (weight 0.5). Have all eight failure categories
   been modeled? To score above 6, kill conditions and monitoring signals
   must be specific. To score above 7, the Decision Rule Module must be
   completed. Populate pre_mortem_scenarios with at least one entry per
   relevant category (target all eight: Technology, Financing, Economic
   capture, Valuation, Policy, Substitution, Timing, Regulatory).

============================================================================
DOMAIN III — PHYSICAL REALITY ANCHOR (15 pts)
============================================================================

3A PHYSICALIZATION CONSTRAINT DEPTH (weight 0.5). How tightly is the
   company's capability constrained by physical bottlenecks (compute,
   power, materials, geography, etc.)? Score 0 for purely digital with no
   physical collision; 10 for hard physical ceilings owned by the company.

3B POWER AND ENERGY POSITION (weight 0.5). Does the company control or
   uniquely benefit from critical power / energy constraints? Use
   disclosed PPAs, captive generation, geographic positioning, and energy
   security disclosures.

3C STRATEGIC SCARCITY QUALITY (weight 0.5). How durable and monetizable
   is the underlying scarcity the company controls or benefits from?
   Consider substitution risk, political pricing risk, and contract
   structures.

============================================================================
DOMAIN IV — CAPITAL TOPOLOGY (10 pts)
============================================================================

4A CAPITAL CONCENTRATION ALIGNMENT (weight 0.5). Is large, concentrated,
   politically influential capital aligned with the thesis? Use disclosed
   beneficial ownership, insider ownership, and any institutional holder
   data present in the filing. If real 13F data is unavailable, say so.

4B INSTITUTIONAL CAPTURE FAVORABILITY (weight 0.5). Does the regulatory
   and political environment protect the company? Use Item 1A risk
   factors, disclosed government contracts, lobbying disclosures, and
   sector regulation context.

============================================================================
DOMAIN V — FRAGILITY PROFILE (15 pts)
============================================================================

5A LIQUIDITY INDEPENDENCE (weight 0.5). How independent is the business
   model from easy money? Use FCF yield, debt maturity, rate sensitivity
   disclosures, and insider selling if visible.

5B SOVEREIGN AND TRUST STABILITY (weight 0.5). How exposed is the company
   to sovereign debt fragility or trust breakdown in its primary
   operating jurisdictions? Use geographic revenue concentration and
   government counterparty disclosures.

5C COMMODITIZATION RESISTANCE (weight 0.5). How resistant is the company
   to value destruction from competitive capex spending or technological
   commoditization? Use 3-year gross margin and ROIC trends and disclosed
   competitive landscape.

============================================================================
EVIDENCE STANDARD (mandatory for every component)
============================================================================

Every component score must include:
  - reasoning: explicit, citing specific 10-K disclosures
  - supporting_evidence: list of verifiable evidence items
  - evidence_classification: one of
        Observable, Inductable, Weakly inferable, Hindsight only, Unknown

Be HONEST about what the 10-K does and does not show. If a component
requires data outside the 10-K (e.g. current multiple for 1D, 13F data for
4A) and you do not have it, say so explicitly and score conservatively.

============================================================================
DOCUMENT COMPLETENESS (CRITICAL METADATA)
============================================================================

At the top of your output, set document_completeness.full_doc to TRUE only
if you were able to read and use the ENTIRE 10-K provided below. If any
portion appeared truncated, missing, garbled, or unreadable, set it to
FALSE and list the missing or partial sections explicitly. This metadata
will be used by downstream systems to decide whether to trust the analysis.

============================================================================
REQUIRED TABLES
============================================================================

You MUST populate:
  - latent_pressure_table  (>= 3 rows)
  - capital_actor_table    (>= 2 rows)
  - probabilistic_scenarios (exactly 3 rows: Bull, Base, Bear; probabilities sum to ~100)
  - primary_falsifiers     (exactly 3 specific, future-observable signals)

============================================================================
SCORE ARITHMETIC (do this carefully)
============================================================================

For each domain, set domain_total = sum of weighted_contribution across its
components. Then:

  raw_total = sum of all five domain_totals

  applicable_cap = min of {{40 if 1A<=2, 50 if 1C<=2, 60 if 1D<=1, 100 otherwise}}

  master_score = round(min(raw_total, applicable_cap))

The kill_condition_check object must reflect the exact boolean state of
each kill condition and the applicable_cap actually used.

============================================================================
TONE
============================================================================

Write probabilistically. Avoid inevitability language. When the 10-K
genuinely supports a strong claim, say so with the evidence. When it does
not, say so. The framework is designed to surface what you do not know as
clearly as what you do.
"""

    @property
    def schema(self):
        return CSPPv26AnalysisResult
