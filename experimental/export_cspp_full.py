#!/usr/bin/env python3
"""
Full CSPP export — pulls from the original Russell 1000 batch plus both
re-run batches (10-K domestic and 20-F foreign), deduplicates across all
three by keeping the most recent result per (ticker, fiscal_year, filing_type),
and writes a single combined CSV.

Batches included:
  7167deb5  cspp russell 1000 - 21/05/2026          (original)
  c2de71c5  cspp russell 1000 - rerun 10K domestic   (ghost-completed + quota failures + BNY + dot-ticker fixes)
  0ebb2480  cspp russell 1000 - rerun 20F foreign     (AS, AU, BEPC, BIRK, BLSH, DOX, GFS, GLOB, NU, ONON, QGEN, SPOT, TIGO, VIK, XP)
"""

import csv
import json
import sqlite3
from pathlib import Path


BATCH_IDS = [
    "7167deb5-a81b-48cd-8f06-7d0d56c3c1b4",  # original
    "c2de71c5-af6d-44f1-bd55-075f4cced4f9",  # 10-K domestic rerun
    "0ebb2480-08a5-4740-8f16-6c54ba98a356",  # 20-F foreign rerun
]

FACTSET_CSV = "factset_russell_1000_23052026.csv"

COMPONENT_CODES = [
    "1A", "1B", "1C", "1D", "1E",
    "2A", "2B", "2C", "2D",
    "3A", "3B", "3C",
    "4A", "4B", "4C",
    "5A", "5B", "5C", "5D",
]

COMPONENT_LOCATION = {
    "1A": ("domain_i_five_truth_layers", "substrate_truth_1A"),
    "1B": ("domain_i_five_truth_layers", "economic_capture_truth_1B"),
    "1C": ("domain_i_five_truth_layers", "financial_survival_truth_1C"),
    "1D": ("domain_i_five_truth_layers", "valuation_entry_truth_1D"),
    "1E": ("domain_i_five_truth_layers", "reflexive_system_truth_1E"),
    "2A": ("domain_ii_epistemic_integrity", "latent_pressure_stage_2A"),
    "2B": ("domain_ii_epistemic_integrity", "evidence_observability_2B"),
    "2C": ("domain_ii_epistemic_integrity", "anti_hindsight_integrity_2C"),
    "2D": ("domain_ii_epistemic_integrity", "pre_mortem_discipline_2D"),
    "3A": ("domain_iii_physical_reality_anchor", "physicalization_constraint_3A"),
    "3B": ("domain_iii_physical_reality_anchor", "power_and_energy_position_3B"),
    "3C": ("domain_iii_physical_reality_anchor", "strategic_scarcity_3C"),
    "4A": ("domain_iv_capital_topology", "capital_concentration_alignment_4A"),
    "4B": ("domain_iv_capital_topology", "institutional_capture_favorability_4B"),
    "4C": ("domain_iv_capital_topology", "hyper_mobile_capital_flow_4C"),
    "5A": ("domain_v_fragility_profile", "liquidity_independence_5A"),
    "5B": ("domain_v_fragility_profile", "sovereign_and_trust_stability_5B"),
    "5C": ("domain_v_fragility_profile", "commoditization_resistance_5C"),
    "5D": ("domain_v_fragility_profile", "cost_of_capital_reappearance_5D"),
}

PRE_MORTEM_CATEGORIES = [
    "technology", "financing", "economic_capture", "valuation",
    "policy", "substitution", "timing", "regulatory",
]

UPDATED_COMPONENT_WEIGHTS = {
    "1A": 12, "1B": 12, "1C": 10, "1D": 10, "1E": 4,
    "2A": 12, "2B": 4,  "2C": 6,  "2D": 4,
    "3A": 7,  "3B": 5,  "3C": 7,
    "4A": 3,  "4B": 4,  "4C": 4,
    "5A": 6,  "5B": 5,  "5C": 8,  "5D": 7,
}


def _get(d, *keys, default=""):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


def _join(items):
    if not items:
        return ""
    if not isinstance(items, list):
        return str(items)
    return "; ".join(str(x) for x in items)


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _updated_tier(score):
    if score >= 85:
        return "Rare exceptional"
    if score >= 75:
        return "Strong candidate"
    if score >= 65:
        return "Worth diligence"
    if score >= 50:
        return "Average or watchlist"
    if score >= 35:
        return "Weak candidate"
    return "Avoid"


