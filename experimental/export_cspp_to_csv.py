#!/usr/bin/env python3
"""
Export CSPP v2.6 (Causal Substrate Propagation Protocol) analysis from a
batch to CSV. Works on in-progress batches — exports whatever results have
already been written, ignoring tickers still pending.

Deduplicates by keeping the most recent result per (ticker, fiscal_year,
filing_type).

Also merges FactSet Russell 1000 data (all columns prefixed with ``fs_``)
for every ticker found in the FactSet CSV.

Usage:
    python experimental/export_cspp_to_csv.py

Output:
    data/cspp_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
BATCH_NAME = "cspp russell 1000 - 21/05/2026"

# Path to FactSet Russell 1000 CSV (relative to project root).
# All columns except 'ticker' will be merged into the export prefixed with 'fs_'.
FACTSET_CSV = "factset_russell_1000_23052026.csv"

# Component codes in canonical CSPP order. Used to flatten the 19 nested
# ComponentScore objects scattered across the 5 domain dicts.
COMPONENT_CODES = [
    "1A", "1B", "1C", "1D", "1E",
    "2A", "2B", "2C", "2D",
    "3A", "3B", "3C",
    "4A", "4B", "4C",
    "5A", "5B", "5C", "5D",
]

# (domain_key_in_json, field_name_in_domain_dict) for each component code.
COMPONENT_LOCATION = {
    "1A": ("domain_i_five_truth_layers",          "substrate_truth_1A"),
    "1B": ("domain_i_five_truth_layers",          "economic_capture_truth_1B"),
    "1C": ("domain_i_five_truth_layers",          "financial_survival_truth_1C"),
    "1D": ("domain_i_five_truth_layers",          "valuation_entry_truth_1D"),
    "1E": ("domain_i_five_truth_layers",          "reflexive_system_truth_1E"),
    "2A": ("domain_ii_epistemic_integrity",       "latent_pressure_stage_2A"),
    "2B": ("domain_ii_epistemic_integrity",       "evidence_observability_2B"),
    "2C": ("domain_ii_epistemic_integrity",       "anti_hindsight_integrity_2C"),
    "2D": ("domain_ii_epistemic_integrity",       "pre_mortem_discipline_2D"),
    "3A": ("domain_iii_physical_reality_anchor",  "physicalization_constraint_3A"),
    "3B": ("domain_iii_physical_reality_anchor",  "power_and_energy_position_3B"),
    "3C": ("domain_iii_physical_reality_anchor",  "strategic_scarcity_3C"),
    "4A": ("domain_iv_capital_topology",          "capital_concentration_alignment_4A"),
    "4B": ("domain_iv_capital_topology",          "institutional_capture_favorability_4B"),
    "4C": ("domain_iv_capital_topology",          "hyper_mobile_capital_flow_4C"),
    "5A": ("domain_v_fragility_profile",          "liquidity_independence_5A"),
    "5B": ("domain_v_fragility_profile",          "sovereign_and_trust_stability_5B"),
    "5C": ("domain_v_fragility_profile",          "commoditization_resistance_5C"),
    "5D": ("domain_v_fragility_profile",          "cost_of_capital_reappearance_5D"),
}

PRE_MORTEM_CATEGORIES = [
    "technology", "financing", "economic_capture", "valuation",
    "policy", "substitution", "timing", "regulatory",
]


def _get(d, *keys, default=""):
    """Safe nested dict.get — returns default if any key in the path is missing."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


def _join(items):
    """Join list[str] with '; '. Tolerates None or non-list values."""
    if not items:
        return ""
    if not isinstance(items, list):
        return str(items)
    return "; ".join(str(x) for x in items)


