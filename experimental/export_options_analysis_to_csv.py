#!/usr/bin/env python3
"""
Export AsymmetricOptionsV4 analysis from a batch to a clean, curated CSV.

Columns are hand-picked and ordered for easy reading:
  - Scores & signals up front for quick scanning/sorting
  - Catalysts expanded into clean numbered columns
  - Evidence & risks at the end (long text)

Deduplicates by keeping the most recent result per (ticker, fiscal_year, filing_type).

Usage:
    python experimental/export_options_analysis_to_csv.py

Output:
    data/<batch_name>_options_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
BATCH_NAME = "all_companies_options"
MAX_CATALYSTS = 4
MAX_HIDDEN_RISKS = 5


def export_options_to_csv():
    """Extract AsymmetricOptionsV4 analyses from a batch and save to a clean CSV."""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    safe_name = BATCH_NAME.replace(" ", "_").lower()
    output_path = project_root / "data" / f"{safe_name}_options_export.csv"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find the batch
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
    print(f"  Status: {status}  |  Progress: {completed}/{total}")

    # Query results
    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'AsymmetricOptionsV4'
        ORDER BY ar.ticker, ar.fiscal_year DESC
        """,
        (batch_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No AsymmetricOptionsV4 results found.")
        return

    # Deduplicate: most recent per (ticker, fiscal_year, filing_type)
    seen = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        if key not in seen or row[4] > seen[key][4]:
            seen[key] = row
    deduped = sorted(seen.values(), key=lambda r: (r[0], -r[1]))
    print(f"  Results: {len(rows)} total, {len(rows) - len(deduped)} dupes removed, {len(deduped)} unique")

    # ── Column definitions (ordered for readability) ──────────────────────────
    # Group 1: Identity
    meta_cols = ["ticker", "fiscal_year", "filing_type"]

    # Group 2: Key signals (scannable)
    signal_cols = [
        "directional_bias",
        "composite_asymmetry_score",
        "leaps_horizon_fit",
    ]

    # Group 3: Sub-scores
    score_cols = [
        "binary_event_score",
        "financial_distress_score",
        "opacity_score",
        "operational_fragility_score",
    ]

    # Group 4: Debt/cash
    financial_cols = [
        "imminent_debt_wall_year",
        "cash_runway_months",
    ]

    # Group 5: Catalysts (numbered)
    catalyst_cols = []
    for i in range(1, MAX_CATALYSTS + 1):
        catalyst_cols.extend([
            f"catalyst_{i}_type",
            f"catalyst_{i}_event",
            f"catalyst_{i}_months",
            f"catalyst_{i}_direction",
        ])

    # Group 6: Thesis
    thesis_cols = ["thesis_summary"]

    # Group 7: Hidden risks (numbered)
    risk_cols = [f"hidden_risk_{i}" for i in range(1, MAX_HIDDEN_RISKS + 1)]

    # Group 8: Evidence (long text, at the end)
    evidence_cols = [
        "binary_event_evidence",
        "financial_distress_evidence",
        "opacity_evidence",
        "operational_fragility_evidence",
    ]

    fieldnames = (
        meta_cols + signal_cols + score_cols + financial_cols
        + catalyst_cols + thesis_cols + risk_cols + evidence_cols
    )

    # ── Build rows ────────────────────────────────────────────────────────────
    csv_rows = []
    for ticker, fiscal_year, filing_type, result_json, created_at in deduped:
        try:
            d = json.loads(result_json)
        except json.JSONDecodeError:
            print(f"  Warning: bad JSON for {ticker} {fiscal_year}")
            continue

        row = {
            # Identity
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            # Signals
            "directional_bias": d.get("directional_bias", ""),
            "composite_asymmetry_score": d.get("composite_asymmetry_score", ""),
            "leaps_horizon_fit": d.get("leaps_horizon_fit", ""),
            # Sub-scores
            "binary_event_score": d.get("binary_event_score", ""),
            "financial_distress_score": d.get("financial_distress_score", ""),
            "opacity_score": d.get("opacity_score", ""),
            "operational_fragility_score": d.get("operational_fragility_score", ""),
            # Financial
            "imminent_debt_wall_year": d.get("imminent_debt_wall_year", ""),
            "cash_runway_months": d.get("cash_runway_months", ""),
            # Thesis
            "thesis_summary": d.get("thesis_summary", ""),
            # Evidence
            "binary_event_evidence": d.get("binary_event_evidence", ""),
            "financial_distress_evidence": d.get("financial_distress_evidence", ""),
            "opacity_evidence": d.get("opacity_evidence", ""),
            "operational_fragility_evidence": d.get("operational_fragility_evidence", ""),
        }

        # Catalysts (expand up to MAX_CATALYSTS)
        catalysts = d.get("catalysts", [])
        for i in range(1, MAX_CATALYSTS + 1):
            if i <= len(catalysts):
                c = catalysts[i - 1]
                row[f"catalyst_{i}_type"] = c.get("catalyst_type", "")
                row[f"catalyst_{i}_event"] = c.get("event_description", "")
                row[f"catalyst_{i}_months"] = c.get("months_to_event", "")
                row[f"catalyst_{i}_direction"] = c.get("direction", "")
            else:
                row[f"catalyst_{i}_type"] = ""
                row[f"catalyst_{i}_event"] = ""
                row[f"catalyst_{i}_months"] = ""
                row[f"catalyst_{i}_direction"] = ""

        # Hidden risks (expand up to MAX_HIDDEN_RISKS)
        risks = d.get("hidden_risks", [])
        for i in range(1, MAX_HIDDEN_RISKS + 1):
            row[f"hidden_risk_{i}"] = risks[i - 1] if i <= len(risks) else ""

        csv_rows.append(row)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nExported {len(csv_rows)} rows → {output_path}")
    print(f"  Columns: {len(fieldnames)}")

    # ── Summary stats ─────────────────────────────────────────────────────────
    print("\n--- Directional Bias ---")
    from collections import Counter
    biases = Counter(r["directional_bias"] for r in csv_rows)
    for bias, count in biases.most_common():
        print(f"  {bias}: {count}")

    print("\n--- Score Averages ---")
    for col in score_cols + ["composite_asymmetry_score"]:
        vals = []
        for r in csv_rows:
            try:
                vals.append(float(r[col]))
            except (ValueError, TypeError):
                pass
        if vals:
            print(f"  {col}: avg={sum(vals)/len(vals):.1f}  min={min(vals):.0f}  max={max(vals):.0f}")

    print("\n--- LEAPS Horizon Fit ---")
    fits = Counter(r["leaps_horizon_fit"] for r in csv_rows)
    for fit, count in fits.most_common():
        print(f"  {fit}: {count}")


if __name__ == "__main__":
    export_options_to_csv()
