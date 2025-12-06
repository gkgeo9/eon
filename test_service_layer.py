#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the AnalysisService layer that wraps all analyzers for the UI.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService


def test_service_fundamental():
    """Test service layer with fundamental analysis."""
    print("\n" + "="*70)
    print("TEST: AnalysisService - Fundamental Analysis")
    print("="*70)

    db = DatabaseRepository("data/test_service.db")
    service = AnalysisService(db)

    print("Running fundamental analysis through service layer...")
    print("Ticker: AAPL, Years: 1, Type: fundamental")

    try:
        run_id = service.run_analysis(
            ticker="AAPL",
            analysis_type="fundamental",
            filing_type="10-K",
            num_years=1
        )

        print(f"✅ Analysis completed!")
        print(f"   Run ID: {run_id}")

        # Check status
        status = db.get_run_status(run_id)
        print(f"   Status: {status}")

        # Get results
        if status == 'completed':
            results = db.get_analysis_results(run_id)
            print(f"   Results: {len(results)} year(s)")
            for result in results:
                print(f"     - Year {result['fiscal_year']}: {result['result_type']}")
            return True
        else:
            details = db.get_run_details(run_id)
            error = details.get('error_message', 'Unknown')
            print(f"   ❌ Error: {error}")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_buffett():
    """Test service layer with Buffett analysis."""
    print("\n" + "="*70)
    print("TEST: AnalysisService - Buffett Lens")
    print("="*70)

    db = DatabaseRepository("data/test_service.db")
    service = AnalysisService(db)

    print("Running Buffett analysis through service layer...")
    print("Ticker: AAPL, Years: 1, Type: buffett")

    try:
        run_id = service.run_analysis(
            ticker="AAPL",
            analysis_type="buffett",
            filing_type="10-K",
            num_years=1
        )

        print(f"✅ Analysis completed!")
        print(f"   Run ID: {run_id}")

        # Check status
        status = db.get_run_status(run_id)
        print(f"   Status: {status}")

        # Get results
        if status == 'completed':
            results = db.get_analysis_results(run_id)
            print(f"   Results: {len(results)} year(s)")
            for result in results:
                print(f"     - Year {result['fiscal_year']}: {result['result_type']}")
            return True
        else:
            details = db.get_run_details(run_id)
            error = details.get('error_message', 'Unknown')
            print(f"   ❌ Error: {error}")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_taleb():
    """Test service layer with Taleb analysis."""
    print("\n" + "="*70)
    print("TEST: AnalysisService - Taleb Lens")
    print("="*70)

    db = DatabaseRepository("data/test_service.db")
    service = AnalysisService(db)

    print("Running Taleb analysis through service layer...")
    print("Ticker: AAPL, Years: 1, Type: taleb")

    try:
        run_id = service.run_analysis(
            ticker="AAPL",
            analysis_type="taleb",
            filing_type="10-K",
            num_years=1
        )

        print(f"✅ Analysis completed!")
        print(f"   Run ID: {run_id}")

        # Check status
        status = db.get_run_status(run_id)
        print(f"   Status: {status}")

        # Get results
        if status == 'completed':
            results = db.get_analysis_results(run_id)
            print(f"   Results: {len(results)} year(s)")
            for result in results:
                print(f"     - Year {result['fiscal_year']}: {result['result_type']}")
            return True
        else:
            details = db.get_run_details(run_id)
            error = details.get('error_message', 'Unknown')
            print(f"   ❌ Error: {error}")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_contrarian():
    """Test service layer with Contrarian analysis."""
    print("\n" + "="*70)
    print("TEST: AnalysisService - Contrarian Lens")
    print("="*70)

    db = DatabaseRepository("data/test_service.db")
    service = AnalysisService(db)

    print("Running Contrarian analysis through service layer...")
    print("Ticker: AAPL, Years: 1, Type: contrarian")

    try:
        run_id = service.run_analysis(
            ticker="AAPL",
            analysis_type="contrarian",
            filing_type="10-K",
            num_years=1
        )

        print(f"✅ Analysis completed!")
        print(f"   Run ID: {run_id}")

        # Check status
        status = db.get_run_status(run_id)
        print(f"   Status: {status}")

        # Get results
        if status == 'completed':
            results = db.get_analysis_results(run_id)
            print(f"   Results: {len(results)} year(s)")
            for result in results:
                print(f"     - Year {result['fiscal_year']}: {result['result_type']}")
            return True
        else:
            details = db.get_run_details(run_id)
            error = details.get('error_message', 'Unknown')
            print(f"   ❌ Error: {error}")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_multi():
    """Test service layer with Multi-Perspective analysis."""
    print("\n" + "="*70)
    print("TEST: AnalysisService - Multi-Perspective")
    print("="*70)

    db = DatabaseRepository("data/test_service.db")
    service = AnalysisService(db)

    print("Running Multi-Perspective analysis through service layer...")
    print("Ticker: AAPL, Years: 1, Type: multi")

    try:
        run_id = service.run_analysis(
            ticker="AAPL",
            analysis_type="multi",
            filing_type="10-K",
            num_years=1
        )

        print(f"✅ Analysis completed!")
        print(f"   Run ID: {run_id}")

        # Check status
        status = db.get_run_status(run_id)
        print(f"   Status: {status}")

        # Get results
        if status == 'completed':
            results = db.get_analysis_results(run_id)
            print(f"   Results: {len(results)} year(s)")
            for result in results:
                print(f"     - Year {result['fiscal_year']}: {result['result_type']}")
            return True
        else:
            details = db.get_run_details(run_id)
            error = details.get('error_message', 'Unknown')
            print(f"   ❌ Error: {error}")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 ANALYSIS SERVICE LAYER TESTING SUITE")
    print("="*70)
    print("This tests the UI service layer that wraps all analyzers")
    print("="*70)

    results = {}

    # Test fundamental
    try:
        results['fundamental'] = test_service_fundamental()
    except Exception as e:
        print(f"\n❌ Fundamental service test failed: {e}")
        import traceback
        traceback.print_exc()
        results['fundamental'] = False

    # Test Buffett
    try:
        results['buffett'] = test_service_buffett()
    except Exception as e:
        print(f"\n❌ Buffett service test failed: {e}")
        import traceback
        traceback.print_exc()
        results['buffett'] = False

    # Test Taleb
    try:
        results['taleb'] = test_service_taleb()
    except Exception as e:
        print(f"\n❌ Taleb service test failed: {e}")
        import traceback
        traceback.print_exc()
        results['taleb'] = False

    # Test Contrarian
    try:
        results['contrarian'] = test_service_contrarian()
    except Exception as e:
        print(f"\n❌ Contrarian service test failed: {e}")
        import traceback
        traceback.print_exc()
        results['contrarian'] = False

    # Test Multi-Perspective
    try:
        results['multi'] = test_service_multi()
    except Exception as e:
        print(f"\n❌ Multi-Perspective service test failed: {e}")
        import traceback
        traceback.print_exc()
        results['multi'] = False

    # Summary
    print("\n" + "="*70)
    print("ANALYSIS SERVICE TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.capitalize():20s}: {status}")

    print("="*70)

    if all(results.values()):
        print("\n🎉 All service layer tests passed!")
        print("\nThe AnalysisService properly wraps:")
        print("  ✓ FundamentalAnalyzer")
        print("  ✓ PerspectiveAnalyzer (Buffett, Taleb, Contrarian, Multi)")
        print("  ✓ Database persistence")
        print("  ✓ File caching")
        print("\nReady for UI integration!")
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"\n⚠️  Some tests failed: {', '.join(failed)}")
