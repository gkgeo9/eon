#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test script for dynamic filing type discovery.
"""

from eon.data.sources.sec import SECDownloader
from eon.ui.database import DatabaseRepository

def test_filing_types():
    """Test the filing type query and caching functionality."""

    print("\n" + "="*60)
    print("Testing Dynamic Filing Type Discovery")
    print("="*60 + "\n")

    # Initialize components
    downloader = SECDownloader()
    db = DatabaseRepository()

    # Test 1: Query filing types for US company (Apple)
    print("Test 1: Querying filing types for AAPL (US company)...")
    try:
        filing_types = downloader.get_available_filing_types("AAPL")
        print(f"✅ Found {len(filing_types)} filing types for AAPL")
        print(f"   Top 10: {filing_types[:10]}")

        # Cache the result
        db.cache_filing_types("AAPL", filing_types)
        print("✅ Cached filing types for AAPL")
    except Exception as e:
        print(f"❌ Error querying AAPL: {e}")

    print()

    # Test 2: Query filing types for another US company (Microsoft)
    print("Test 2: Querying filing types for MSFT (US company)...")
    try:
        filing_types = downloader.get_available_filing_types("MSFT")
        print(f"✅ Found {len(filing_types)} filing types for MSFT")
        print(f"   Top 10: {filing_types[:10]}")

        # Cache the result
        db.cache_filing_types("MSFT", filing_types)
        print("✅ Cached filing types for MSFT")
    except Exception as e:
        print(f"❌ Error querying MSFT: {e}")

    print()

    # Test 3: Test cache retrieval
    print("Test 3: Testing cache retrieval...")
    try:
        cached_aapl = db.get_cached_filing_types("AAPL", max_age_hours=24)
        if cached_aapl:
            print(f"✅ Retrieved {len(cached_aapl)} filing types from cache for AAPL")
            print(f"   Top 10: {cached_aapl[:10]}")
        else:
            print("❌ Cache miss for AAPL")
    except Exception as e:
        print(f"❌ Error retrieving cache: {e}")

    print()

    # Test 4: Try an international company ticker (if exists)
    print("Test 4: Querying filing types for international company (TSM - Taiwan)...")
    try:
        filing_types = downloader.get_available_filing_types("TSM")
        print(f"✅ Found {len(filing_types)} filing types for TSM")
        print(f"   Top 10: {filing_types[:10]}")
    except Exception as e:
        print(f"⚠️  Note: {e}")
        print("   (International companies may have different or fewer SEC filings)")

    print()

    # Test 5: Test with invalid ticker
    print("Test 5: Testing error handling with invalid ticker...")
    try:
        filing_types = downloader.get_available_filing_types("INVALID123")
        if filing_types:
            print(f"⚠️  Found {len(filing_types)} filing types for invalid ticker")
        else:
            print("✅ Correctly returned empty list for invalid ticker")
    except Exception as e:
        print(f"✅ Correctly raised error: {type(e).__name__}")

    print("\n" + "="*60)
    print("Testing Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_filing_types()
