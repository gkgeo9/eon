#!/usr/bin/env python3
"""
Export Multi-Perspective Analysis (Buffett/Taleb/Contrarian) from a batch to CSV.

Exports ALL fields from each perspective with no truncation.
Deduplicates by keeping the most recent result per (ticker, fiscal_year, filing_type).

Usage:
    python experimental/export_multi_analysis_to_csv.py

Output:
    data/multi_analysis_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
BATCH_NAME = "all_comp_08022026"


def export_multi_analysis_to_csv():
    """Extract all multi-perspective analyses from a batch and save to CSV."""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    output_path = project_root / "data" / "multi_analysis_export.csv"

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
        print(f"Batch '{BATCH_NAME}' not found in database.")
        conn.close()
        return

    batch_id, name, total, completed, status = batch_row
    print(f"Found batch: {name}")
    print(f"  Status: {status}")
    print(f"  Progress: {completed}/{total} tickers completed")

    # Query all SimplifiedAnalysis results for this batch
    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'SimplifiedAnalysis'
        ORDER BY ar.ticker, ar.fiscal_year DESC
        """,
        (batch_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No completed analyses found in this batch yet.")
        return

    # Deduplicate: keep the most recent result per (ticker, fiscal_year, filing_type)
    seen = {}
    for row in rows:
        key = (row[0], row[1], row[2])  # ticker, fiscal_year, filing_type
        if key not in seen or row[4] > seen[key][4]:  # compare created_at
            seen[key] = row
    deduped_rows = sorted(seen.values(), key=lambda r: (r[0], -r[1]))  # sort by ticker, year desc
    duplicates_removed = len(rows) - len(deduped_rows)

    print(f"\n  Total results: {len(rows)}")
    print(f"  Duplicates removed: {duplicates_removed}")
    print(f"  Unique analyses: {len(deduped_rows)}")

    # Define CSV columns — every field from every perspective, no truncation
    fieldnames = [
        # Meta
        "ticker",
        "fiscal_year",
        "filing_type",
        "created_at",
        # Action Signals
        "buffett_action_signal",
        "taleb_action_signal",
        "contrarian_action_signal",
        # Buffett — all fields
        "buffett_verdict",
        "buffett_moat_rating",
        "buffett_management_quality",
        "buffett_business_understanding",
        "buffett_economic_moat",
        "buffett_pricing_power",
        "buffett_return_on_invested_capital",
        "buffett_free_cash_flow_quality",
        "buffett_intrinsic_value_estimate",
        "buffett_tailwinds",
        # Taleb — all fields
        "taleb_verdict",
        "taleb_antifragile_rating",
        "taleb_fragility_assessment",
        "taleb_skin_in_the_game",
        "taleb_optionality",
        "taleb_lindy_effect",
        "taleb_dependency_chains",
        "taleb_tail_risks",
        "taleb_hidden_risks",
        "taleb_via_negativa",
        # Contrarian — all fields
        "contrarian_verdict",
        "contrarian_conviction_level",
        "contrarian_consensus_view",
        "contrarian_variant_perception",
        "contrarian_market_pricing",
        "contrarian_positioning",
        "contrarian_consensus_wrong",
        "contrarian_hidden_strengths",
        "contrarian_hidden_weaknesses",
        "contrarian_catalysts",
        # Overall
        "synthesis",
        "final_verdict",
    ]

    # Process rows
    csv_rows = []
    for ticker, fiscal_year, filing_type, result_json, created_at in deduped_rows:
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse JSON for {ticker} {fiscal_year}")
            continue

        buffett = data.get("buffett", {})
        taleb = data.get("taleb", {})
        contrarian = data.get("contrarian", {})

        csv_row = {
            # Meta
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            "created_at": created_at,
            # Action Signals
            "buffett_action_signal": buffett.get("action_signal", ""),
            "taleb_action_signal": taleb.get("action_signal", ""),
            "contrarian_action_signal": contrarian.get("action_signal", ""),
            # Buffett — all fields
            "buffett_verdict": buffett.get("buffett_verdict", ""),
            "buffett_moat_rating": buffett.get("moat_rating", ""),
            "buffett_management_quality": buffett.get("management_quality", ""),
            "buffett_business_understanding": buffett.get("business_understanding", ""),
            "buffett_economic_moat": buffett.get("economic_moat", ""),
            "buffett_pricing_power": buffett.get("pricing_power", ""),
            "buffett_return_on_invested_capital": buffett.get("return_on_invested_capital", ""),
            "buffett_free_cash_flow_quality": buffett.get("free_cash_flow_quality", ""),
            "buffett_intrinsic_value_estimate": buffett.get("intrinsic_value_estimate", ""),
            "buffett_tailwinds": "; ".join(buffett.get("business_tailwinds", [])),
            # Taleb — all fields
            "taleb_verdict": taleb.get("taleb_verdict", ""),
            "taleb_antifragile_rating": taleb.get("antifragile_rating", ""),
            "taleb_fragility_assessment": taleb.get("fragility_assessment", ""),
            "taleb_skin_in_the_game": taleb.get("skin_in_the_game", ""),
            "taleb_optionality": taleb.get("optionality_and_asymmetry", ""),
            "taleb_lindy_effect": taleb.get("lindy_effect", ""),
            "taleb_dependency_chains": taleb.get("dependency_chains", ""),
            "taleb_tail_risks": "; ".join(taleb.get("tail_risk_exposure", [])),
            "taleb_hidden_risks": "; ".join(taleb.get("hidden_risks", [])),
            "taleb_via_negativa": "; ".join(taleb.get("via_negativa", [])),
            # Contrarian — all fields
            "contrarian_verdict": contrarian.get("contrarian_verdict", ""),
            "contrarian_conviction_level": contrarian.get("conviction_level", ""),
            "contrarian_consensus_view": contrarian.get("consensus_view", ""),
            "contrarian_variant_perception": contrarian.get("variant_perception", ""),
            "contrarian_market_pricing": contrarian.get("market_pricing", ""),
            "contrarian_positioning": contrarian.get("positioning", ""),
            "contrarian_consensus_wrong": "; ".join(contrarian.get("consensus_wrong_because", [])),
            "contrarian_hidden_strengths": "; ".join(contrarian.get("hidden_strengths", [])),
            "contrarian_hidden_weaknesses": "; ".join(contrarian.get("hidden_weaknesses", [])),
            "contrarian_catalysts": "; ".join(contrarian.get("catalyst_timeline", [])),
            # Overall
            "synthesis": data.get("synthesis", ""),
            "final_verdict": data.get("final_verdict", ""),
        }
        csv_rows.append(csv_row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nExported {len(csv_rows)} analyses to: {output_path}")
    print(f"  Columns: {len(fieldnames)}")

    # Action signal summary
    print("\n--- Action Signal Summary ---")
    for perspective in ["buffett", "taleb", "contrarian"]:
        signal_key = f"{perspective}_action_signal"
        signals = [r[signal_key] for r in csv_rows if r[signal_key]]
        if signals:
            priority = signals.count("PRIORITY")
            investigate = signals.count("INVESTIGATE")
            pass_count = signals.count("PASS")
            print(
                f"  {perspective.capitalize():12} - "
                f"PRIORITY: {priority}, INVESTIGATE: {investigate}, PASS: {pass_count}"
            )


if __name__ == "__main__":
    export_multi_analysis_to_csv()
