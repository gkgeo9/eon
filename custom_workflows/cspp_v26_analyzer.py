#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSPP v2.6 — Causal Substrate Propagation Protocol Analyzer.

============================================================================
WHAT THIS WORKFLOW DOES
============================================================================

Applies the full Causal Substrate Propagation Protocol v2.6 framework
to a single fiscal year of a 10-K filing and produces a structured,
auditable master score (0-100) with allocation tier and capital bucket.

The framework is a first-principles causal inference protocol designed for
real-time analysis under uncertainty. It is explicitly NOT a hindsight
narrative generator. Every output is required to be probabilistic and
falsifiable.

Single year only (min_years = max_years = 1) — analysis runs on the most
recent 10-K, since the framework's stage-positioning and reflexivity
analysis is keyed to a point-in-time disclosure.

============================================================================
FRAMEWORK MODULE COVERAGE MAP
============================================================================

This map tells an auditor where each module of the framework is implemented
in this file. Modules marked "scored" produce a 0-10 raw score that
contributes to the 100-pt master score. Modules marked "diagnostic" do not
score directly but inform one or more scored components per the framework's
"Scoring note" annotations.

DOMAIN I — Five Truth Layers (40 weighted pts)
  1A Substrate Truth ............... DomainI.substrate_truth_1A          [scored, w=1.0, KILL]
  1B Economic Capture Truth ........ DomainI.economic_capture_truth_1B   [scored, w=1.0]
  1C Financial Survival Truth ...... DomainI.financial_survival_truth_1C [scored, w=1.0, KILL]
                                     DomainI.financial_survival_ratios   [supporting numbers]
  1D Valuation Entry Truth ......... DomainI.valuation_entry_truth_1D    [scored, w=0.5, KILL]
                                     DomainI.valuation_context           [supporting numbers]
  1E Reflexive System Truth ........ DomainI.reflexive_system_truth_1E   [scored, w=0.5]

DOMAIN II — Epistemic Integrity (20 weighted pts)
  2A Latent Pressure Stage ......... DomainII.latent_pressure_stage_2A   [scored, w=0.5]
  2B Evidence Observability ........ DomainII.evidence_observability_2B  [scored, w=0.5]
  2C Anti-Hindsight Integrity ...... DomainII.anti_hindsight_integrity_2C[scored, w=0.5, INTEG FLAG]
                                     DomainII.anti_hindsight_checklist   [7 mandatory questions]
  2D Pre-Mortem Discipline ......... DomainII.pre_mortem_discipline_2D   [scored, w=0.5]
                                     DomainII.pre_mortem_scenarios       [8 required categories]
                                     DomainII.decision_rule              [7 required fields]

DOMAIN III — Physical Reality Anchor (15 weighted pts)
  3A Physicalization Constraint .... DomainIII.physicalization_constraint_3A [scored, w=0.5]
  3B Power and Energy Position ..... DomainIII.power_and_energy_position_3B  [scored, w=0.5]
  3C Strategic Scarcity Quality .... DomainIII.strategic_scarcity_3C         [scored, w=0.5]

DOMAIN IV — Capital Topology (10 weighted pts)
  4A Capital Concentration ......... DomainIV.capital_concentration_alignment_4A    [scored, w=0.5]
  4B Institutional Capture ......... DomainIV.institutional_capture_favorability_4B [scored, w=0.5]

DOMAIN V — Fragility Profile (15 weighted pts)
  5A Liquidity Independence ........ DomainV.liquidity_independence_5A          [scored, w=0.5]
  5B Sovereign + Trust Stability ... DomainV.sovereign_and_trust_stability_5B   [scored, w=0.5]
  5C Commoditization Resistance .... DomainV.commoditization_resistance_5C      [scored, w=0.5]

UNSCORED MODULES (informational, drive scoring quality)
  Three Clocks Module .............. ModuleDiagnostics.three_clocks
  Bottleneck Inflation ............. ModuleDiagnostics.bottleneck_inflation_note
  Continuity Infrastructure ........ ModuleDiagnostics.continuity_infrastructure_note
  Capex Arms Race .................. ModuleDiagnostics.capex_arms_race_note
  Asset Holder Policy Bias ......... ModuleDiagnostics.asset_holder_policy_bias_note
  Private Market Opacity ........... ModuleDiagnostics.private_market_opacity_note
  Sovereign Industrial Compute ..... ModuleDiagnostics.sovereign_industrial_compute_note
  Jurisdictional Arbitrage ......... ModuleDiagnostics.jurisdictional_arbitrage_note
  Trust Asset Failure .............. ModuleDiagnostics.trust_asset_failure_note
  Energy Security .................. ModuleDiagnostics.energy_security_note
  Latent Civilization Pressures .... CSPPv26AnalysisResult.latent_pressure_table  (8-question test)
  Capital Topology actors .......... CSPPv26AnalysisResult.capital_actor_table
  Market Visibility Lag (stage) .... DomainII.estimated_stage
  False Positive Library ........... AntiHindsightChecklist.historical_false_positives
  Alternative Futures Module ....... AntiHindsightChecklist.alternative_futures
  Probabilistic Inference Module ... CSPPv26AnalysisResult.probabilistic_scenarios
  Barbell Allocation ............... CSPPv26AnalysisResult.capital_bucket
  Gap Safeguards (10 layers) ....... CSPPv26AnalysisResult.gap_safeguards_audit
  Signal Ranking Module ............ CSPPv26AnalysisResult.signal_ranking
  Dual Track / Thesis Typology ..... CSPPv26AnalysisResult.thesis_classification
  Humility Principle ............... enforced via prompt + key_thesis_statement guard

KILL CONDITIONS (applied AFTER raw scoring, override master score)
  1A raw <= 2  -> master capped at 40
  1C raw <= 2  -> master capped at 50
  1D raw <= 1  -> master capped at 60
  2C raw <= 1  -> INTEGRITY FLAG (no cap, but analysis marked unreliable)

============================================================================
GEMINI STRUCTURED-OUTPUT COMPATIBILITY NOTES (as of 2026)
============================================================================