def _stage_cap(estimated_stage):
    stage = (estimated_stage or "").lower()
    if "stage 5" in stage:
        return 60
    if "stage 4" in stage:
        return 68
    if "stage 3" in stage:
        return 82
    return 100


def _compute_updated_score(row):
    total_weight = sum(UPDATED_COMPONENT_WEIGHTS.values())
    weighted_points = 0.0
    raw_scores = {}

    for code, weight in UPDATED_COMPONENT_WEIGHTS.items():
        score = _to_float(row.get(f"score_{code}_raw"), default=0.0)
        raw_scores[code] = score
        weighted_points += (score / 10.0) * weight

    updated_score = (weighted_points / total_weight) * 100.0
    notes = []

    high_count = sum(1 for score in raw_scores.values() if score >= 8)
    elite_count = high_count
    very_elite_count = sum(1 for score in raw_scores.values() if score >= 9)
    weak_count = sum(1 for score in raw_scores.values() if score <= 4)
    very_weak_count = sum(1 for score in raw_scores.values() if score <= 3)

    if high_count == 0:
        updated_score -= 10
        notes.append("mediocrity penalty: no component scored 8 or above")
    elif high_count <= 2:
        updated_score -= 6
        notes.append("mediocrity penalty: too few standout strengths")
    elif high_count <= 4:
        updated_score -= 3
        notes.append("mild mediocrity penalty")

    if elite_count >= 7:
        updated_score += 5
        notes.append("elite bonus: seven or more components scored 8 or above")
    elif elite_count >= 5:
        updated_score += 3
        notes.append("elite bonus: five or more components scored 8 or above")

    if very_elite_count >= 3:
        updated_score += 3
        notes.append("exceptional strength bonus: three or more components scored 9 or above")

    if _to_bool(row.get("analysis_partial")):
        updated_score -= 8
        notes.append("partial analysis penalty")

    if not _to_bool(row.get("full_doc")):
        updated_score -= 5
        notes.append("incomplete filing penalty")

    applicable_cap = _to_float(row.get("applicable_cap"), default=100)
    if applicable_cap > 0:
        updated_score = min(updated_score, applicable_cap)

    cap = _stage_cap(row.get("estimated_stage", ""))
    if cap < 100:
        updated_score = min(updated_score, cap)
        notes.append(f"stage cap applied: {cap}")

    if very_weak_count >= 4:
        updated_score = min(updated_score, 45)
        notes.append("weakness cluster cap: four or more very weak components")
    elif weak_count >= 6:
        updated_score = min(updated_score, 55)
        notes.append("weakness cluster cap: six or more weak components")
    elif weak_count >= 4:
        updated_score = min(updated_score, 65)
        notes.append("weakness cluster cap: four or more weak components")

    if updated_score >= 85:
        required = ["1A", "1B", "1C", "2A", "5C"]
        if any(raw_scores.get(code, 0) < 8 for code in required):
            updated_score = 84
            notes.append("exceptional gate: core pillars below 8")

    if updated_score >= 75:
        if raw_scores.get("1A", 0) < 6 or raw_scores.get("1B", 0) < 6 or raw_scores.get("1C", 0) < 6:
            updated_score = 74
            notes.append("strong candidate gate: truth layer below 6")
        if raw_scores.get("1D", 0) < 4:
            updated_score = 74
            notes.append("strong candidate gate: valuation entry below 4")

    final_score = int(round(max(0, min(100, updated_score))))

    if not notes:
        notes.append("no extra penalty or cap applied")

    return final_score, _updated_tier(final_score), "; ".join(notes)


def _load_factset(project_root):
    factset_path = project_root / FACTSET_CSV
    if not factset_path.exists():
        print(f"  Warning: FactSet CSV not found at {factset_path}. Skipping merge.")
        return [], {}

    fs_fieldnames = []
    lookup = {}

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


