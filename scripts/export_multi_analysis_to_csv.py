#!/usr/bin/env python3
"""
Export Multi-Perspective Analysis (Buffett/Taleb/Contrarian) from a batch to CSV.

Usage:
    python scripts/export_multi_analysis_to_csv.py

Output:
    data/multi_analysis_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path

# Batch to export
BATCH_NAME = "IV40to80_2"


def export_multi_analysis_to_csv():
    """Extract all multi-perspective analyses from a batch and save to CSV."""
    # Paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    output_path = project_root / "data" / "multi_analysis_export.csv"

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, find the batch_id
    cursor.execute(
        "SELECT batch_id, name, total_tickers, completed_tickers, status FROM batch_jobs WHERE name = ?",
        (BATCH_NAME,)
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
    cursor.execute("""
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = 'SimplifiedAnalysis'
        ORDER BY ar.ticker, ar.fiscal_year DESC
    """, (batch_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No completed analyses found in this batch yet.")
        return

    # Define CSV columns - key fields from each perspective + action signals
    fieldnames = [
        # Meta
        "ticker",
        "fiscal_year",
        "filing_type",
        "created_at",
        # Action Signals (the new fields!)
        "buffett_action_signal",
        "taleb_action_signal",
        "contrarian_action_signal",
        # Buffett key fields
        "buffett_verdict",
        "moat_rating",
        "management_grade",
        "roic_summary",
        "margin_of_safety",
        # Taleb key fields
        "taleb_verdict",
        "antifragile_rating",
        "fragility_summary",
        "skin_in_the_game_summary",
        # Contrarian key fields
        "contrarian_verdict",
        "conviction_level",
        "variant_perception",
        "market_pricing_summary",
        # Overall
        "synthesis",
        "final_verdict",
        # Detailed fields (truncated for CSV readability)
        "buffett_business_understanding",
        "buffett_economic_moat",
        "buffett_pricing_power",
        "buffett_intrinsic_value_estimate",
        "taleb_optionality",
        "taleb_lindy_effect",
        "contrarian_consensus_view",
        # Lists as semicolon-separated
        "buffett_tailwinds",
        "taleb_tail_risks",
        "taleb_hidden_risks",
        "taleb_via_negativa",
        "contrarian_consensus_wrong",
        "contrarian_hidden_strengths",
        "contrarian_hidden_weaknesses",
        "contrarian_catalysts",
    ]

    # Process rows and write to CSV
    csv_rows = []
    for ticker, fiscal_year, filing_type, result_json, created_at in rows:
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse JSON for {ticker} {fiscal_year}")
            continue

        buffett = data.get("buffett", {})
        taleb = data.get("taleb", {})
        contrarian = data.get("contrarian", {})

        # Extract management grade from management_quality text (look for "Grade: X")
        mgmt_text = buffett.get("management_quality", "")
        mgmt_grade = ""
        if "Grade:" in mgmt_text:
            grade_part = mgmt_text.split("Grade:")[-1].strip()
            mgmt_grade = grade_part.split()[0] if grade_part else ""

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
            # Buffett key fields
            "buffett_verdict": buffett.get("buffett_verdict", ""),
            "moat_rating": buffett.get("moat_rating", ""),
            "management_grade": mgmt_grade,
            "roic_summary": _truncate(buffett.get("return_on_invested_capital", ""), 300),
            "margin_of_safety": _truncate(buffett.get("intrinsic_value_estimate", ""), 300),
            # Taleb key fields
            "taleb_verdict": taleb.get("taleb_verdict", ""),
            "antifragile_rating": taleb.get("antifragile_rating", ""),
            "fragility_summary": _truncate(taleb.get("fragility_assessment", ""), 300),
            "skin_in_the_game_summary": _truncate(taleb.get("skin_in_the_game", ""), 300),
            # Contrarian key fields
            "contrarian_verdict": contrarian.get("contrarian_verdict", ""),
            "conviction_level": contrarian.get("conviction_level", ""),
            "variant_perception": _truncate(contrarian.get("variant_perception", ""), 500),
            "market_pricing_summary": _truncate(contrarian.get("market_pricing", ""), 300),
            # Overall
            "synthesis": _truncate(data.get("synthesis", ""), 500),
            "final_verdict": _truncate(data.get("final_verdict", ""), 500),
            # Detailed fields
            "buffett_business_understanding": _truncate(buffett.get("business_understanding", ""), 300),
            "buffett_economic_moat": _truncate(buffett.get("economic_moat", ""), 300),
            "buffett_pricing_power": _truncate(buffett.get("pricing_power", ""), 300),
            "buffett_intrinsic_value_estimate": _truncate(buffett.get("intrinsic_value_estimate", ""), 300),
            "taleb_optionality": _truncate(taleb.get("optionality_and_asymmetry", ""), 300),
            "taleb_lindy_effect": _truncate(taleb.get("lindy_effect", ""), 300),
            "contrarian_consensus_view": _truncate(contrarian.get("consensus_view", ""), 300),
            # Lists as semicolon-separated
            "buffett_tailwinds": "; ".join(buffett.get("business_tailwinds", [])),
            "taleb_tail_risks": "; ".join(taleb.get("tail_risk_exposure", [])),
            "taleb_hidden_risks": "; ".join(taleb.get("hidden_risks", [])),
            "taleb_via_negativa": "; ".join(taleb.get("via_negativa", [])),
            "contrarian_consensus_wrong": "; ".join(contrarian.get("consensus_wrong_because", [])),
            "contrarian_hidden_strengths": "; ".join(contrarian.get("hidden_strengths", [])),
            "contrarian_hidden_weaknesses": "; ".join(contrarian.get("hidden_weaknesses", [])),
            "contrarian_catalysts": "; ".join(contrarian.get("catalyst_timeline", [])),
        }
        csv_rows.append(csv_row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nExported {len(csv_rows)} analyses to: {output_path}")

    # Print summary of action signals
    print("\n--- Action Signal Summary ---")
    for perspective in ["buffett", "taleb", "contrarian"]:
        signal_key = f"{perspective}_action_signal"
        signals = [r[signal_key] for r in csv_rows if r[signal_key]]
        if signals:
            priority = signals.count("PRIORITY")
            investigate = signals.count("INVESTIGATE")
            pass_count = signals.count("PASS")
            print(f"{perspective.capitalize():12} - PRIORITY: {priority}, INVESTIGATE: {investigate}, PASS: {pass_count}")


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text to max_len characters, adding ellipsis if truncated."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


if __name__ == "__main__":
    export_multi_analysis_to_csv()
