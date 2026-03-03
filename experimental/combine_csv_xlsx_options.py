#!/usr/bin/env python3
"""
Combine any analysis CSV export with FactSet CSV market data.

Joins the analysis export (from export_any_analysis_to_csv.py) with FactSet data
on ticker, producing a single combined file with both AI analysis and market data.

Usage:
    python experimental/combine_csv_xlsx_options.py

Output:
    data/combined_<batch>_factset.csv
"""

import os

import pandas as pd
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
ANALYSIS_CSV = "data/all_companies_options_options_export.csv"
FACTSET_CSV = "all_companies_08022026_24022026.csv"


def combine_analysis_with_factset(
    csv_path: str = ANALYSIS_CSV,
    factset_path: str = FACTSET_CSV,
    output_path: str | None = None,
) -> pd.DataFrame:
    """
    Combine analysis CSV with FactSet CSV market data.

    Args:
        csv_path: Path to the analysis export CSV
        factset_path: Path to the FactSet CSV file
        output_path: Path for combined output CSV (auto-generated if None)

    Returns:
        Combined DataFrame
    """
    project_root = Path(__file__).parent.parent
    csv_full = project_root / csv_path
    factset_full = project_root / factset_path

    if output_path is None:
        stem = Path(csv_path).stem.replace("_export", "")
        output_path = f"data/combined_{stem}_factset.csv"
    output_full = project_root / output_path

    # Read analysis CSV
    print(f"Reading analysis CSV: {csv_path}")
    df_analysis = pd.read_csv(csv_full)
    print(f"  Shape: {df_analysis.shape}")
    print(f"  Unique tickers: {df_analysis['ticker'].nunique()}")

    # Read FactSet CSV
    print(f"\nReading FactSet CSV: {factset_path}")
    df_factset = pd.read_csv(factset_full).dropna(how="all")
    df_factset.columns = [c.strip() for c in df_factset.columns]
    print(f"  Shape: {df_factset.shape}")
    print(f"  Unique tickers: {df_factset['ticker'].nunique()}")

    # Normalize tickers for matching
    df_analysis["ticker"] = df_analysis["ticker"].astype(str).str.strip().str.upper()
    df_factset["ticker"] = df_factset["ticker"].astype(str).str.strip().str.upper()

    # Drop rows where ticker is NaN or empty
    df_factset = df_factset[df_factset["ticker"].notna() & (df_factset["ticker"] != "NAN")]

    # Check overlap
    analysis_tickers = set(df_analysis["ticker"].unique())
    factset_tickers = set(df_factset["ticker"].unique())
    overlap = analysis_tickers & factset_tickers
    only_analysis = analysis_tickers - factset_tickers
    print(f"\n  Ticker overlap: {len(overlap)}/{len(analysis_tickers)} analysis tickers found in FactSet")
    if only_analysis and len(only_analysis) <= 20:
        print(f"  Analysis tickers not in FactSet: {sorted(only_analysis)}")
    elif only_analysis:
        print(f"  Analysis tickers not in FactSet: {len(only_analysis)} tickers")

    # Handle column name conflicts (except 'ticker')
    factset_cols = set(df_factset.columns) - {"ticker"}
    analysis_cols = set(df_analysis.columns) - {"ticker"}
    conflicts = factset_cols & analysis_cols
    if conflicts:
        print(f"\n  Column name conflicts (prefixed with 'fs_'): {conflicts}")
        rename_map = {c: f"fs_{c}" for c in conflicts}
        df_factset = df_factset.rename(columns=rename_map)

    # Left join: keep all analysis rows, add FactSet data where available
    print(f"\nCombining with left join on 'ticker'...")
    combined = df_analysis.merge(df_factset, on="ticker", how="left")

    # Check match rate using a FactSet-only column
    factset_indicator = [c for c in df_factset.columns if c != "ticker"][0]
    matched = combined[factset_indicator].notna().sum()
    total = len(combined)
    print(f"  Combined shape: {combined.shape}")
    print(f"  Rows with FactSet data: {matched}/{total} ({matched/total*100:.1f}%)")

    # Save
    print(f"\nSaving to {output_path}...")
    combined.to_csv(output_full, index=False)

    size_mb = os.path.getsize(output_full) / 1024 / 1024
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  Total columns: {len(combined.columns)}")

    # Print column groups
    print(f"\n--- Analysis columns ({len(analysis_cols) + 1}) ---")
    for c in ["ticker"] + sorted(analysis_cols):
        print(f"    {c}")
    print(f"\n--- FactSet columns ({len(factset_cols)}) ---")
    for c in sorted(df_factset.columns):
        if c != "ticker":
            print(f"    {c}")

    return combined


if __name__ == "__main__":
    combine_analysis_with_factset()