The schema in this file is designed to round-trip cleanly through the
google-genai SDK's response_schema path. Specifically:

  - Field(ge=, le=) on int is supported (existing example workflows in
    this repo rely on the same pattern).
  - Literal with multiple string values is supported. Literal with a
    SINGLE value triggers a known schema-validation bug
    (googleapis/python-genai issue #264) and is avoided.
  - Field default values are NOT used anywhere — the Gemini API rejects
    response schemas that carry Pydantic defaults
    (googleapis/python-genai issue #699).
  - Optional / Union (anyOf) is avoided where possible. Where a value may
    not exist, the model is instructed to emit "n/a" or
    "unknown — outside 10-K" instead of null.
  - Nested BaseModel and List[BaseModel] are fully supported.
  - Numeric range constraints (min_length / max_length / min_items /
    max_items) are unreliable, so cardinality requirements are enforced
    in the prompt rather than the schema.
  - Gemini 2.5+ preserves field declaration order in the output, so the
    field order in CSPPv26AnalysisResult below is meaningful — it drives
    the analytic flow (orient -> diagnose -> score -> conclude).
"""

from typing import List, Literal
from pydantic import BaseModel, Field

from custom_workflows.base import CustomWorkflow


# ===========================================================================
# SECTION 1 — Document completeness self-report
# ---------------------------------------------------------------------------
# Surfaced at the top of the result so downstream code can quickly decide
# whether to trust the analysis. If the model could not read the entire
# 10-K (truncation, garbled PDF extraction, missing exhibits) the master
# score should be treated as preliminary.
# ===========================================================================


class DocumentCompleteness(BaseModel):
    """Model's self-assessment of whether it analyzed the complete 10-K.

    NOTE: This is metadata for the consumer of the analysis, not a CSPP
    framework module. It exists because PDF extraction can truncate or
    corrupt sections of a 10-K, and the framework's evidentiary standard
    becomes unreliable when the source document is incomplete.
    """

    full_doc: bool = Field(
        description=(
            "TRUE if you (the model) were able to read and analyze the ENTIRE "
            "10-K filing provided in the prompt. FALSE if any portion of the "
            "filing appeared truncated, missing, unreadable, or had to be "
            "skipped due to length. Be honest — a FALSE here is critical "
            "metadata that tells downstream systems the analysis may be "
            "incomplete."
        )
    )
    sections_visible: List[str] = Field(
        description=(
            "List the major 10-K sections you could clearly see and use "
            "(e.g. 'Item 1 Business', 'Item 1A Risk Factors', "
            "'Item 7 MD&A', 'Item 7A Quantitative and Qualitative "
            "Disclosures', 'Item 8 Financial Statements', "
            "'Item 9A Controls', 'Exhibits / Subsidiaries'). Use the actual "
            "item numbers from the filing."
        )
    )
    sections_missing_or_partial: List[str] = Field(
        description=(
            "List any 10-K sections that appeared missing, truncated, "
            "garbled, or only partially extractable. Empty list if "
            "everything was clean."
        )
    )
    completeness_note: str = Field(
        description=(
            "Short note (1-3 sentences) explaining your completeness "
            "assessment. If full_doc is FALSE, explain specifically what "
            "was missing and how that limits the analysis (which scores "
            "are most affected)."
        )
    )


# ===========================================================================
# SECTION 2 — Thesis classification (Dual Track / typology)
# ---------------------------------------------------------------------------
# Framework ref: "The framework now attempts to distinguish..." table near
# the top of the CSPP v2.6 spec, listing 8 thesis types. Capturing this
# upfront prevents the model from confusing a "Real structural
# transformation" thesis with a "Liquidity amplified narrative" thesis.
# Multi-select via List because real cases often blend types.
# ===========================================================================


class ThesisClassification(BaseModel):
    """Which CSPP v2.6 thesis archetype(s) does this case represent?

    Framework ref: top-of-spec typology table. A clear classification
    anchors how the model should weight evidence (e.g. an "AI
    infrastructure effect" thesis must score 3A/3B harder; a "Liquidity
    amplified narrative" thesis must score 5A/1D harder).
    """

    primary_track: Literal[
        "Market Visible",
        "Latent Civilization Pressure",
        "Both — mixed",
    ] = Field(
        description=(
            "Which of the two CSPP tracks dominates this thesis? "
            "Market Visible = the thesis is already expressed in current "
            "earnings / multiples. Latent = the thesis depends on slow "
            "variables that markets have not yet priced in. Both = a real "
            "mix of both."
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
            "Which thesis archetype(s) from the CSPP v2.6 typology table "
            "does this case represent? Pick all that genuinely apply, "
            "usually 1-3. Don't reach — if only one fits, list only one."
        )
    )
    classification_rationale: str = Field(
        description=(
            "2-4 sentences explaining why these archetypes were chosen, "
            "citing specific disclosures from the 10-K."
        )
    )


# ===========================================================================
# SECTION 3 — Diagnostic modules (unscored, but inform multiple scores)
# ---------------------------------------------------------------------------
# Every module in this section is referenced in the framework as
# "[ Scoring note: This module informs Score X... ]". They do not have
# their own rubric, but the framework requires the analyst to think
# through them. By forcing the model to write them out BEFORE scoring,
# we avoid the failure mode where the model scores domains in isolation
# and misses cross-cutting causality.
# ===========================================================================


class ThreeClocks(BaseModel):
    """Three Clocks Module — physical / financial / narrative clock divergence.

    Framework ref: "Three Clocks Module" + scoring note that the gap
    between the physical clock (observable in 10-K operations) and the
    narrative clock (visible in current market multiples) defines the
    Stage Positioning score (2A).
    """

    physical_clock_state: str = Field(
        description=(
            "Where the company is on the PHYSICAL clock — what real-world "
            "adaptation, capex, capacity, deployment, or operational change "
            "is actually happening per the 10-K. The physical clock always "
            "leads."
        )
    )
    financial_clock_state: str = Field(
        description=(
            "Where the company is on the FINANCIAL clock — how the physical "
            "change has begun to express in earnings, margins, segment "
            "results, and cash flow. The financial clock lags the physical."
        )
    )
    narrative_clock_state: str = Field(
        description=(
            "Where the company is on the NARRATIVE clock — how the market, "
            "analysts, and media currently frame the thesis. The narrative "
            "clock can overshoot or undershoot. Use 'unknown — outside "
            "10-K' if you cannot infer this without market data."
        )
    )
    clock_divergence_assessment: str = Field(
        description=(
            "2-4 sentences on where the three clocks DIVERGE and what that "
            "divergence implies for entry timing. A large physical-leading-"
            "narrative gap implies early-stage opportunity (high 2A). A "
            "narrative-overshooting-physical gap implies crowded / "
            "speculative (low 2A and low 1D)."
        )
    )


class ModuleDiagnostics(BaseModel):
    """Unscored diagnostic modules required by the framework.

    Each `*_note` field is a short structured assessment of an unscored
    CSPP module that the framework's "Scoring note" annotations require
    the analyst to consider before assigning specific component scores.

    The model is instructed to write these BEFORE the domain scores so
    that the diagnostic thinking actually informs the rubric-based scores
    (rather than being post-hoc rationalization).
    """

    three_clocks: ThreeClocks = Field(
        description=(
            "Three Clocks Module output. Informs Score 2A. The gap between "
            "physical and narrative clocks IS the stage positioning."
        )
    )
    bottleneck_inflation_note: str = Field(
        description=(
            "Bottleneck Inflation Module. Informs 1A and 3A. Is the "
            "company SITTING AT a bottleneck (pricing power), or SUFFERING "
            "input-cost inflation from a bottleneck (margin compression)? "
            "Cite specific disclosures from MD&A / cost of revenue."
        )
    )
    continuity_infrastructure_note: str = Field(
        description=(
            "Continuity Infrastructure Module. Informs 1A and 1B. Does the "
            "company's revenue/customer base show that it is essential "
            "infrastructure under stress (recurring, mission-critical, "
            "regulated)? Or is it discretionary? Cite contract structures, "
            "customer concentration, recurring-revenue %."
        )
    )
    capex_arms_race_note: str = Field(
        description=(
            "Capex Arms Race Module. Informs 5C. Is the company's capex "
            "OFFENSIVE (creating durable separation, expanding moat) or "
            "DEFENSIVE (just keeping up, eroding ROIC)? Cite disclosed "
            "capex trajectory, ROIC trend, and competitor commentary."
        )
    )
    asset_holder_policy_bias_note: str = Field(
        description=(
            "Asset Holder Policy Bias Module. Informs 4B. Is this company "
            "an explicit beneficiary of asset-price-stabilizing policy "
            "(housing finance, central bank backstops, GSE-like structures, "
            "REIT tax treatment, buyback-friendly regimes)? Or is it "
            "neutral / disadvantaged? 'Not applicable' if neither."
        )
    )
    private_market_opacity_note: str = Field(
        description=(
            "Private Market Opacity Module. Informs 4B and 5B. Does the "
            "company rely on private credit, mark-to-model assets, or "
            "illiquid funding that could delay (not prevent) price "
            "discovery in stress? Cite specific funding disclosures. "
            "'Not applicable' if funding is fully public/transparent."
        )
    )
    sovereign_industrial_compute_note: str = Field(
        description=(
            "Sovereign Industrial Compute Module. Informs 3B and 4A. Is "
            "the company exposed to export controls, sovereign compute "
            "buildout programs (e.g. CHIPS Act, EU sovereign cloud, "
            "national AI plans), or geographic manufacturing dependencies "
            "in chips/fabs/AI infra? 'Not applicable' for non-tech "
            "companies with no compute exposure."
        )
    )
    jurisdictional_arbitrage_note: str = Field(
        description=(
            "Jurisdictional Arbitrage Module. Informs 4A. Is the company "
            "benefiting from (or threatened by) capital, labor, tax, or "
            "regulatory arbitrage between jurisdictions? Cite geographic "
            "concentration, tax-rate disclosures, redomiciliation events."
        )
    )
    trust_asset_failure_note: str = Field(
        description=(
            "Trust Asset Failure Module. Informs 5B. Is any portion of "
            "this company's value dependent on trust rather than productive "
            "cash flow (sovereign credit, GSE wrap, deposit insurance, "
            "regulatory licensure, network-effect lock-in)? 'Not "
            "applicable' if the value is fully cash-flow-anchored."
        )
    )
    energy_security_note: str = Field(
        description=(
            "Energy Security Module. Informs 3B. Is the company's energy "
            "supply physically secure, dispatchable, geopolitically "
            "insulated, and backed up? Or exposed to import dependence, "
            "grid saturation, and political acceptability risk?"
        )
    )


# ===========================================================================
# SECTION 4 — Latent Pressure Table (8-question test)
# ---------------------------------------------------------------------------
# Framework ref: "Latent Pressure Test" requires 8 questions per
# pressure: observable, inductable, flows_affected, activation_threshold,
# sectors_benefit, sectors_suffer, falsifier, false_positive.
# Previous version of this file covered only 5 of 8.
# ===========================================================================


class LatentPressureRow(BaseModel):
    """One pressure from the Latent Civilization Pressure Registry.

    Framework ref: "Latent Pressure Test" — every pressure relevant to
    the company must answer all 8 questions. The Pressure Registry lists
    physical, supply-chain, technology, human, financial-institutional
    pressures. The model should pull from multiple registry categories.
    """

    pressure: str = Field(
        description=(
            "The latent pressure (e.g. 'grid saturation', 'aging "
            "demographics', 'advanced packaging bottleneck', 'sovereign "
            "debt refinancing stress', 'JIT supply chain fragility'). "
            "Should come from the Latent Civilization Pressure Registry."
        )
    )
    registry_category: Literal[
        "Physical", "Supply chain", "Technology", "Human",
        "Financial / institutional",
    ] = Field(
        description="Which Pressure Registry category this pressure belongs to."
    )
    observable: bool = Field(
        description="Is the pressure directly observable today?"
    )
    inductable: bool = Field(
        description="Is it reasonably inferable from current data?"
    )
    flows_affected: str = Field(
        description=(
            "Which of the framework's flow systems (energy, material, "
            "human, capital, trust, liquidity, information, political, "
            "security, currency, passive capital, collateral, regulatory, "
            "jurisdictional, compute, power) does this pressure propagate "
            "through?"
        )
    )
    activation_threshold: str = Field(
        description=(
            "What level / event would activate this pressure financially? "
            "(e.g. 'insurance withdrawal from coastal markets', 'PJM "
            "interconnect queue exceeds 5 years', 'sovereign refinancing "
            "rate >7%')."
        )
    )
    sectors_benefit: str = Field(
        description="Which sectors / company types BENEFIT when this pressure activates?"
    )
    sectors_suffer: str = Field(
        description="Which sectors / company types SUFFER when this pressure activates?"
    )
    falsifier: str = Field(
        description=(
            "What specific observation would FALSIFY this pressure's "
            "relevance? (Required to prevent narrative capture.)"
        )
    )
    false_positive_risk: str = Field(
        description=(
            "Closest historical analogue from the False Positive Library "
            "(clean tech 2007, 3D printing, SPACs, metaverse, commodity "
            "supercycle, etc.) and a one-sentence note on why this case "
            "is or is not different."
        )
    )
    financial_expression: str = Field(
        description=(
            "How would this pressure first show up in THIS company's "
            "financial results (which line item, which segment, which "
            "ratio)?"
        )
    )


# ===========================================================================
# SECTION 5 — Capital Actor Table
# ---------------------------------------------------------------------------
# Framework ref: "CAPITAL ACTOR TABLE" required output. Forces the model
# to think about WHO is moving capital into/out of this company and what
# fragility that creates.
# ===========================================================================


class CapitalActorRow(BaseModel):
    """One capital actor from the required Capital Actor Table.

    Framework ref: required output table "Capital actor | Incentive |
    Flow direction | Assets affected | Political influence | Fragility
    created".
    """

    actor: str = Field(
        description=(
            "Capital actor (e.g. 'passive index funds', 'sovereign wealth "
            "funds', 'private credit funds', 'retail option flow', "
            "'corporate buyback', 'foreign central bank reserve managers')."
        )
    )
    incentive: str = Field(
        description="What motivates this actor's allocation decision."
    )
    flow_direction: Literal["Inflow", "Outflow", "Neutral", "Mixed"] = Field(
        description=(
            "Net direction of this actor's flow into the company / sector "
            "currently."
        )
    )
    assets_affected: str = Field(
        description="Which assets / instruments the flow most affects."
    )
    political_influence: str = Field(
        description=(
            "The actor's political or regulatory leverage relative to this "
            "company / sector."
        )
    )
    fragility_created: str = Field(
        description=(
            "What fragility (if any) this actor's flow introduces — e.g. "
            "reflexive forced selling, concentration risk, governance "
            "passivity, momentum dependence."
        )
    )


# ===========================================================================
# SECTION 6 — Generic score block reused for all 17 scored components
# ---------------------------------------------------------------------------
# Framework ref: every component rubric requires "Raw score / Weighted /
# Reasoning". The "evidence_classification" field implements the
# "Real Time Evidence Standard" classification mandated for every major
# claim. The "kill_condition_triggered" field implements the kill check
# for the 4 components that have one.
# ===========================================================================


class ComponentScore(BaseModel):
    """A single scored CSPP component.

    The framework defines 17 such components across the 5 domains:
    Domain I has 5, II has 4, III has 3, IV has 2, V has 3.

    (The framework prose says "15 components" but the score sheet
    actually enumerates 17. This is a known typo in the source spec.)
    """

    code: Literal[
        "1A", "1B", "1C", "1D", "1E",
        "2A", "2B", "2C", "2D",
        "3A", "3B", "3C",
        "4A", "4B",
        "5A", "5B", "5C",
    ] = Field(description="CSPP component code from the framework.")
    name: str = Field(
        description="Component name (e.g. 'Substrate Truth')."
    )
    raw_score: int = Field(
        ge=0, le=10,
        description=(
            "Raw score 0-10 per the component rubric in the framework. "
            "Score conservatively when evidence is thin — the framework "
            "rewards calibrated uncertainty over false precision."
        )
    )
    weight: float = Field(
        description=(
            "Weight applied to the raw score per the framework "
            "(1.0 for 1A/1B/1C; 0.5 for all other components)."
        )
    )
    weighted_contribution: float = Field(
        description="raw_score * weight. Contributes to the master score."
    )
    evidence_classification: Literal[
        "Observable", "Inductable", "Weakly inferable", "Hindsight only", "Unknown",
    ] = Field(
        description=(
            "Real Time Evidence Standard classification of the evidence "
            "underlying this score. Per the framework, this classification "
            "is MANDATORY for every major claim."
        )
    )
    reasoning: str = Field(
        description=(
            "Explicit reasoning for the score, citing specific disclosures "
            "from the 10-K (item, section, or page-level reference where "
            "possible). 2-6 sentences. Must be written probabilistically, "
            "never as inevitability."
        )
    )
    supporting_evidence: List[str] = Field(
        description=(
            "List of specific, verifiable evidence items from the 10-K "
            "that anchor this score (financial figures, contract "
            "disclosures, risk factor language, segment data, etc.). Each "
            "bullet should distinguish observable facts from inferences."
        )
    )
    kill_condition_triggered: bool = Field(
        description=(
            "TRUE only for components 1A (raw<=2), 1C (raw<=2), "
            "1D (raw<=1), or 2C (raw<=1) when the threshold is crossed. "
            "FALSE otherwise, including for components that have no kill "
            "condition (1B, 1E, 2A, 2B, 2D, 3A-3C, 4A-4B, 5A-5C)."
        )
    )


# ===========================================================================
# SECTION 7 — Domain I: Five Truth Layers (40 weighted pts)
# ---------------------------------------------------------------------------
# The framework's primary causal filter. Three components carry full
# weight (1.0); two carry half weight (0.5) because they require market
# context beyond a single 10-K. Three of the five also carry kill
# conditions that cap the master score.
# ===========================================================================


class FinancialSurvivalRatios(BaseModel):
    """Concrete balance-sheet ratios that drive the 1C rubric.

    Framework ref: 1C rubric requires "Key ratios" section — Net debt /
    EBITDA, Interest coverage, FCF yield. Added: nearest debt maturity
    and liquidity buffer for full stress-test context.
    """

    net_debt_to_ebitda: str = Field(
        description="Net debt / EBITDA. Use 'n/a' if not disclosed / derivable."
    )
    interest_coverage: str = Field(
        description="EBIT / interest expense. Use 'n/a' if not derivable."
    )
    fcf_yield: str = Field(
        description=(
            "Free cash flow yield (FCF / market cap or FCF / enterprise "
            "value — say which). Use 'unknown — outside 10-K' if market "
            "cap is unknown."
        )
    )
    nearest_debt_maturity: str = Field(
        description=(
            "Year and approximate size of the nearest major debt maturity "
            "from the long-term debt note."
        )
    )
    liquidity_buffer: str = Field(
        description=(
            "Cash + marketable securities + undrawn revolver as disclosed."
        )
    )


class ValuationContext(BaseModel):
    """Market context used to score 1D (Valuation Entry Truth).

    Framework ref: 1D rubric requires the analyst to assess whether the
    thesis is already capitalized. This requires data OUTSIDE the 10-K
    (current multiples, peer set, analyst coverage). If unavailable, the
    model must say so and score conservatively.
    """

    current_multiple: str = Field(
        description=(
            "Best single valuation multiple "
            "(e.g. 'EV/EBITDA 14x', 'P/E 28x', 'P/S 6x'). "
            "Use 'unknown — outside 10-K' if market data is unavailable."
        )
    )
    peer_multiple_range: str = Field(
        description=(
            "Peer multiple range. 'unknown — outside 10-K' if no reliable "
            "peer set is available without additional data."
        )
    )
    analyst_coverage_skew: str = Field(
        description=(
            "Qualitative skew of analyst coverage "
            "(e.g. 'mostly bullish', 'split', 'hostile'). "
            "Use 'unknown — outside 10-K' if not inferable."
        )
    )
    stage_implication: str = Field(
        description=(
            "1-2 sentences: given the multiple vs. peer range vs. "
            "narrative clock state, what stage (0-5) does the valuation "
            "imply, and how does that constrain the 1D score?"
        )
    )


class DomainI_FiveTruthLayers(BaseModel):
    """Domain I — Five Truth Layers (max 40 weighted pts).

    Components:
      1A Substrate Truth        weight 1.0   KILL: raw<=2 caps master at 40
      1B Economic Capture       weight 1.0
      1C Financial Survival     weight 1.0   KILL: raw<=2 caps master at 50
      1D Valuation Entry        weight 0.5   KILL: raw<=1 caps master at 60
      1E Reflexive System       weight 0.5

    Maximum domain total: 1.0*10 + 1.0*10 + 1.0*10 + 0.5*10 + 0.5*10 = 40.
    """

    substrate_truth_1A: ComponentScore = Field(
        description=(
            "1A — Substrate Truth (weight 1.0). KILL: raw<=2 caps master "
            "at 40. Is the physical or social transformation this company "
            "operates within actually real and measurable from disclosed "
            "data?"
        )
    )
    economic_capture_truth_1B: ComponentScore = Field(
        description=(
            "1B — Economic Capture Truth (weight 1.0). Can this company "
            "durably capture value from the transformation?"
        )
    )
    financial_survival_truth_1C: ComponentScore = Field(
        description=(
            "1C — Financial Survival Truth (weight 1.0). KILL: raw<=2 "
            "caps master at 50. Can the company survive a severe adverse "
            "financing environment?"
        )
    )
    financial_survival_ratios: FinancialSurvivalRatios = Field(
        description=(
            "The actual disclosed numbers that justify the 1C score. "
            "Required for auditability."
        )
    )
    valuation_entry_truth_1D: ComponentScore = Field(
        description=(
            "1D — Valuation Entry Truth (weight 0.5). KILL: raw<=1 caps "
            "master at 60. High score = thesis undercapitalized "
            "(favorable entry); low score = crowded."
        )
    )
    valuation_context: ValuationContext = Field(
        description="Market context that justifies the 1D score."
    )
    reflexive_system_truth_1E: ComponentScore = Field(
        description=(
            "1E — Reflexive System Truth (weight 0.5). Will capital flows "
            "into this sector reshape reality FOR or AGAINST the thesis?"
        )
    )
    domain_total: float = Field(
        ge=0, le=40,
        description=(
            "Sum of weighted_contribution across 1A-1E (max 40). "
            "Compute exactly — this feeds the master score."
        )
    )


# ===========================================================================
# SECTION 8 — Domain II: Epistemic Integrity (20 weighted pts)
# ---------------------------------------------------------------------------
# The framework's quality-of-analysis filter. All 4 components carry
# weight 0.5. 2C carries an integrity flag (not a cap) — raw<=1 marks
# the entire analysis structurally unreliable but does NOT cap the
# master score.
# ===========================================================================


class AntiHindsightChecklist(BaseModel):
    """The 7 mandatory anti-hindsight discipline questions.

    Framework ref: "ANTI-HINDSIGHT DISCIPLINE MODULE" — every analysis
    must answer these 7 questions. Scoring 2C above 6 requires all 7
    answered; above 7 requires the false positive library to be
    consulted (captured here in historical_false_positives).
    """

    what_was_observable_then: str = Field(
        description="What was directly observable at the time of this 10-K?"
    )
    what_was_inferable_then: str = Field(
        description=(
            "What was reasonably inferable but not directly observable at "
            "the time of this 10-K?"
        )
    )
    what_was_unknowable: str = Field(
        description="What was fundamentally unknowable at the time of this 10-K?"
    )
    alternative_futures: List[str] = Field(
        description=(
            "At least 2 plausible alternative futures (not just the base "
            "thesis). Implements the Alternative Futures Module."
        )
    )
    contradicting_signals: List[str] = Field(
        description=(
            "Specific disclosures or data points in this 10-K that "
            "CONTRADICT the thesis. Be honest — every real thesis has "
            "some."
        )
    )
    likely_blind_spots: List[str] = Field(
        description=(
            "What this protocol applied to this filing is likely to miss "
            "(model limitations, framework limitations, evidence gaps)."
        )
    )
    historical_false_positives: List[str] = Field(
        description=(
            "Historical analogues from the False Positive Library — clean "
            "tech 2007, 3D printing, SPACs, metaverse, commodity "
            "supercycle, etc. — that resemble this thesis. For each, a "
            "short note on why this case is or is not different."
        )
    )


# Implementation note: previous versions used a List[PreMortemScenario]
# with a free-form category enum. That allowed the model to skip
# categories. The framework REQUIRES all 8. We now expose 8 separate
# required fields so the schema itself guarantees coverage. The trade-off
# is verbosity, but the framework explicitly says "Full pre-mortem across
# all eight categories" is required for the highest scores.
class PreMortemScenario(BaseModel):
    """One failure-category scenario within the Pre-Mortem Module."""

    failure_mode: str = Field(
        description=(
            "How the thesis fails in this category, given the 10-K "
            "disclosures. If this category genuinely doesn't apply, write "
            "'Not applicable — ' followed by why, and set probability to "
            "the residual (typically 1-5%)."
        )
    )
    probability_pct: int = Field(
        ge=0, le=100,
        description=(
            "Estimated probability (0-100) of this failure mode "
            "materializing within a 5-year horizon."
        )
    )
    early_warning_signals: List[str] = Field(
        description="Concrete signals that would indicate this failure is unfolding."
    )
    kill_condition: str = Field(
        description=(
            "Specific, measurable kill condition tied to this failure "
            "mode (e.g. 'gross margin falls below 35% for two consecutive "
            "quarters', 'net debt/EBITDA exceeds 4.0x'). Required for 2D "
            "scores above 6."
        )
    )


class PreMortemScenarios(BaseModel):
    """All 8 mandated Pre-Mortem failure categories as separate required fields.

    Framework ref: "PRE-MORTEM MODULE" enumerates exactly 8 failure
    categories. To score 2D >= 8 ("Exemplary"), all 8 must be modeled
    with probabilities. Separate required fields prevent the model from
    skipping any.
    """

    technology: PreMortemScenario = Field(
        description="Technology failure: substrate obsolescence, breakthrough by competitor, technical risk."
    )
    financing: PreMortemScenario = Field(
        description="Financing failure: refinancing wall, credit downgrade, capital market closure."
    )
    economic_capture: PreMortemScenario = Field(
        description="Economic capture failure: moat erosion, margin compression, customer concentration loss."
    )
    valuation: PreMortemScenario = Field(
        description="Valuation failure: multiple compression, rerating, consensus reversal."
    )
    policy: PreMortemScenario = Field(
        description="Policy failure: subsidy removal, tariff imposition, sanctions, monetary regime shift."
    )
    substitution: PreMortemScenario = Field(
        description="Substitution failure: cheaper / better alternative, demand shifts to substitute."
    )
    timing: PreMortemScenario = Field(
        description="Timing failure: thesis correct but multi-year delay; capital exhausted before payoff."
    )
    regulatory: PreMortemScenario = Field(
        description="Regulatory failure: breakup, profit cap, forced divestiture, licensure loss."
    )


class DecisionRule(BaseModel):
    """Decision Rule Module — 7 mandated fields.

    Framework ref: "DECISION RULE MODULE" requires every thesis to
    specify Entry conditions, Evidence thresholds, Position sizing,
    Kill conditions, Valuation discipline, Survivability assumptions,
    Monitoring signals. Required for 2D score above 7.
    """

    entry_conditions: str = Field(
        description="What specific price level / evidence event would trigger initial entry?"
    )
    evidence_thresholds: str = Field(
        description=(
            "What further evidence (e.g. specific KPI thresholds, "
            "disclosed contract wins, margin trajectory) would justify "
            "scaling the position?"
        )
    )
    position_sizing_guidance: str = Field(
        description=(
            "How large should this position be relative to the "
            "portfolio's survivability assumptions and the company's own "
            "fragility profile (Domain V)?"
        )
    )
    kill_conditions: str = Field(
        description=(
            "Specific, measurable conditions that would trigger a full "
            "exit of the position. Distinct from the framework's score-"
            "level kill conditions — these are POSITION-level."
        )
    )
    valuation_discipline: str = Field(
        description=(
            "Maximum multiple or absolute valuation level at which to "
            "start trimming, regardless of thesis confirmation."
        )
    )
    survivability_assumptions: str = Field(
        description="What the position assumes about the company surviving stress."
    )
    monitoring_signals: List[str] = Field(
        description=(
            "Measurable signals to track on an ongoing basis (quarterly "
            "KPIs, macro variables, sector flow data)."
        )
    )


class DomainII_EpistemicIntegrity(BaseModel):
    """Domain II — Epistemic Integrity (max 20 weighted pts).

    All 4 components carry weight 0.5. 2C carries an INTEGRITY FLAG
    (not a master-score cap): raw<=1 marks the entire analysis
    structurally unreliable.

    Maximum domain total: 0.5*10 * 4 = 20.
    """

    latent_pressure_stage_2A: ComponentScore = Field(
        description=(
            "2A — Latent Pressure Stage Positioning (weight 0.5). Where "
            "in the recognition cycle is the primary latent pressure? "
            "High score = early stage (Stage 0-1); low score = crowded "
            "(Stage 4-5)."
        )
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
        description=(
            "2B — Evidence Observability (weight 0.5). What proportion of "
            "your claims about this company are directly observable in "
            "this 10-K vs. inferred?"
        )
    )
    anti_hindsight_integrity_2C: ComponentScore = Field(
        description=(
            "2C — Anti-Hindsight Integrity (weight 0.5). INTEGRITY FLAG: "
            "raw<=1 marks the analysis structurally unreliable but does "
            "NOT cap the master score."
        )
    )
    anti_hindsight_checklist: AntiHindsightChecklist = Field(
        description=(
            "All 7 anti-hindsight questions answered. Required for 2C > 6. "
            "Required for 2C > 7 that the false positive library bucket "
            "(historical_false_positives) contains real analogues."
        )
    )
    pre_mortem_discipline_2D: ComponentScore = Field(
        description=(
            "2D — Pre-Mortem Discipline (weight 0.5). To score above 6, "
            "kill conditions and monitoring signals must be specific. To "
            "score above 7, decision_rule must be complete. To score 8+, "
            "all 8 pre_mortem_scenarios categories must have meaningful "
            "content."
        )
    )
    pre_mortem_scenarios: PreMortemScenarios = Field(
        description=(
            "Pre-mortem across all 8 mandated failure categories. Separate "
            "required fields prevent skipping."
        )
    )
    decision_rule: DecisionRule = Field(
        description="Decision Rule Module — all 7 fields required for 2D > 7."
    )
    domain_total: float = Field(
        ge=0, le=20,
        description="Sum of weighted_contribution across 2A-2D (max 20)."
    )


# ===========================================================================
# SECTION 9 — Domain III: Physical Reality Anchor (15 weighted pts)
# ---------------------------------------------------------------------------
# The framework's anchor against pure software / pure narrative theses.
# All 3 components carry weight 0.5. No kill conditions.
# Particularly important for AI infrastructure, energy, and materials
# theses where the thesis depends on real-world bottlenecks.
# ===========================================================================


class DomainIII_PhysicalRealityAnchor(BaseModel):
    """Domain III — Physical Reality Anchor (max 15 weighted pts).

    Maximum domain total: 0.5*10 * 3 = 15.

    For purely software / services companies with no physical collision,
    3A and 3B may legitimately score 0-2. That is correct — the
    framework does not penalize digital companies, it just doesn't
    award them physicalization credit they haven't earned.
    """

    physicalization_constraint_3A: ComponentScore = Field(
        description=(
            "3A — Physicalization Constraint Depth (weight 0.5). How "
            "tightly is the company's capability constrained by physical "
            "bottlenecks? 0 = purely digital with no physical collision; "
            "10 = hard physical ceiling owned by the company."
        )
    )
    primary_physical_constraint: str = Field(
        description=(
            "The dominant physical bottleneck the company sits at or "
            "depends on (e.g. 'leading-edge HBM packaging capacity', "
            "'grid interconnect queue in PJM', 'lithium hydroxide "
            "supply'). Use 'None — purely digital' if no binding "
            "constraint exists."
        )
    )
    capex_to_revenue_pct: str = Field(
        description="Capex as % of revenue (latest fiscal year), or 'n/a'."
    )
    power_and_energy_position_3B: ComponentScore = Field(
        description=(
            "3B — Power and Energy Position (weight 0.5). Does the "
            "company control or uniquely benefit from critical power / "
            "energy constraints?"
        )
    )
    disclosed_energy_agreements: List[str] = Field(
        description=(
            "Specific PPAs, captive generation, hydro / nuclear / grid "
            "agreements disclosed in the filing. Empty list if none "
            "disclosed."
        )
    )
    strategic_scarcity_3C: ComponentScore = Field(
        description=(
            "3C — Strategic Scarcity Quality (weight 0.5). How durable "
            "and monetizable is the scarcity the company controls or "
            "benefits from?"
        )
    )
    scarcity_type: str = Field(
        description=(
            "Type of scarcity (geopolitical, regulatory, physical, "
            "technological), or 'No structural scarcity' if none exists."
        )
    )
    substitution_risks: List[str] = Field(
        description="Disclosed or evident substitution threats to that scarcity."
    )
    domain_total: float = Field(
        ge=0, le=15,
        description="Sum of weighted_contribution across 3A-3C (max 15)."
    )


# ===========================================================================
# SECTION 10 — Domain IV: Capital Topology (10 weighted pts)
# ---------------------------------------------------------------------------
# Captures the modern reality that concentrated, mobile, politically
# influential capital shapes outcomes — not just productive capacity.
# 2 components, weight 0.5 each.
#
# NOTE: 10-Ks contain limited capital topology data. Detailed beneficial
# ownership is in DEF 14A (proxy), not 10-K. The 10-K cover sheet does
# disclose >5% holders and Section 16 officers/directors. 13F data is
# external. The model is instructed to be honest when data is unavailable.
# ===========================================================================


class DomainIV_CapitalTopology(BaseModel):
    """Domain IV — Capital Topology (max 10 weighted pts).

    Maximum domain total: 0.5*10 * 2 = 10.
    """

    capital_concentration_alignment_4A: ComponentScore = Field(
        description=(
            "4A — Capital Concentration Alignment (weight 0.5). Is large, "
            "concentrated, politically influential capital aligned with "
            "the thesis?"
        )
    )
    largest_disclosed_holders: List[str] = Field(
        description=(
            "Largest beneficial owners disclosed in the 10-K itself "
            "(typically the cover page lists >5% beneficial holders and "
            "named executive officer ownership). The 10-K does NOT "
            "include the full institutional holder list — that comes from "
            "DEF 14A and 13F filings. If the 10-K cover lacks this, say "
            "so and list only what is in-filing."
        )
    )
    insider_ownership_pct: str = Field(
        description="Aggregate insider/officer/director ownership %, or 'n/a'."
    )
    institutional_ownership_signal: str = Field(
        description=(
            "Qualitative signal of institutional positioning if disclosed "
            "or reasonably inferable from the filing's references to "
            "shareholder communications; otherwise 'unknown — outside "
            "10-K'."
        )
    )
    institutional_capture_favorability_4B: ComponentScore = Field(
        description=(
            "4B — Institutional Capture Favorability (weight 0.5). Does "
            "the regulatory and political environment PROTECT this "
            "company's thesis?"
        )
    )
    key_regulatory_disclosures: List[str] = Field(
        description=(
            "Specific regulatory items from Item 1 (Business — Regulation) "
            "and Item 1A (Risk Factors — Regulatory) that drive the 4B "
            "score."
        )
    )
    government_revenue_pct: str = Field(
        description="% of revenue from government counterparties, or 'n/a'."
    )
    domain_total: float = Field(
        ge=0, le=10,
        description="Sum of weighted_contribution across 4A-4B (max 10)."
    )


# ===========================================================================
# SECTION 11 — Domain V: Fragility Profile (15 weighted pts)
# ---------------------------------------------------------------------------
# Tests survivability across multiple stress dimensions: rates / liquidity
# (5A), sovereign and trust breakdown (5B), and competitive
# commoditization (5C). 3 components, weight 0.5 each.
# ===========================================================================


class DomainV_FragilityProfile(BaseModel):
    """Domain V — Fragility Profile (max 15 weighted pts).

    Maximum domain total: 0.5*10 * 3 = 15.
    """

    liquidity_independence_5A: ComponentScore = Field(
        description=(
            "5A — Liquidity Independence (weight 0.5). How independent is "
            "the business model from easy money? Consolidates Liquidity "
            "Fantasy Module and Cost of Capital Reappearance Module."
        )
    )
    sovereign_and_trust_stability_5B: ComponentScore = Field(
        description=(
            "5B — Sovereign and Trust Stability (weight 0.5). How exposed "
            "is the company to sovereign debt fragility or trust "
            "breakdown? Consolidates Sovereign Debt Fragility Module and "
            "Trust Asset Failure Module."
        )
    )
    geographic_revenue_concentration: str = Field(
        description=(
            "Concentration of revenue by jurisdiction "
            "(e.g. 'US 78%, EMEA 14%, APAC 8%'). Note the primary "
            "operating jurisdiction's sovereign rating if discernible."
        )
    )
    commoditization_resistance_5C: ComponentScore = Field(
        description=(
            "5C — Commoditization Resistance (weight 0.5). How resistant "
            "is the company to value destruction from competitive capex "
            "or technological commoditization? Consolidates Model "
            "Commoditization Module and Capex Arms Race Module."
        )
    )
    gross_margin_trend_3yr: str = Field(
        description=(
            "Gross margin trajectory over the last 3 disclosed fiscal "
            "years. Use 'insufficient history' if the company is new."
        )
    )
    roic_trend_3yr: str = Field(
        description=(
            "Return on invested capital trajectory over the last 3 "
            "disclosed fiscal years. Use 'insufficient history' if new."
        )
    )
    primary_commoditization_risk: str = Field(
        description="The single most credible commoditization or substitution risk."
    )
    domain_total: float = Field(
        ge=0, le=15,
        description="Sum of weighted_contribution across 5A-5C (max 15)."
    )


# ===========================================================================
# SECTION 12 — Kill condition check, scenarios, tables, audit, ranking
# ---------------------------------------------------------------------------
# Final synthesis structures. Kill conditions audit the four caps before
# computing the master score. Scenarios implement Probabilistic Inference.
# Gap Safeguards Audit implements the framework's 10 mandatory audit
# layers. Signal Ranking implements the Signal Ranking Module.
# ===========================================================================


class KillConditionCheck(BaseModel):
    """Explicit audit of all four kill / integrity conditions.

    Framework ref: Three master-score caps (1A, 1C, 1D) and one
    integrity flag (2C). Audit values here must be consistent with the
    raw scores in the domain blocks. Inconsistency is an analyst error.
    """

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
            "TRUE if Score 2C raw <= 1. Does NOT cap the master score, "
            "but marks the entire analysis as structurally unreliable."
        )
    )
    applicable_cap: int = Field(
        ge=0, le=100,
        description=(
            "Lowest cap triggered (40 / 50 / 60), or 100 if no cap "
            "applies. This is the value used in the master_score "
            "calculation."
        )
    )


class ProbabilisticScenario(BaseModel):
    """One leg of the Bull / Base / Bear scenario set.

    Framework ref: "PROBABILISTIC INFERENCE MODULE" — every thesis
    requires three scenarios with probabilities. The three probabilities
    should sum to ~100.
    """

    name: Literal["Bull", "Base", "Bear"] = Field(description="Scenario label.")
    narrative: str = Field(description="What has to be true for this scenario to play out.")
    probability_pct: int = Field(
        ge=0, le=100,
        description="Estimated probability for this scenario (the three must sum to ~100)."
    )
    price_target_or_outcome: str = Field(
        description=(
            "Qualitative or quantitative outcome "
            "(e.g. 'fair value $145, +30%', or 'multiple compresses to 12x')."
        )
    )
    key_drivers: List[str] = Field(
        description="2-4 specific drivers that distinguish this scenario from the others."
    )


class GapSafeguardsAudit(BaseModel):
    """The 10 mandatory Gap Safeguard audit layers.

    Framework ref: "GAP SAFEGUARDS" section — "All ten gaps are mandatory
    audit layers for every CSPP analysis." Each field is a short note
    (1-3 sentences) on how the gap was considered, or "Not applicable"
    with reasoning.
    """

    gap_1_quantification: str = Field(
        description=(
            "Quantification: Were the major claims quantified with actual "
            "disclosed numbers rather than qualitative assertions?"
        )
    )
    gap_2_branch_control: str = Field(
        description=(
            "Branch control: Were alternative causal branches explicitly "
            "considered, rather than collapsing to a single forward path?"
        )
    )
    gap_3_narrative_psychology: str = Field(
        description=(
            "Narrative psychology: Did the analysis guard against "
            "narrative intoxication, momentum bias, and inevitability "
            "framing?"
        )
    )
    gap_4_reflexivity: str = Field(
        description=(
            "Reflexivity: Were reflexive dynamics (capital flows "
            "reshaping reality) modeled explicitly per Layer 5?"
        )
    )
    gap_5_institutional_power: str = Field(
        description=(
            "Institutional power: Were lobbying, regulatory capture, and "
            "sovereign influence modeled per Domain IV?"
        )
    )
    gap_6_substitution_systems: str = Field(
        description=(
            "Substitution systems: Was technological / business-model "
            "substitution modeled across multiple time horizons?"
        )
    )
    gap_7_topology_analysis: str = Field(
        description=(
            "Topology analysis: Was the capital topology (who owns, who "
            "trades, who controls) mapped, not just the company itself?"
        )
    )
    gap_8_temporal_dynamics: str = Field(
        description=(
            "Temporal dynamics: Were the three clocks (physical, "
            "financial, narrative) distinguished and their divergence "
            "analyzed?"
        )
    )
    gap_9_market_structure: str = Field(
        description=(
            "Market structure: Were passive flows, ETF concentration, "
            "options gamma, and structural buyers/sellers considered?"
        )
    )
    gap_10_civilization_hierarchy: str = Field(
        description=(
            "Civilization hierarchy: Were the slow latent pressures "
            "(energy, demographics, geopolitics, climate) placed above "
            "fast variables in the causal chain?"
        )
    )


class SignalRanking(BaseModel):
    """Signal Ranking Module — top causal signals for this thesis.

    Framework ref: "SIGNAL RANKING MODULE" lists 24 highest-priority
    causal signals. For each thesis the analyst must identify which
    handful of those signals are most determinative.
    """

    top_signals: List[str] = Field(
        description=(
            "The 3-5 most causally important signals for this specific "
            "thesis, drawn from the framework's 24-signal priority list "
            "(leverage dependency, liquidity dependency, concentration, "
            "policy dependency, supply discipline, globalization stress, "
            "latent pressure activation, infrastructure bottlenecks, "
            "continuity infrastructure importance, substitution flow "
            "emergence, inflation persistence, issuance quality "
            "deterioration, cost of capital sensitivity, energy security "
            "exposure, strategic scarcity, sovereign debt fragility, "
            "capital concentration, institutional capture, power "
            "bottlenecks, compute concentration, AI physicalization, "
            "capex intensity, model commoditization risk)."
        )
    )
    ranking_rationale: str = Field(
        description=(
            "2-4 sentences on why these signals dominate for this "
            "particular company and what to watch for early warning."
        )
    )


# ===========================================================================
# SECTION 13 — Top-level result
# ---------------------------------------------------------------------------
# Field ORDER below is meaningful. Gemini 2.5+ preserves field order in
# output, and the order is designed to walk the model through the
# framework's analytic flow:
#
#   1.  Identify the subject
#   2.  Verify document completeness
#   3.  Classify the thesis type (Dual Track + 8-type typology)
#   4.  Think diagnostically (unscored modules) BEFORE scoring
#   5.  Orient on latent pressures and capital actors
#   6.  Score the five domains
#   7.  Audit kill conditions
#   8.  Compute totals, tier, capital bucket
#   9.  Project Bull / Base / Bear scenarios
#  10.  State thesis statement + falsifiers
#  11.  Audit method (10 gaps) and rank signals
#  12.  Executive summary
# ===========================================================================


class CSPPv26AnalysisResult(BaseModel):
    """Top-level CSPP v2.6 analysis result for a single fiscal year 10-K.

    Maximum master_score = 100 (sum of domain maxima: 40 + 20 + 15 + 10 + 15).
    Master score may be capped by kill conditions (40 / 50 / 60).
    Integrity flag (2C raw <= 1) does NOT cap but flags the analysis as
    structurally unreliable.
    """

    # -------------------------------------------------------------------
    # 1. Identification
    # -------------------------------------------------------------------
    company_name: str = Field(description="Full legal company name from the 10-K cover.")
    ticker: str = Field(description="Ticker symbol passed into the workflow.")
    fiscal_year: int = Field(description="Fiscal year of the 10-K analyzed.")
    primary_exchange: str = Field(
        description="Primary listing exchange (e.g. 'NASDAQ', 'NYSE')."
    )
    primary_thesis: str = Field(
        description=(
            "One-paragraph statement of the core CSPP thesis being "
            "scored. Must be written probabilistically, not as certainty."
        )
    )

    # -------------------------------------------------------------------
    # 2. Document completeness self-report (transparency before analysis)
    # -------------------------------------------------------------------
    document_completeness: DocumentCompleteness = Field(
        description="Model's self-report on whether it read the full 10-K."
    )

    # -------------------------------------------------------------------
    # 3. Thesis classification (frames how scores should be weighted)
    # -------------------------------------------------------------------
    thesis_classification: ThesisClassification = Field(
        description="Dual Track and 8-type typology classification of the thesis."
    )

    # -------------------------------------------------------------------
    # 4. Diagnostic modules (think first, score second)
    # -------------------------------------------------------------------
    module_diagnostics: ModuleDiagnostics = Field(
        description=(
            "Unscored diagnostic modules required by the framework. "
            "These MUST be completed before scoring the domains so the "
            "diagnostic thinking actually informs the rubric-based scores."
        )
    )

    # -------------------------------------------------------------------
    # 5. Required orientation tables
    # -------------------------------------------------------------------
    latent_pressure_table: List[LatentPressureRow] = Field(
        description=(
            "Mandatory Latent Pressure Table — at least 3 rows, drawing "
            "from at least 2 different Pressure Registry categories. "
            "Each row must answer all 8 questions of the Latent Pressure "
            "Test."
        )
    )
    capital_actor_table: List[CapitalActorRow] = Field(
        description=(
            "Mandatory Capital Actor Table — at least 2 rows, covering "
            "the most influential capital actors for this company / sector."
        )
    )

    # -------------------------------------------------------------------
    # 6. The five scoring domains (40 + 20 + 15 + 10 + 15 = 100 pts max)
    # -------------------------------------------------------------------
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

    # -------------------------------------------------------------------
    # 7. Kill condition audit (apply caps BEFORE computing master score)
    # -------------------------------------------------------------------
    kill_condition_check: KillConditionCheck = Field(
        description="Audit of all four kill / integrity conditions."
    )

    # -------------------------------------------------------------------
    # 8. Master score, tier, capital bucket
    # -------------------------------------------------------------------
    raw_total: float = Field(
        ge=0, le=100,
        description="Uncapped sum of all five domain totals (max 100)."
    )
    master_score: int = Field(
        ge=0, le=100,
        description=(
            "Final master score = round(min(raw_total, applicable_cap)). "
            "Apply kill condition caps FIRST."
        )
    )
    allocation_tier: Literal[
        "Exceptional (85-100)",
        "High conviction (70-84)",
        "Moderate conviction (55-69)",
        "Low conviction (40-54)",
        "Speculative (25-39)",
        "Reject (0-24)",
    ] = Field(description="Allocation tier mapped from the master score.")
    capital_bucket: Literal[
        "Core capital",
        "Defensive growth",
        "Real asset ballast",
        "Transition capital",
        "Optionality capital",
        "Watchlist capital",
        "Avoid capital",
    ] = Field(description="Recommended Barbell Allocation bucket per the framework.")

    # -------------------------------------------------------------------
    # 9. Probabilistic scenarios
    # -------------------------------------------------------------------
    probabilistic_scenarios: List[ProbabilisticScenario] = Field(
        description=(
            "Exactly three scenarios — Bull, Base, Bear — with "
            "probabilities summing to approximately 100."
        )
    )

    # -------------------------------------------------------------------
    # 10. Thesis statement and falsifiers
    # -------------------------------------------------------------------
    key_thesis_statement: str = Field(
        description=(
            "One-paragraph core causal thesis this score reflects. MUST "
            "NOT be written as certainty. MUST explicitly distinguish "
            "observable, inductable, and unknowable elements. Implements "
            "the framework's Humility Principle."
        )
    )
    primary_falsifiers: List[str] = Field(
        description=(
            "Exactly 3 specific, future-observable signals that would "
            "materially reduce this score if they appeared in a future "
            "10-K or in market data. Each must be falsifiable and "
            "measurable."
        )
    )

    # -------------------------------------------------------------------
    # 11. Audit method (10 gaps) and signal ranking
    # -------------------------------------------------------------------
    gap_safeguards_audit: GapSafeguardsAudit = Field(
        description="Mandatory 10-gap audit per the framework's Gap Safeguards section."
    )
    signal_ranking: SignalRanking = Field(
        description="Signal Ranking Module — top causal signals for this thesis."
    )

    # -------------------------------------------------------------------
    # 12. Executive summary
    # -------------------------------------------------------------------
    executive_summary: str = Field(
        description=(
            "Final 4-6 sentence executive summary: master score, tier, "
            "capital bucket, any kill condition or integrity flag, and "
            "the single most important reason a CSPP allocator would or "
            "would not act. No new claims here — only synthesis of what "
            "is already in the structured fields above."
        )
    )


# ===========================================================================
# SECTION 14 — Workflow class
# ---------------------------------------------------------------------------
# The prompt below is intentionally long because the CSPP framework is
# dense and the model needs explicit guidance on (a) how to interpret
# each rubric, (b) how to handle edge cases (pre-revenue, multi-segment,
# non-US, REITs, etc.), and (c) the analytic order of operations.
#
# Prompt length is acceptable because the 10-K itself dwarfs it and
# Gemini's input context is generous.
# ===========================================================================


class CSPPv26Analyzer(CustomWorkflow):
    """CSPP v2.6 single-year 10-K analyzer.

    Applies the Causal Substrate Propagation Protocol v2.6 to the most
    recent fiscal year of a company's 10-K and produces a 0-100 master
    score with kill condition audits, allocation tier, capital bucket,
    Bull/Base/Bear scenarios, latent pressure and capital actor tables,
    a 10-gap audit, and signal ranking.

    Single-year framework: min_years = max_years = 1. The framework's
    stage positioning and reflexivity analysis is point-in-time.
    """

    name = "CSPP v2.6 — Causal Substrate Propagation"
    description = (
        "Apply the Causal Substrate Propagation Protocol v2.6 to one "
        "fiscal year of a 10-K. Produces 17 component scores across 5 "
        "domains, kill condition audit, Bull/Base/Bear scenarios, "
        "10-gap audit, signal ranking, and a 0-100 master score with "
        "allocation tier and capital bucket."
    )
    icon = "🧭"
    min_years = 1
    max_years = 1  # Single-year framework — most recent 10-K only.
    category = "fundamental"

    @property
    def prompt_template(self) -> str:
        # The prompt is structured to walk the model through the same
        # analytic flow that the schema enforces:
        #   orient -> diagnose -> score -> audit -> conclude.
        # Each major section below maps directly to a top-level field in
        # the CSPPv26AnalysisResult schema.
        return """
You are applying the CSPP v2.6 (Causal Substrate Propagation Protocol)
analytical framework to {ticker} for fiscal year {year}, based ONLY on
the 10-K filing provided at the end of this prompt.

CSPP v2.6 is a first-principles causal framework. It exists for real-time
causal inference under uncertainty, NOT for retrospective narrative
construction. Every conclusion you produce must remain probabilistic and
falsifiable. The Humility Principle is core: the framework assumes
important systems are partially unknowable, so survivability matters more
than predictive precision.

============================================================================
SCORING ARCHITECTURE (100-point master score)
============================================================================

Domain I    Five Truth Layers            40 pts   (5 components)
Domain II   Epistemic Integrity          20 pts   (4 components)
Domain III  Physical Reality Anchor      15 pts   (3 components)
Domain IV   Capital Topology             10 pts   (2 components)
Domain V    Fragility Profile            15 pts   (3 components)
                                       -----
                                        100 pts   (17 components total)

Each component is scored 0-10 raw, then multiplied by its weight (1.0
for 1A/1B/1C; 0.5 for everything else).

KILL CONDITIONS (apply BEFORE finalizing the master score):
  - 1A Substrate Truth     raw <= 2  -> master capped at 40
  - 1C Financial Survival  raw <= 2  -> master capped at 50
  - 1D Valuation Entry     raw <= 1  -> master capped at 60
  - 2C Anti-Hindsight      raw <= 1  -> INTEGRITY FLAG (no cap, but the
                                       analysis is marked structurally
                                       unreliable)

Final master_score = round(min(raw_total, applicable_cap)).

Allocation tiers (final mapping):
  85-100  Exceptional          Flagship allocation
  70-84   High conviction      Meaningful position
  55-69   Moderate conviction  Partial or transition capital
  40-54   Low conviction       Watchlist or optionality only
  25-39   Speculative          Avoid or micro-position only
  0-24    Reject               Short candidate or hard pass

============================================================================
ORDER OF OPERATIONS (critical — follow this flow)
============================================================================

1.  Identify the company and verify document_completeness HONESTLY.
2.  Classify the thesis (Dual Track + 8-type typology).
3.  Write module_diagnostics — Three Clocks, Bottleneck Inflation,
    Continuity Infrastructure, Capex Arms Race, Asset Holder Policy Bias,
    Private Market Opacity, Sovereign Industrial Compute, Jurisdictional
    Arbitrage, Trust Asset Failure, Energy Security. These are UNSCORED
    but the framework REQUIRES them and they inform the domain scores.
4.  Build the latent_pressure_table (>=3 rows from >=2 registry
    categories, all 8 questions answered per row) and capital_actor_table
    (>=2 rows).
5.  Score each domain using its rubric. Use evidence from steps 3-4 to
    justify scores.
6.  Audit kill conditions in kill_condition_check.
7.  Compute raw_total = sum of all 5 domain_total values.
8.  Compute applicable_cap from kill conditions, then
    master_score = round(min(raw_total, applicable_cap)).
9.  Map master_score to allocation_tier and capital_bucket.
10. Project Bull / Base / Bear scenarios (probabilities sum ~100).
11. Write key_thesis_statement (probabilistic, distinguishing
    observable / inductable / unknowable) and 3 primary_falsifiers.
12. Complete the 10-gap audit (gap_safeguards_audit) and signal_ranking.
13. Write the final executive_summary (synthesis only, no new claims).

============================================================================
DOMAIN I — FIVE TRUTH LAYERS (40 pts)
============================================================================

1A SUBSTRATE TRUTH (weight 1.0). Is the physical or social transformation
   this company operates within actually real and measurable from
   disclosed data? Score 0 = pure narrative; 10 = irreversible, fully
   quantified transformation provable in the filing. KILL: raw<=2 caps
   master at 40.

1B ECONOMIC CAPTURE TRUTH (weight 1.0). Can this company durably capture
   value from the transformation? Use disclosed gross margins, operating
   margins, pricing trends, customer concentration, and competitive moat
   disclosures. 0 = commodity / zero rent; 10 = near-monopolistic.

1C FINANCIAL SURVIVAL TRUTH (weight 1.0). Can this company survive a
   severe adverse financing environment? Evaluate net debt / EBITDA,
   interest coverage, free cash flow, debt maturity profile, disclosed
   liquidity. 0 = insolvency in mild stress; 10 = fortress / anti-fragile.
   KILL: raw<=2 caps master at 50. POPULATE financial_survival_ratios
   with the actual numbers from the filing.

1D VALUATION ENTRY TRUTH (weight 0.5). High score = thesis
   undercapitalized (favorable entry). Low score = crowded. If you do
   NOT have reliable market data beyond the 10-K, say so explicitly in
   valuation_context and score conservatively (typically 4-6). KILL:
   raw<=1 caps master at 60.

1E REFLEXIVE SYSTEM TRUTH (weight 0.5). Will capital flows into this
   sector reshape reality FOR or AGAINST the thesis? 0 = destructive
   reflexivity (overcapacity already forming); 10 = constructive
   feedback loop accelerating the transformation.

============================================================================
DOMAIN II — EPISTEMIC INTEGRITY (20 pts)
============================================================================

2A LATENT PRESSURE STAGE POSITIONING (weight 0.5). Where in the
   recognition cycle is the primary latent pressure driving the thesis?
   Stage 0 Ignored / 1 Niche / 2 Early capital / 3 Rerating /
   4 Consensus / 5 Crowded. High score = early stage. The Three Clocks
   divergence (physical vs narrative) IS the stage signal — if physical
   change is real but narrative is absent, score high.

2B EVIDENCE OBSERVABILITY (weight 0.5). What proportion of your claims
   about this company are directly observable in this 10-K versus
   inferred?

2C ANTI-HINDSIGHT INTEGRITY (weight 0.5). Does this analysis resist
   retrospective narrative construction? Populate ALL 7 fields of
   anti_hindsight_checklist. To score above 6, all 7 must be answered.
   To score above 7, historical_false_positives must contain real
   analogues with honest differentiation. INTEGRITY FLAG: raw<=1 marks
   the entire analysis structurally unreliable.

2D PRE-MORTEM DISCIPLINE (weight 0.5). Have all 8 failure categories
   been modeled? The schema requires ALL 8 fields of pre_mortem_scenarios
   to be present. To score above 6, kill_conditions in each scenario
   must be specific. To score above 7, decision_rule must be fully
   populated.

============================================================================
DOMAIN III — PHYSICAL REALITY ANCHOR (15 pts)
============================================================================

3A PHYSICALIZATION CONSTRAINT DEPTH (weight 0.5). How tightly is the
   company's capability constrained by physical bottlenecks (compute,
   power, materials, geography)? Score 0 for purely digital with no
   physical collision; 10 for hard physical ceilings owned by the
   company. For pure SaaS / pure services this may legitimately be 0-2 —
   that is correct, not a flaw.

3B POWER AND ENERGY POSITION (weight 0.5). Does the company control or
   uniquely benefit from critical power / energy constraints? Use
   disclosed PPAs, captive generation, geographic positioning. For
   companies with no special energy position, this is 0-2.

3C STRATEGIC SCARCITY QUALITY (weight 0.5). How durable and monetizable
   is the scarcity the company controls? Consider substitution risk,
   political pricing risk, contract structures.

============================================================================
DOMAIN IV — CAPITAL TOPOLOGY (10 pts)
============================================================================

4A CAPITAL CONCENTRATION ALIGNMENT (weight 0.5). Is large, concentrated,
   politically influential capital aligned with the thesis? Use
   disclosed beneficial ownership (10-K cover lists >5% holders and NEO
   ownership). Full institutional holder data is in DEF 14A / 13F (NOT
   in the 10-K) — if you don't have it, say so and score from what is
   in-filing.

4B INSTITUTIONAL CAPTURE FAVORABILITY (weight 0.5). Does the regulatory
   environment protect the company? Use Item 1 (Business — Regulation)
   and Item 1A (Risk Factors — Regulatory).

============================================================================
DOMAIN V — FRAGILITY PROFILE (15 pts)
============================================================================

5A LIQUIDITY INDEPENDENCE (weight 0.5). How independent is the business
   model from easy money? Use FCF yield, debt maturity, rate sensitivity
   disclosures, insider selling if visible.

5B SOVEREIGN AND TRUST STABILITY (weight 0.5). How exposed is the
   company to sovereign debt fragility or trust breakdown in its primary
   operating jurisdictions? Use geographic revenue concentration and
   government counterparty disclosures. For non-US companies the primary
   jurisdiction's sovereign rating may matter materially.

5C COMMODITIZATION RESISTANCE (weight 0.5). How resistant is the
   company to value destruction from competitive capex or technological
   commoditization? Use 3-year gross margin and ROIC trends; map to the
   Capex Arms Race diagnostic (offensive vs defensive capex).

============================================================================
EVIDENCE STANDARD (mandatory for every component)
============================================================================

Every ComponentScore object must include:
  - reasoning: explicit, citing specific 10-K disclosures
  - supporting_evidence: list of verifiable items from the filing
  - evidence_classification: one of
        Observable, Inductable, Weakly inferable, Hindsight only, Unknown

Be HONEST about what the 10-K does and does not show. If a component
requires data outside the 10-K (e.g. current multiple for 1D, full 13F
data for 4A) and you do not have it, say so explicitly and score
conservatively. Penalizing absent data is correct; inventing data is not.

============================================================================
EDGE CASE GUIDANCE
============================================================================

PRE-REVENUE / RECENT IPO: 3-year trends may be unavailable. Write
"insufficient history" for trend fields and score 1C and 5C conservatively
to reflect the uncertainty.

MULTI-SEGMENT / CONGLOMERATE: Think at the segment level where it
matters (different segments may have different moats, different physical
constraints). State which segment dominates the thesis.

INTERNATIONAL / NON-US FILER: 5B may carry more weight (sovereign
rating, currency risk). Geographic_revenue_concentration matters more.
Note the primary regulator (FCA, BaFin, etc.) if relevant for 4B.

REIT / BDC / BANK / INSURANCE: Standard ratios (gross margin) may not
apply. Use sector-appropriate analogs (NOI, NIM, combined ratio, book
value growth) and SAY SO in the reasoning.

HOLDING COMPANY / SPAC / SHELL: Note the structure explicitly. Score
1A based on the underlying assets, not the holding entity. 1C may be
strong (cash) but 1A may be weak (no operating substrate yet).

CONTROLLING SHAREHOLDER: 4A interpretation flips — concentrated
ownership by a long-horizon controlling shareholder is usually positive
(alignment, no short-term flow risk). Concentration by short-horizon
financial holders is usually negative (forced selling risk).

STATE-OWNED / QUASI-STATE: 4B is usually high (regulatory protection)
but 5B may be weak (sovereign dependency). Flag this trade-off.

ACTIVE M&A / RESTRUCTURING: One-time items distort trend analysis. Use
"organic / continuing operations" figures where the filing distinguishes.

============================================================================
DOCUMENT COMPLETENESS (CRITICAL METADATA)
============================================================================

Set document_completeness.full_doc to TRUE only if you were able to read
and use the ENTIRE 10-K. If any portion appeared truncated, missing,
garbled, or unreadable, set it to FALSE and list the missing or partial
sections explicitly. This metadata will be used by downstream systems to
decide whether to trust the analysis. A FALSE is not a failure — it is
honest reporting. A FALSE with a clear note is more useful than a
silently-incomplete TRUE.

============================================================================
REQUIRED TABLES AND LISTS — CARDINALITY
============================================================================

  - latent_pressure_table    >= 3 rows, from >= 2 registry categories
  - capital_actor_table      >= 2 rows
  - probabilistic_scenarios  exactly 3 (Bull, Base, Bear); probs sum ~100
  - primary_falsifiers       exactly 3 specific, future-observable signals
  - pre_mortem_scenarios     ALL 8 categories required (schema enforced)
  - anti_hindsight_checklist ALL 7 questions answered (schema enforced)
  - decision_rule            ALL 7 fields populated (schema enforced)
  - gap_safeguards_audit     ALL 10 gaps assessed (schema enforced)
  - signal_ranking.top_signals  3-5 signals from the 24-signal framework list

============================================================================
SCORE ARITHMETIC (do this carefully)
============================================================================

For each domain, set domain_total = sum of weighted_contribution across
its components. Then:

  raw_total = sum of all five domain_total values

  applicable_cap = min of {{40 if 1A<=2, 50 if 1C<=2, 60 if 1D<=1,
                            100 otherwise}}

  master_score = round(min(raw_total, applicable_cap))

The kill_condition_check object MUST be internally consistent with the
raw scores in the domain blocks. Inconsistency is an analyst error.

============================================================================
CHUNK LAWS (anchoring principles)
============================================================================

Keep these laws in mind while scoring — they prevent common failure modes:

  - Transformations can be correct but catastrophically overcapitalized.
  - Real expansions can become dangerous through unstable leverage.
  - Trust-dependent liquidity systems can fail nonlinearly.
  - Low rates push capital toward duration and scalable platforms.
  - Passive flows and network effects create reflexive concentration.
  - Essentiality does not equal pricing power when supply discipline
    collapses.
  - Continuity infrastructure rerates when normal coordination breaks.
  - When capital has a price again, optionality without cash flow
    reprices violently.
  - Digital capability becomes investable infrastructure when it collides
    with physical constraints.

============================================================================
TONE
============================================================================

Write probabilistically. Avoid inevitability language. When the 10-K
genuinely supports a strong claim, say so with the evidence. When it
does not, say so. The framework is designed to surface what you do not
know as clearly as what you do.

The Humility Principle is non-negotiable: every major claim should be
classifiable on the Real Time Evidence Standard (Observable / Inductable
/ Weakly inferable / Hindsight only / Unknown). If you find yourself
writing "obviously" or "clearly" anywhere, replace it with the actual
disclosed evidence.
"""

    @property
    def schema(self):
        return CSPPv26AnalysisResult
