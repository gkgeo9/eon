#!/usr/bin/env python3
"""
Export all MoonshotAnalysisResult data from fintel.db to CSV.

Usage:
    python tests/export_moonshot_to_csv.py

Output:
    data/moonshot_analysis_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path


def export_moonshot_to_csv():
    """Extract all moonshot analyses from fintel.db and save to CSV."""
    # Paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "fintel.db"
    output_path = project_root / "data" / "moonshot_analysis_export.csv"

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all moonshot analyses
    cursor.execute("""
        SELECT ticker, fiscal_year, filing_type, result_json, created_at
        FROM analysis_results
        WHERE result_type = 'MoonshotAnalysisResult'
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No moonshot analyses found in the database.")
        return

    # Define CSV columns - flatten the JSON structure
    fieldnames = [
        "ticker",
        "fiscal_year",
        "filing_type",
        "created_at",
        "quick_verdict",
        "one_sentence_thesis",
        "anti_consensus_score",
        "moonshot_conviction",
        "business_model_novelty",
        "what_sounds_impossible",
        "why_market_doubts",
        "bull_case_multiple",
        "bear_case_outcome",
        "probability_assessment",
        "expected_value",
        "market_misunderstanding",
        "catalysts_and_timeline",
        "capital_situation",
        "comparable_examples",
        "insider_alignment",
        "what_would_kill_thesis",
        "progress_evidence",
        "credibility_signals",
        "execution_risks",
    ]

    # Process rows and write to CSV
    csv_rows = []
    for ticker, fiscal_year, filing_type, result_json, created_at in rows:
        data = json.loads(result_json)

        # Extract nested fields
        novelty = data.get("novelty", {})
        asymmetry = data.get("asymmetry", {})

        csv_row = {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            "created_at": created_at,
            "quick_verdict": data.get("quick_verdict", ""),
            "one_sentence_thesis": data.get("one_sentence_thesis", ""),
            "anti_consensus_score": data.get("anti_consensus_score", ""),
            "moonshot_conviction": data.get("moonshot_conviction", ""),
            "business_model_novelty": novelty.get("business_model_novelty", ""),
            "what_sounds_impossible": novelty.get("what_sounds_impossible", ""),
            "why_market_doubts": novelty.get("why_market_doubts", ""),
            "bull_case_multiple": asymmetry.get("bull_case_multiple", ""),
            "bear_case_outcome": asymmetry.get("bear_case_outcome", ""),
            "probability_assessment": asymmetry.get("probability_assessment", ""),
            "expected_value": asymmetry.get("expected_value", ""),
            "market_misunderstanding": data.get("market_misunderstanding", ""),
            "catalysts_and_timeline": data.get("catalysts_and_timeline", ""),
            "capital_situation": data.get("capital_situation", ""),
            "comparable_examples": data.get("comparable_examples", ""),
            "insider_alignment": data.get("insider_alignment", ""),
            "what_would_kill_thesis": data.get("what_would_kill_thesis", ""),
            # Convert lists to semicolon-separated strings
            "progress_evidence": "; ".join(novelty.get("progress_evidence", [])),
            "credibility_signals": "; ".join(data.get("credibility_signals", [])),
            "execution_risks": "; ".join(data.get("execution_risks", [])),
        }
        csv_rows.append(csv_row)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Exported {len(csv_rows)} moonshot analyses to: {output_path}")


if __name__ == "__main__":
    export_moonshot_to_csv()
