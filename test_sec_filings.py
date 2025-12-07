#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to discover and validate available SEC filing types.

Tests:
- 10-K: Annual report (already supported)
- 10-Q: Quarterly report (already added)
- 8-K: Current report (material events)
- 4: Insider trading report
- DEF 14A: Proxy statement
- S-1: IPO registration
"""

from fintel.data.sources.sec import SECDownloader
from pathlib import Path

def test_filing_types():
    """Test different SEC filing types."""

    # Test ticker with good filing history
    ticker = "AAPL"

    filing_types_to_test = [
        ("10-K", "Annual Report"),
        ("10-Q", "Quarterly Report"),
        ("8-K", "Current Report (Material Events)"),
        ("4", "Insider Trading Report"),
        ("DEF 14A", "Proxy Statement"),
        ("S-1", "IPO Registration"),
        ("13F-HR", "Institutional Holdings"),
    ]

    downloader = SECDownloader()

    results = {}

    print(f"\n{'='*60}")
    print(f"Testing SEC Filing Types for {ticker}")
    print(f"{'='*60}\n")

    for filing_type, description in filing_types_to_test:
        print(f"Testing {filing_type:12} ({description})... ", end="", flush=True)

        try:
            # Try to download 1 filing
            filing_path = downloader.download(
                ticker=ticker,
                num_filings=1,
                filing_type=filing_type
            )

            if filing_path and filing_path.exists():
                # Count files
                num_files = len(list(filing_path.rglob("*")))
                results[filing_type] = {
                    "status": "✅ SUCCESS",
                    "description": description,
                    "path": str(filing_path),
                    "num_files": num_files
                }
                print(f"✅ SUCCESS ({num_files} files)")
            else:
                results[filing_type] = {
                    "status": "⚠️  NO DATA",
                    "description": description,
                    "path": None,
                    "num_files": 0
                }
                print("⚠️  NO DATA FOUND")

        except Exception as e:
            results[filing_type] = {
                "status": "❌ FAILED",
                "description": description,
                "error": str(e)
            }
            print(f"❌ FAILED: {e}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")

    successful = [ft for ft, r in results.items() if r["status"] == "✅ SUCCESS"]
    failed = [ft for ft, r in results.items() if r["status"] == "❌ FAILED"]
    no_data = [ft for ft, r in results.items() if r["status"] == "⚠️  NO DATA"]

    print(f"✅ Successful: {len(successful)}")
    for ft in successful:
        print(f"   - {ft:12} {results[ft]['description']}")

    if no_data:
        print(f"\n⚠️  No Data: {len(no_data)}")
        for ft in no_data:
            print(f"   - {ft:12} {results[ft]['description']}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for ft in failed:
            print(f"   - {ft:12} {results[ft].get('error', 'Unknown error')}")

    print(f"\n{'='*60}")
    print("RECOMMENDATIONS FOR UI")
    print(f"{'='*60}\n")

    if successful:
        print("Add these filing types to the UI dropdown:")
        print('```python')
        print('filing_type = st.selectbox(')
        print('    "Filing Type",')
        print('    options=[')
        for ft in successful:
            print(f'        "{ft}",  # {results[ft]["description"]}')
        print('    ],')
        print('    help="Type of SEC filing to analyze"')
        print(')')
        print('```')

    print()
    return results

if __name__ == "__main__":
    results = test_filing_types()