def _load_factset(project_root: Path) -> tuple[list[str], dict[str, dict]]:
    """Load FactSet CSV and return (fs_fieldnames, lookup_by_ticker).

    fs_fieldnames — column names already prefixed with 'fs_' (ticker excluded).
    lookup_by_ticker — {ticker: {fs_col: value, ...}}
    """
    factset_path = project_root / FACTSET_CSV
    if not factset_path.exists():
        print(f"  Warning: FactSet CSV not found at {factset_path} — skipping merge.")
        return [], {}

    fs_fieldnames: list[str] = []
    lookup: dict[str, dict] = {}
    with open(factset_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        raw_cols = [c for c in (reader.fieldnames or []) if c != "ticker"]
        fs_fieldnames = [f"fs_{c}" for c in raw_cols]
        for row in reader:
            ticker = (row.get("ticker") or "").strip()
            if ticker:
                lookup[ticker] = {f"fs_{c}": row.get(c, "") for c in raw_cols}

    print(f"  FactSet: loaded {len(lookup)} tickers, {len(fs_fieldnames)} columns.")
    return fs_fieldnames, lookup


def export_cspp_to_csv():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    output_path = project_root / "data" / "cspp_export.csv"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT batch_id, name, total_tickers, completed_tickers, status "
        "FROM batch_jobs WHERE name = ?",
        (BATCH_NAME,),
    )
    batch_row = cursor.fetchone()
    if not batch_row:
        print(f"Batch '{BATCH_NAME}' not found.")
        conn.close()
        return

    batch_id, name, total, completed, status = batch_row
    print(f"Found batch: {name}")
    print(f"  Status: {status}")
    print(f"  Progress: {completed}/{total} tickers")

    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'CSPPv26AnalysisResult'
        ORDER BY ar.ticker, ar.fiscal_year DESC
        """,
        (batch_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No CSPP results found in this batch yet.")
        return

    # ── Load FactSet data ──────────────────────────────────────────────────
    fs_fieldnames, fs_lookup = _load_factset(project_root)

    # Dedupe: latest created_at wins per (ticker, fiscal_year, filing_type)
    seen = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        if key not in seen or row[4] > seen[key][4]:
            seen[key] = row
    deduped = sorted(seen.values(), key=lambda r: (r[0], -r[1]))
    print(f"\n  Total results: {len(rows)}")
    print(f"  Duplicates removed: {len(rows) - len(deduped)}")
    print(f"  Unique analyses: {len(deduped)}")

    # ── Build column list ──────────────────────────────────────────────────
    fieldnames = [
        # Meta
        "ticker", "fiscal_year", "filing_type", "created_at",
        "company_name", "primary_exchange",
        # Headline scores
        "master_score", "raw_total", "allocation_tier", "capital_bucket",
        "analysis_partial", "failed_call",
        # Kill condition check
        "cap_1A_substrate_triggered", "cap_1C_survival_triggered",
        "cap_1D_valuation_triggered", "integrity_flag_2C_triggered",
        "applicable_cap",
        # AI infrastructure
        "ai_infrastructure_relevant",
        "ai_score_adjustment_3A", "ai_score_adjustment_3B", "ai_score_adjustment_3C",
        "ai_adjustment_rationale",
        # Document completeness
        "full_doc", "sections_missing_or_partial", "completeness_note",
        # Thesis classification
        "thesis_primary_track", "thesis_types", "classification_rationale",
        "primary_thesis", "key_thesis_statement",
        # Three Clocks
        "three_clocks_physical", "three_clocks_financial",
        "three_clocks_narrative", "three_clocks_divergence",
        # Chunk laws
        "chunk_laws_triggered",
        # Domain totals
        "domain_i_total", "domain_ii_total", "domain_iii_total",
        "domain_iv_total", "domain_v_total",
        # Stage classification (Domain II context)
        "primary_latent_pressure", "estimated_stage",
    ]

    # 19 components × 3 columns (raw_score, evidence_classification, kill_triggered)
    for code in COMPONENT_CODES:
        fieldnames += [
            f"score_{code}_raw",
            f"score_{code}_evidence",
            f"score_{code}_kill_triggered",
        ]

    fieldnames += [
        # Domain I supporting context
        "net_debt_to_ebitda", "interest_coverage", "fcf_yield",
        "nearest_debt_maturity", "liquidity_buffer",
        "current_multiple", "peer_multiple_range",
        "analyst_coverage_skew", "valuation_stage_implication",
        # Domain III supporting context
        "primary_physical_constraint", "capex_to_revenue_pct",
        "disclosed_energy_agreements", "scarcity_type", "substitution_risks",
        # Domain IV supporting context
        "largest_disclosed_holders", "insider_ownership_pct",
        "institutional_ownership_signal", "key_regulatory_disclosures",
        "government_revenue_pct", "capital_mobility_profile",
        # Domain V supporting context
        "geographic_revenue_concentration", "gross_margin_trend_3yr",
        "roic_trend_3yr", "primary_commoditization_risk",
        "rate_sensitivity_profile",
        # Module diagnostics (9 notes)
        "diag_bottleneck_inflation", "diag_continuity_infrastructure",
        "diag_capex_arms_race", "diag_asset_holder_policy",
        "diag_private_market_opacity", "diag_sovereign_industrial_compute",
        "diag_jurisdictional_arbitrage", "diag_trust_asset_failure",
        "diag_energy_security",
        # Probabilistic scenarios (Bull/Base/Bear)
        "bull_probability_pct", "bull_outcome", "bull_narrative",
        "base_probability_pct", "base_outcome", "base_narrative",
        "bear_probability_pct", "bear_outcome", "bear_narrative",
    ]

    # 8 pre-mortem categories × 2 columns
    for cat in PRE_MORTEM_CATEGORIES:
        fieldnames += [
            f"premortem_{cat}_prob_pct",
            f"premortem_{cat}_failure_mode",
        ]

    fieldnames += [
        # Anti-hindsight (highlights)
        "ah_contradicting_signals", "ah_likely_blind_spots",
        "ah_historical_false_positives",
        # Primary falsifiers
        "primary_falsifiers",
        # Signal ranking
        "top_signals", "signal_ranking_rationale",
        # Gap safeguards audit (10 notes)
        "gap_quantification", "gap_branch_control", "gap_narrative_psychology",
        "gap_reflexivity", "gap_institutional_power", "gap_substitution_systems",
        "gap_topology_analysis", "gap_temporal_dynamics", "gap_market_structure",
        "gap_civilization_hierarchy",
        # Decision rule
        "dr_entry_conditions", "dr_evidence_thresholds",
        "dr_position_sizing_guidance", "dr_kill_conditions",
        "dr_valuation_discipline", "dr_survivability_assumptions",
        "dr_monitoring_signals",
        # Counts of underlying tables (deep contents not flattened)
        "latent_pressure_count", "capital_actor_count",
        # Executive summary
        "executive_summary",
    ]

    # Append FactSet columns (prefixed with 'fs_') after all CSPP columns
    fieldnames += fs_fieldnames

    # ── Build rows ─────────────────────────────────────────────────────────
    csv_rows = []
    parse_errors = 0
    for ticker, fiscal_year, filing_type, result_json, created_at in deduped:
        try:
            d = json.loads(result_json)
        except json.JSONDecodeError:
            parse_errors += 1
            print(f"  Warning: could not parse JSON for {ticker} {fiscal_year}")
            continue

        # Scenarios — map by name
        scenarios = {s.get("name"): s for s in d.get("probabilistic_scenarios", []) if isinstance(s, dict)}
        bull = scenarios.get("Bull", {})
        base = scenarios.get("Base", {})
        bear = scenarios.get("Bear", {})

        ai = d.get("ai_infrastructure_analysis") or {}

        domain_i = d.get("domain_i_five_truth_layers", {})
        domain_ii = d.get("domain_ii_epistemic_integrity", {})
        domain_iii = d.get("domain_iii_physical_reality_anchor", {})
        domain_iv = d.get("domain_iv_capital_topology", {})
        domain_v = d.get("domain_v_fragility_profile", {})

        fin_ratios = domain_i.get("financial_survival_ratios", {})
        val_ctx = domain_i.get("valuation_context", {})
        diag = d.get("module_diagnostics", {})
        clocks = diag.get("three_clocks", {})
        thesis = d.get("thesis_classification", {})
        doc = d.get("document_completeness", {})
        kill = d.get("kill_condition_check", {})
        gap = d.get("gap_safeguards_audit", {})
        sig = d.get("signal_ranking", {})
        dr = _get(domain_ii, "decision_rule", default={})
        ah = _get(domain_ii, "anti_hindsight_checklist", default={})
        pm = _get(domain_ii, "pre_mortem_scenarios", default={})

        row = {
            # Meta
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            "created_at": created_at,
            "company_name": d.get("company_name", ""),
            "primary_exchange": d.get("primary_exchange", ""),
            # Headline
            "master_score": d.get("master_score", ""),
            "raw_total": d.get("raw_total", ""),
            "allocation_tier": d.get("allocation_tier", ""),
            "capital_bucket": d.get("capital_bucket", ""),
            "analysis_partial": d.get("analysis_partial", ""),
            "failed_call": d.get("failed_call", "") or "",
            # Kill condition check
            "cap_1A_substrate_triggered": kill.get("cap_1A_substrate_triggered", ""),
            "cap_1C_survival_triggered": kill.get("cap_1C_survival_triggered", ""),
            "cap_1D_valuation_triggered": kill.get("cap_1D_valuation_triggered", ""),
            "integrity_flag_2C_triggered": kill.get("integrity_flag_2C_triggered", ""),
            "applicable_cap": kill.get("applicable_cap", ""),
            # AI infra
            "ai_infrastructure_relevant": d.get("ai_infrastructure_relevant", False),
            "ai_score_adjustment_3A": ai.get("score_adjustment_3A", "") if ai else "",
            "ai_score_adjustment_3B": ai.get("score_adjustment_3B", "") if ai else "",
            "ai_score_adjustment_3C": ai.get("score_adjustment_3C", "") if ai else "",
            "ai_adjustment_rationale": ai.get("adjustment_rationale", "") if ai else "",
            # Doc completeness
            "full_doc": doc.get("full_doc", ""),
            "sections_missing_or_partial": _join(doc.get("sections_missing_or_partial", [])),
            "completeness_note": doc.get("completeness_note", ""),
            # Thesis classification
            "thesis_primary_track": thesis.get("primary_track", ""),
            "thesis_types": _join(thesis.get("thesis_types", [])),
            "classification_rationale": thesis.get("classification_rationale", ""),
            "primary_thesis": d.get("primary_thesis", ""),
            "key_thesis_statement": d.get("key_thesis_statement", ""),
            # Three clocks
            "three_clocks_physical": clocks.get("physical_clock_state", ""),
            "three_clocks_financial": clocks.get("financial_clock_state", ""),
            "three_clocks_narrative": clocks.get("narrative_clock_state", ""),
            "three_clocks_divergence": clocks.get("clock_divergence_assessment", ""),
            # Chunk laws
            "chunk_laws_triggered": _join(d.get("chunk_laws_triggered", [])),
            # Domain totals
            "domain_i_total": domain_i.get("domain_total", ""),
            "domain_ii_total": domain_ii.get("domain_total", ""),
            "domain_iii_total": domain_iii.get("domain_total", ""),
            "domain_iv_total": domain_iv.get("domain_total", ""),
            "domain_v_total": domain_v.get("domain_total", ""),
            # Stage classification
            "primary_latent_pressure": domain_ii.get("primary_latent_pressure", ""),
            "estimated_stage": domain_ii.get("estimated_stage", ""),
            # Domain I supporting
            "net_debt_to_ebitda": fin_ratios.get("net_debt_to_ebitda", ""),
            "interest_coverage": fin_ratios.get("interest_coverage", ""),
            "fcf_yield": fin_ratios.get("fcf_yield", ""),
            "nearest_debt_maturity": fin_ratios.get("nearest_debt_maturity", ""),
            "liquidity_buffer": fin_ratios.get("liquidity_buffer", ""),
            "current_multiple": val_ctx.get("current_multiple", ""),
            "peer_multiple_range": val_ctx.get("peer_multiple_range", ""),
            "analyst_coverage_skew": val_ctx.get("analyst_coverage_skew", ""),
            "valuation_stage_implication": val_ctx.get("stage_implication", ""),
            # Domain III supporting
            "primary_physical_constraint": domain_iii.get("primary_physical_constraint", ""),
            "capex_to_revenue_pct": domain_iii.get("capex_to_revenue_pct", ""),
            "disclosed_energy_agreements": _join(domain_iii.get("disclosed_energy_agreements", [])),
            "scarcity_type": domain_iii.get("scarcity_type", ""),
            "substitution_risks": _join(domain_iii.get("substitution_risks", [])),
            # Domain IV supporting
            "largest_disclosed_holders": _join(domain_iv.get("largest_disclosed_holders", [])),
            "insider_ownership_pct": domain_iv.get("insider_ownership_pct", ""),
            "institutional_ownership_signal": domain_iv.get("institutional_ownership_signal", ""),
            "key_regulatory_disclosures": _join(domain_iv.get("key_regulatory_disclosures", [])),
            "government_revenue_pct": domain_iv.get("government_revenue_pct", ""),
            "capital_mobility_profile": domain_iv.get("capital_mobility_profile", ""),
            # Domain V supporting
            "geographic_revenue_concentration": domain_v.get("geographic_revenue_concentration", ""),
            "gross_margin_trend_3yr": domain_v.get("gross_margin_trend_3yr", ""),
            "roic_trend_3yr": domain_v.get("roic_trend_3yr", ""),
            "primary_commoditization_risk": domain_v.get("primary_commoditization_risk", ""),
            "rate_sensitivity_profile": domain_v.get("rate_sensitivity_profile", ""),
            # Module diagnostics
            "diag_bottleneck_inflation": diag.get("bottleneck_inflation_note", ""),
            "diag_continuity_infrastructure": diag.get("continuity_infrastructure_note", ""),
            "diag_capex_arms_race": diag.get("capex_arms_race_note", ""),
            "diag_asset_holder_policy": diag.get("asset_holder_policy_bias_note", ""),
            "diag_private_market_opacity": diag.get("private_market_opacity_note", ""),
            "diag_sovereign_industrial_compute": diag.get("sovereign_industrial_compute_note", ""),
            "diag_jurisdictional_arbitrage": diag.get("jurisdictional_arbitrage_note", ""),
            "diag_trust_asset_failure": diag.get("trust_asset_failure_note", ""),
            "diag_energy_security": diag.get("energy_security_note", ""),
            # Scenarios
            "bull_probability_pct": bull.get("probability_pct", ""),
            "bull_outcome": bull.get("price_target_or_outcome", ""),
            "bull_narrative": bull.get("narrative", ""),
            "base_probability_pct": base.get("probability_pct", ""),
            "base_outcome": base.get("price_target_or_outcome", ""),
            "base_narrative": base.get("narrative", ""),
            "bear_probability_pct": bear.get("probability_pct", ""),
            "bear_outcome": bear.get("price_target_or_outcome", ""),
            "bear_narrative": bear.get("narrative", ""),
            # Anti-hindsight highlights
            "ah_contradicting_signals": _join(ah.get("contradicting_signals", [])),
            "ah_likely_blind_spots": _join(ah.get("likely_blind_spots", [])),
            "ah_historical_false_positives": _join(ah.get("historical_false_positives", [])),
            # Primary falsifiers
            "primary_falsifiers": _join(d.get("primary_falsifiers", [])),
            # Signal ranking
            "top_signals": _join(sig.get("top_signals", [])),
            "signal_ranking_rationale": sig.get("ranking_rationale", ""),
            # Gap audit
            "gap_quantification": gap.get("gap_1_quantification", ""),
            "gap_branch_control": gap.get("gap_2_branch_control", ""),
            "gap_narrative_psychology": gap.get("gap_3_narrative_psychology", ""),
            "gap_reflexivity": gap.get("gap_4_reflexivity", ""),
            "gap_institutional_power": gap.get("gap_5_institutional_power", ""),
            "gap_substitution_systems": gap.get("gap_6_substitution_systems", ""),
            "gap_topology_analysis": gap.get("gap_7_topology_analysis", ""),
            "gap_temporal_dynamics": gap.get("gap_8_temporal_dynamics", ""),
            "gap_market_structure": gap.get("gap_9_market_structure", ""),
            "gap_civilization_hierarchy": gap.get("gap_10_civilization_hierarchy", ""),
            # Decision rule
            "dr_entry_conditions": dr.get("entry_conditions", ""),
            "dr_evidence_thresholds": dr.get("evidence_thresholds", ""),
            "dr_position_sizing_guidance": dr.get("position_sizing_guidance", ""),
            "dr_kill_conditions": dr.get("kill_conditions", ""),
            "dr_valuation_discipline": dr.get("valuation_discipline", ""),
            "dr_survivability_assumptions": dr.get("survivability_assumptions", ""),
            "dr_monitoring_signals": _join(dr.get("monitoring_signals", [])),
            # Table counts
            "latent_pressure_count": len(d.get("latent_pressure_table", []) or []),
            "capital_actor_count": len(d.get("capital_actor_table", []) or []),
            # Executive summary
            "executive_summary": d.get("executive_summary", ""),
        }

        # 19 component scores
        for code in COMPONENT_CODES:
            domain_key, field_name = COMPONENT_LOCATION[code]
            comp = _get(d, domain_key, field_name, default={})
            row[f"score_{code}_raw"] = comp.get("raw_score", "") if isinstance(comp, dict) else ""
            row[f"score_{code}_evidence"] = comp.get("evidence_classification", "") if isinstance(comp, dict) else ""
            row[f"score_{code}_kill_triggered"] = comp.get("kill_condition_triggered", "") if isinstance(comp, dict) else ""

        # 8 pre-mortem scenarios
        for cat in PRE_MORTEM_CATEGORIES:
            scen = pm.get(cat, {}) if isinstance(pm, dict) else {}
            row[f"premortem_{cat}_prob_pct"] = scen.get("probability_pct", "") if isinstance(scen, dict) else ""
            row[f"premortem_{cat}_failure_mode"] = scen.get("failure_mode", "") if isinstance(scen, dict) else ""

        # Merge FactSet columns — blank if ticker not found in FactSet
        fs_data = fs_lookup.get(ticker, {})
        for fs_col in fs_fieldnames:
            row[fs_col] = fs_data.get(fs_col, "")

        csv_rows.append(row)

    # ── Write CSV ──────────────────────────────────────────────────────────
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nExported {len(csv_rows)} analyses to: {output_path}")
    print(f"  Columns: {len(fieldnames)}")
    if parse_errors:
        print(f"  JSON parse errors skipped: {parse_errors}")

    # ── Quick summary ──────────────────────────────────────────────────────
    if csv_rows:
        scores = [r["master_score"] for r in csv_rows if isinstance(r["master_score"], int)]
        if scores:
            print(f"\n--- Master Score Summary ---")
            print(f"  Count: {len(scores)}  min: {min(scores)}  max: {max(scores)}  mean: {sum(scores)/len(scores):.1f}")
            ge70 = sum(1 for s in scores if s >= 70)
            ge55 = sum(1 for s in scores if s >= 55)
            print(f"  Master score >=70 (high conviction): {ge70}")
            print(f"  Master score >=55 (moderate+):       {ge55}")
        partials = sum(1 for r in csv_rows if r.get("analysis_partial"))
        if partials:
            print(f"\n  Partial analyses (one or more sub-calls failed): {partials}")
        ai_count = sum(1 for r in csv_rows if r.get("ai_infrastructure_relevant"))
        print(f"  AI-infrastructure flagged: {ai_count}")


if __name__ == "__main__":
    export_cspp_to_csv()
