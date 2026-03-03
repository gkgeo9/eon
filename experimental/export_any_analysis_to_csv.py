#!/usr/bin/env python3
"""
Export any analysis type from a batch to CSV.

Auto-detects the result_type in the batch and dynamically flattens all JSON fields
into CSV columns. Works for AsymmetricOptionsV4, SimplifiedAnalysis, or any future type.

Nested lists (e.g. catalysts, hidden_risks) are flattened into numbered columns.
Deduplicates by keeping the most recent result per (ticker, fiscal_year, filing_type).

Usage:
    python experimental/export_any_analysis_to_csv.py

Output:
    data/<batch_name>_export.csv
"""

import csv
import json
import sqlite3
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
BATCH_NAME = "all_companies_options"


def flatten_value(prefix: str, value, out: dict):
    """Recursively flatten a value into dot-separated keys."""
    if isinstance(value, dict):
        for k, v in value.items():
            flatten_value(f"{prefix}_{k}" if prefix else k, v, out)
    elif isinstance(value, list):
        if not value:
            return  # skip empty lists entirely
        elif isinstance(value[0], dict):
            # List of dicts (e.g. catalysts) → numbered columns
            for i, item in enumerate(value, 1):
                flatten_value(f"{prefix}_{i}", item, out)
        else:
            # List of strings (e.g. hidden_risks) → semicolon-joined
            out[prefix] = "; ".join(str(v) for v in value)
    else:
        out[prefix] = value if value is not None else ""


def export_batch_to_csv():
    """Extract all analyses from a batch and save to CSV."""
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "eon.db"
    safe_name = BATCH_NAME.replace(" ", "_").lower()
    output_path = project_root / "data" / f"{safe_name}_export.csv"

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

    # Detect result types in this batch
    cursor.execute(
        """
        SELECT DISTINCT ar.result_type
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
        """,
        (batch_id,),
    )
    result_types = [r[0] for r in cursor.fetchall()]
    print(f"  Result types found: {result_types}")

    if not result_types:
        print("No completed analyses found in this batch yet.")
        conn.close()
        return

    # Use the first (or only) result type
    result_type = result_types[0]
    if len(result_types) > 1:
        print(f"  Multiple result types found, using: {result_type}")

    # Query all results for this batch and type
    cursor.execute(
        """
        SELECT ar.ticker, ar.fiscal_year, ar.filing_type, ar.result_json, ar.created_at
        FROM analysis_results ar
        JOIN batch_items bi ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ?
          AND ar.result_type = ?
        ORDER BY ar.ticker, ar.fiscal_year DESC
        """,
        (batch_id, result_type),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No completed analyses found.")
        return

    # Deduplicate: keep the most recent result per (ticker, fiscal_year, filing_type)
    seen = {}
    for row in rows:
        key = (row[0], row[1], row[2])
        if key not in seen or row[4] > seen[key][4]:
            seen[key] = row
    deduped_rows = sorted(seen.values(), key=lambda r: (r[0], -r[1]))
    duplicates_removed = len(rows) - len(deduped_rows)

    print(f"\n  Total results: {len(rows)}")
    print(f"  Duplicates removed: {duplicates_removed}")
    print(f"  Unique analyses: {len(deduped_rows)}")

    # Flatten all rows and collect all possible columns
    csv_rows = []
    all_keys = set()

    for ticker, fiscal_year, filing_type, result_json, created_at in deduped_rows:
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse JSON for {ticker} {fiscal_year}")
            continue

        flat = {}
        flatten_value("", data, flat)

        # Add meta columns
        row_data = {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "filing_type": filing_type,
            "created_at": created_at,
        }
        row_data.update(flat)
        csv_rows.append(row_data)
        all_keys.update(row_data.keys())

    if not csv_rows:
        print("No rows to export after parsing.")
        return

    # Build ordered column list: meta first, then sorted analysis fields
    meta_cols = ["ticker", "fiscal_year", "filing_type", "created_at"]
    analysis_cols = sorted(all_keys - set(meta_cols))
    fieldnames = meta_cols + analysis_cols

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in csv_rows:
            # Fill missing keys with empty string
            complete_row = {col: row.get(col, "") for col in fieldnames}
            writer.writerows([complete_row])

    print(f"\nExported {len(csv_rows)} analyses to: {output_path}")
    print(f"  Result type: {result_type}")
    print(f"  Columns: {len(fieldnames)}")
    print(f"\n  Column list:")
    for col in fieldnames:
        print(f"    - {col}")

    # Summary stats for key score fields (if they exist)
    score_cols = [c for c in analysis_cols if "score" in c.lower()]
    if score_cols:
        print("\n--- Score Summary ---")
        for col in score_cols:
            values = [r[col] for r in csv_rows if r.get(col, "") != ""]
            numeric = []
            for v in values:
                try:
                    numeric.append(float(v))
                except (ValueError, TypeError):
                    pass
            if numeric:
                avg = sum(numeric) / len(numeric)
                print(f"  {col}: avg={avg:.1f}, min={min(numeric):.0f}, max={max(numeric):.0f}")

    # Directional bias summary (for options analysis)
    bias_col = "directional_bias"
    if bias_col in all_keys:
        print("\n--- Directional Bias Summary ---")
        biases = [r.get(bias_col, "") for r in csv_rows if r.get(bias_col, "")]
        from collections import Counter

        for bias, count in Counter(biases).most_common():
            print(f"  {bias}: {count}")


if __name__ == "__main__":
    export_batch_to_csv()
