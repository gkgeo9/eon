#!/usr/bin/env python3
"""
Combine CSV and XLSX files from data folder.

This script combines:
- multi_analysis_export.csv (AI analysis results with 39 columns)
- all_companies_08022026.xlsx (FactSet market data with 35 columns)

Into a single combined file with 74 columns.
"""

import pandas as pd
from pathlib import Path


def combine_files(
    csv_path: str = "data/multi_analysis_export.csv",
    xlsx_path: str = "data/all_companies_08022026.xlsx",
    output_path: str = "data/combined_analysis_market_data.csv",
) -> pd.DataFrame:
    """
    Combine CSV analysis data with XLSX market data.

    Args:
        csv_path: Path to the multi-analysis export CSV
        xlsx_path: Path to the all companies XLSX file
        output_path: Path for the combined output CSV

    Returns:
        Combined DataFrame
    """
    # Read both files
    print(f"Reading {csv_path}...")
    df_csv = pd.read_csv(csv_path)
    print(f"  Shape: {df_csv.shape}")
    print(f"  Unique tickers: {df_csv['ticker'].nunique()}")

    print(f"\nReading {xlsx_path}...")
    # Header is at row 4 (0-indexed), drop empty rows
    df_xlsx = pd.read_excel(xlsx_path, header=4).dropna(how="all")
    print(f"  Shape: {df_xlsx.shape}")
    print(f"  Unique tickers: {df_xlsx['ticker'].nunique()}")

    # Clean up xlsx column names (strip whitespace)
    df_xlsx.columns = [c.strip() for c in df_xlsx.columns]

    # Check overlap
    xlsx_tickers = set(df_xlsx["ticker"].unique())
    csv_tickers = set(df_csv["ticker"].unique())
    overlap = len(xlsx_tickers & csv_tickers)
    print(f"\nTicker overlap: {overlap}/{len(csv_tickers)} CSV tickers found in XLSX")

    # Left join: keep all CSV rows, add XLSX market data where available
    print(f"\nCombining with left join on 'ticker'...")
    combined = df_csv.merge(df_xlsx, on="ticker", how="left")

    print(f"  Combined shape: {combined.shape}")
    matched = combined["company_name"].notna().sum()
    total = len(combined)
    print(f"  Rows with market data: {matched}/{total} ({matched/total*100:.1f}%)")

    # Save
    print(f"\nSaving to {output_path}...")
    combined.to_csv(output_path, index=False)

    import os

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  Total columns: {len(combined.columns)}")

    return combined


if __name__ == "__main__":
    combine_files()