def export_cspp_full():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    output_path = project_root / "data" / "cspp_export_full.csv"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Report on each batch
    all_rows = []
    for batch_id in BATCH_IDS:
        cursor.execute(
            "SELECT batch_id, name, total_tickers, completed_tickers, status "
            "FROM batch_jobs WHERE batch_id = ?",
            (batch_id,),
        )
        batch_row = cursor.fetchone()

        if not batch_row:
            print(f"  Batch {batch_id[:8]}... not found — skipping.")
            continue

        _, name, total, completed, status = batch_row
        print(f"Batch: {name}")
        print(f"  Status: {status}  |  Progress: {completed}/{total} tickers")

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
        batch_rows = cursor.fetchall()
        print(f"  Results found: {len(batch_rows)}")
        all_rows.extend(batch_rows)

    conn.close()

    if not all_rows:
        print("\nNo CSPP results found across any batch.")
        return

    fs_fieldnames, fs_lookup = _load_factset(project_root)

    # Deduplicate across all batches: keep most recent created_at per (ticker, fiscal_year, filing_type)
    seen = {}
    for row in all_rows:
        key = (row[0], row[1], row[2])
        if key not in seen or row[4] > seen[key][4]:
            seen[key] = row

    deduped = sorted(seen.values(), key=lambda r: (r[0], -r[1]))

    print("")
    print(f"  Total results across all batches: {len(all_rows)}")
    print(f"  Duplicates removed: {len(all_rows) - len(deduped)}")
    print(f"  Unique analyses: {len(deduped)}")

    fieldnames = [
        "ticker", "fiscal_year", "filing_type", "created_at",
        "company_name", "primary_exchange",
        "master_score", "updated_score", "updated_tier", "updated_score_notes",
        "raw_total", "allocation_tier", "capital_bucket",
        "analysis_partial", "failed_call",
        "cap_1A_substrate_triggered", "cap_1C_survival_triggered",
        "cap_1D_valuation_triggered", "integrity_flag_2C_triggered",
        "applicable_cap",
        "ai_infrastructure_relevant",
        "ai_score_adjustment_3A", "ai_score_adjustment_3B", "ai_score_adjustment_3C",
        "ai_adjustment_rationale",
        "full_doc", "sections_missing_or_partial", "completeness_note",
        "thesis_primary_track", "thesis_types", "classification_rationale",
        "primary_thesis", "key_thesis_statement",
        "three_clocks_physical", "three_clocks_financial",
        "three_clocks_narrative", "three_clocks_divergence",
        "chunk_laws_triggered",
        "domain_i_total", "domain_ii_total", "domain_iii_total",
        "domain_iv_total", "domain_v_total",
        "primary_latent_pressure", "estimated_stage",
    ]

    for code in COMPONENT_CODES:
        fieldnames += [
            f"score_{code}_raw",
            f"score_{code}_evidence",
            f"score_{code}_kill_triggered",
        ]

    fieldnames += [
        "net_debt_to_ebitda", "interest_coverage", "fcf_yield",
        "nearest_debt_maturity", "liquidity_buffer",
        "current_multiple", "peer_multiple_range",
        "analyst_coverage_skew", "valuation_stage_implication",
        "primary_physical_constraint", "capex_to_revenue_pct",
        "disclosed_energy_agreements", "scarcity_type", "substitution_risks",
        "largest_disclosed_holders", "insider_ownership_pct",
        "institutional_ownership_signal", "key_regulatory_disclosures",
        "government_revenue_pct", "capital_mobility_profile",
        "geographic_revenue_concentration", "gross_margin_trend_3yr",
        "roic_trend_3yr", "primary_commoditization_risk",
        "rate_sensitivity_profile",
        "diag_bottleneck_inflation", "diag_continuity_infrastructure",
        "diag_capex_arms_race", "diag_asset_holder_policy",
        "diag_private_market_opacity", "diag_sovereign_industrial_compute",
        "diag_jurisdictional_arbitrage", "diag_trust_asset_failure",
        "diag_energy_security",
        "bull_probability_pct", "bull_outcome", "bull_narrative",
        "base_probability_pct", "base_outcome", "base_narrative",
        "bear_probability_pct", "bear_outcome", "bear_narrative",
    ]

    for cat in PRE_MORTEM_CATEGORIES:
        fieldnames += [
            f"premortem_{cat}_prob_pct",
            f"premortem_{cat}_failure_mode",
        ]

    fieldnames += [
        "ah_contradicting_signals", "ah_likely_blind_spots",
        "ah_historical_false_positives",
        "primary_falsifiers",
        "top_signals", "signal_ranking_rationale",
        "gap_quantification", "gap_branch_control", "gap_narrative_psychology",
        "gap_reflexivity", "gap_institutional_power", "gap_substitution_systems",
        "gap_topology_analysis", "gap_temporal_dynamics", "gap_market_structure",
        "gap_civilization_hierarchy",
        "dr_entry_conditions", "dr_evidence_thresholds",
        "dr_position_sizing_guidance", "dr_kill_conditions",
        "dr_valuation_discipline", "dr_survivability_assumptions",
        "dr_monitoring_signals",
        "latent_pressure_count", "capital_actor_count",
        "executive_summary",
    ]

    fieldnames += fs_fieldnames

    csv_rows = []
    parse_errors = 0

    for ticker, fiscal_year, filing_type, result_json, created_at in deduped:
        try:
            d = json.loads(result_json)
        except json.JSONDecodeError:
            parse_errors += 1
            print(f"  Warning: could not parse JSON for {ticker} {fiscal_year}")
            continue

        scenarios = {
            s.get("name"): s
            for s in d.get("probabilistic_scenarios", [])
            if isinstance(s, dict)
        }

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
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            "created_at": created_at,
            "company_name": d.get("company_name", ""),
            "primary_exchange": d.get("primary_exchange", ""),
            "master_score": d.get("master_score", ""),
            "updated_score": "",
            "updated_tier": "",
            "updated_score_notes": "",
            "raw_total": d.get("raw_total", ""),
            "allocation_tier": d.get("allocation_tier", ""),
            "capital_bucket": d.get("capital_bucket", ""),
            "analysis_partial": d.get("analysis_partial", ""),
            "failed_call": d.get("failed_call", "") or "",
            "cap_1A_substrate_triggered": kill.get("cap_1A_substrate_triggered", ""),
            "cap_1C_survival_triggered": kill.get("cap_1C_survival_triggered", ""),
            "cap_1D_valuation_triggered": kill.get("cap_1D_valuation_triggered", ""),
            "integrity_flag_2C_triggered": kill.get("integrity_flag_2C_triggered", ""),
            "applicable_cap": kill.get("applicable_cap", ""),
            "ai_infrastructure_relevant": d.get("ai_infrastructure_relevant", False),
            "ai_score_adjustment_3A": ai.get("score_adjustment_3A", "") if ai else "",
            "ai_score_adjustment_3B": ai.get("score_adjustment_3B", "") if ai else "",
            "ai_score_adjustment_3C": ai.get("score_adjustment_3C", "") if ai else "",
            "ai_adjustment_rationale": ai.get("adjustment_rationale", "") if ai else "",
            "full_doc": doc.get("full_doc", ""),
            "sections_missing_or_partial": _join(doc.get("sections_missing_or_partial", [])),
            "completeness_note": doc.get("completeness_note", ""),
            "thesis_primary_track": thesis.get("primary_track", ""),
            "thesis_types": _join(thesis.get("thesis_types", [])),
            "classification_rationale": thesis.get("classification_rationale", ""),
            "primary_thesis": d.get("primary_thesis", ""),
            "key_thesis_statement": d.get("key_thesis_statement", ""),
            "three_clocks_physical": clocks.get("physical_clock_state", ""),
            "three_clocks_financial": clocks.get("financial_clock_state", ""),
            "three_clocks_narrative": clocks.get("narrative_clock_state", ""),
            "three_clocks_divergence": clocks.get("clock_divergence_assessment", ""),
            "chunk_laws_triggered": _join(d.get("chunk_laws_triggered", [])),
            "domain_i_total": domain_i.get("domain_total", ""),
            "domain_ii_total": domain_ii.get("domain_total", ""),
            "domain_iii_total": domain_iii.get("domain_total", ""),
            "domain_iv_total": domain_iv.get("domain_total", ""),
            "domain_v_total": domain_v.get("domain_total", ""),
            "primary_latent_pressure": domain_ii.get("primary_latent_pressure", ""),
            "estimated_stage": domain_ii.get("estimated_stage", ""),
            "net_debt_to_ebitda": fin_ratios.get("net_debt_to_ebitda", ""),
            "interest_coverage": fin_ratios.get("interest_coverage", ""),
            "fcf_yield": fin_ratios.get("fcf_yield", ""),
            "nearest_debt_maturity": fin_ratios.get("nearest_debt_maturity", ""),
            "liquidity_buffer": fin_ratios.get("liquidity_buffer", ""),
            "current_multiple": val_ctx.get("current_multiple", ""),
            "peer_multiple_range": val_ctx.get("peer_multiple_range", ""),
            "analyst_coverage_skew": val_ctx.get("analyst_coverage_skew", ""),
            "valuation_stage_implication": val_ctx.get("stage_implication", ""),
            "primary_physical_constraint": domain_iii.get("primary_physical_constraint", ""),
            "capex_to_revenue_pct": domain_iii.get("capex_to_revenue_pct", ""),
            "disclosed_energy_agreements": _join(domain_iii.get("disclosed_energy_agreements", [])),
            "scarcity_type": domain_iii.get("scarcity_type", ""),
            "substitution_risks": _join(domain_iii.get("substitution_risks", [])),
            "largest_disclosed_holders": _join(domain_iv.get("largest_disclosed_holders", [])),
            "insider_ownership_pct": domain_iv.get("insider_ownership_pct", ""),
            "institutional_ownership_signal": domain_iv.get("institutional_ownership_signal", ""),
            "key_regulatory_disclosures": _join(domain_iv.get("key_regulatory_disclosures", [])),
            "government_revenue_pct": domain_iv.get("government_revenue_pct", ""),
            "capital_mobility_profile": domain_iv.get("capital_mobility_profile", ""),
            "geographic_revenue_concentration": domain_v.get("geographic_revenue_concentration", ""),
            "gross_margin_trend_3yr": domain_v.get("gross_margin_trend_3yr", ""),
            "roic_trend_3yr": domain_v.get("roic_trend_3yr", ""),
            "primary_commoditization_risk": domain_v.get("primary_commoditization_risk", ""),
            "rate_sensitivity_profile": domain_v.get("rate_sensitivity_profile", ""),
            "diag_bottleneck_inflation": diag.get("bottleneck_inflation_note", ""),
            "diag_continuity_infrastructure": diag.get("continuity_infrastructure_note", ""),
            "diag_capex_arms_race": diag.get("capex_arms_race_note", ""),
            "diag_asset_holder_policy": diag.get("asset_holder_policy_bias_note", ""),
            "diag_private_market_opacity": diag.get("private_market_opacity_note", ""),
            "diag_sovereign_industrial_compute": diag.get("sovereign_industrial_compute_note", ""),
            "diag_jurisdictional_arbitrage": diag.get("jurisdictional_arbitrage_note", ""),
            "diag_trust_asset_failure": diag.get("trust_asset_failure_note", ""),
            "diag_energy_security": diag.get("energy_security_note", ""),
            "bull_probability_pct": bull.get("probability_pct", ""),
            "bull_outcome": bull.get("price_target_or_outcome", ""),
            "bull_narrative": bull.get("narrative", ""),
            "base_probability_pct": base.get("probability_pct", ""),
            "base_outcome": base.get("price_target_or_outcome", ""),
            "base_narrative": base.get("narrative", ""),
            "bear_probability_pct": bear.get("probability_pct", ""),
            "bear_outcome": bear.get("price_target_or_outcome", ""),
            "bear_narrative": bear.get("narrative", ""),
            "ah_contradicting_signals": _join(ah.get("contradicting_signals", [])),
            "ah_likely_blind_spots": _join(ah.get("likely_blind_spots", [])),
            "ah_historical_false_positives": _join(ah.get("historical_false_positives", [])),
            "primary_falsifiers": _join(d.get("primary_falsifiers", [])),
            "top_signals": _join(sig.get("top_signals", [])),
            "signal_ranking_rationale": sig.get("ranking_rationale", ""),
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
            "dr_entry_conditions": dr.get("entry_conditions", ""),
            "dr_evidence_thresholds": dr.get("evidence_thresholds", ""),
            "dr_position_sizing_guidance": dr.get("position_sizing_guidance", ""),
            "dr_kill_conditions": dr.get("kill_conditions", ""),
            "dr_valuation_discipline": dr.get("valuation_discipline", ""),
            "dr_survivability_assumptions": dr.get("survivability_assumptions", ""),
            "dr_monitoring_signals": _join(dr.get("monitoring_signals", [])),
            "latent_pressure_count": len(d.get("latent_pressure_table", []) or []),
            "capital_actor_count": len(d.get("capital_actor_table", []) or []),
            "executive_summary": d.get("executive_summary", ""),
        }

        for code in COMPONENT_CODES:
            domain_key, field_name = COMPONENT_LOCATION[code]
            comp = _get(d, domain_key, field_name, default={})
            row[f"score_{code}_raw"] = comp.get("raw_score", "") if isinstance(comp, dict) else ""
            row[f"score_{code}_evidence"] = comp.get("evidence_classification", "") if isinstance(comp, dict) else ""
            row[f"score_{code}_kill_triggered"] = comp.get("kill_condition_triggered", "") if isinstance(comp, dict) else ""

        for cat in PRE_MORTEM_CATEGORIES:
            scen = pm.get(cat, {}) if isinstance(pm, dict) else {}
            row[f"premortem_{cat}_prob_pct"] = scen.get("probability_pct", "") if isinstance(scen, dict) else ""
            row[f"premortem_{cat}_failure_mode"] = scen.get("failure_mode", "") if isinstance(scen, dict) else ""

        updated_score, updated_tier, updated_notes = _compute_updated_score(row)
        row["updated_score"] = updated_score
        row["updated_tier"] = updated_tier
        row["updated_score_notes"] = updated_notes

        fs_data = fs_lookup.get(ticker, {})
        for fs_col in fs_fieldnames:
            row[fs_col] = fs_data.get(fs_col, "")

        csv_rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print("")
    print(f"Exported {len(csv_rows)} analyses to: {output_path}")
    print(f"  Columns: {len(fieldnames)}")

    if parse_errors:
        print(f"  JSON parse errors skipped: {parse_errors}")

    if csv_rows:
        master_scores = [
            _to_float(r.get("master_score"), default=None)
            for r in csv_rows
            if r.get("master_score") not in ("", None)
        ]
        master_scores = [s for s in master_scores if s is not None]

        updated_scores = [
            _to_float(r.get("updated_score"), default=None)
            for r in csv_rows
            if r.get("updated_score") not in ("", None)
        ]
        updated_scores = [s for s in updated_scores if s is not None]

        if master_scores:
            print("")
            print("Original Master Score Summary")
            print(f"  Count: {len(master_scores)}")
            print(f"  Min: {min(master_scores):.0f}")
            print(f"  Max: {max(master_scores):.0f}")
            print(f"  Mean: {sum(master_scores) / len(master_scores):.1f}")
            print(f"  Score >= 70: {sum(1 for s in master_scores if s >= 70)}")
            print(f"  Score >= 55: {sum(1 for s in master_scores if s >= 55)}")

        if updated_scores:
            print("")
            print("Updated Score Summary")
            print(f"  Count: {len(updated_scores)}")
            print(f"  Min: {min(updated_scores):.0f}")
            print(f"  Max: {max(updated_scores):.0f}")
            print(f"  Mean: {sum(updated_scores) / len(updated_scores):.1f}")
            print(f"  Score >= 85: {sum(1 for s in updated_scores if s >= 85)}")
            print(f"  Score >= 75: {sum(1 for s in updated_scores if s >= 75)}")
            print(f"  Score >= 65: {sum(1 for s in updated_scores if s >= 65)}")
            print(f"  Score < 50: {sum(1 for s in updated_scores if s < 50)}")

        partials = sum(1 for r in csv_rows if _to_bool(r.get("analysis_partial")))
        if partials:
            print(f"  Partial analyses: {partials}")

        ai_count = sum(1 for r in csv_rows if _to_bool(r.get("ai_infrastructure_relevant")))
        print(f"  AI infrastructure flagged: {ai_count}")


if __name__ == "__main__":
    export_cspp_full()
