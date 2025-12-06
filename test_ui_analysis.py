#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test for UI analysis workflow.
Tests the entire flow: database → service → analyzer → results
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService

def test_full_analysis_workflow():
    """Test the complete analysis workflow."""
    print("="*70)
    print("FINTEL UI ANALYSIS WORKFLOW TEST")
    print("="*70)

    # Setup
    print("\n1. Setting up database and service...")
    db = DatabaseRepository("data/test_analysis.db")
    service = AnalysisService(db)
    print("   ✅ Database and service initialized")
    print(f"   ✅ Available API keys: {len(service.api_key_manager.api_keys)}")

    # Test parameters
    ticker = "AAPL"
    analysis_type = "fundamental"
    filing_type = "10-K"
    num_years = 1

    print(f"\n2. Starting {analysis_type} analysis for {ticker}...")
    print(f"   Ticker: {ticker}")
    print(f"   Type: {analysis_type}")
    print(f"   Filing: {filing_type}")
    print(f"   Years: {num_years}")

    try:
        # Run analysis
        run_id = service.run_analysis(
            ticker=ticker,
            analysis_type=analysis_type,
            filing_type=filing_type,
            num_years=num_years
        )

        print(f"   ✅ Analysis started with run_id: {run_id}")

        # Monitor status
        print("\n3. Monitoring analysis progress...")
        max_wait = 600  # 10 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = db.get_run_status(run_id)
            elapsed = int(time.time() - start_time)

            if status == 'completed':
                print(f"   ✅ Analysis completed in {elapsed} seconds")
                break
            elif status == 'failed':
                run_details = db.get_run_details(run_id)
                error_msg = run_details.get('error_message', 'Unknown error')
                print(f"   ❌ Analysis failed: {error_msg}")
                return False
            elif status == 'running':
                print(f"   🔄 Still running... ({elapsed}s elapsed)")
                time.sleep(10)
            else:
                print(f"   ⏳ Status: {status} ({elapsed}s)")
                time.sleep(5)

        if time.time() - start_time >= max_wait:
            print(f"   ⏰ Timeout after {max_wait} seconds")
            return False

        # Get results
        print("\n4. Retrieving results...")
        results = db.get_analysis_results(run_id)
        print(f"   ✅ Retrieved {len(results)} result(s)")

        # Display results summary
        print("\n5. Results Summary:")
        for result in results:
            print(f"\n   Year: {result['year']}")
            print(f"   Type: {result['type']}")
            print(f"   Data keys: {list(result['data'].keys())[:10]}...")

            # Show key takeaways if available
            if 'key_takeaways' in result['data']:
                print(f"   Key Takeaways:")
                for takeaway in result['data']['key_takeaways'][:3]:
                    print(f"     - {takeaway[:100]}...")

        print("\n" + "="*70)
        print("✅ TEST PASSED - Full workflow successful!")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n   ❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        print("❌ TEST FAILED")
        print("="*70)
        return False


def test_database_operations():
    """Test database operations."""
    print("\n" + "="*70)
    print("DATABASE OPERATIONS TEST")
    print("="*70)

    db = DatabaseRepository("data/test_db_ops.db")

    # Test creating a run
    print("\n1. Testing create_analysis_run...")
    db.create_analysis_run(
        run_id="test-run-123",
        ticker="TEST",
        analysis_type="fundamental",
        filing_type="10-K",
        years=[2024],
        config={'test': 'config'}
    )
    print("   ✅ Created analysis run")

    # Test updating status
    print("\n2. Testing update_run_status...")
    db.update_run_status("test-run-123", "running")
    status = db.get_run_status("test-run-123")
    assert status == "running"
    print(f"   ✅ Status updated to: {status}")

    # Test storing result
    print("\n3. Testing store_result...")
    db.store_result(
        run_id="test-run-123",
        ticker="TEST",
        fiscal_year=2024,
        filing_type="10-K",
        result_type="TenKAnalysis",
        result_data={'test': 'data', 'key_takeaways': ['test1', 'test2']}
    )
    print("   ✅ Stored result")

    # Test retrieving results
    print("\n4. Testing get_analysis_results...")
    results = db.get_analysis_results("test-run-123")
    assert len(results) == 1
    print(f"   ✅ Retrieved {len(results)} result(s)")

    # Test custom prompts
    print("\n5. Testing custom prompts...")
    prompt_id = db.save_prompt(
        name="Test Prompt",
        description="Test description",
        template="Analyze {ticker} for {year}",
        analysis_type="fundamental"
    )
    print(f"   ✅ Created prompt with ID: {prompt_id}")

    prompts = db.get_prompts_by_type("fundamental")
    assert len(prompts) >= 1
    print(f"   ✅ Retrieved {len(prompts)} prompt(s)")

    # Clean up
    db.delete_prompt(prompt_id)
    db.delete_analysis_run("test-run-123")
    print("   ✅ Cleaned up test data")

    print("\n✅ All database tests passed!")
    return True


if __name__ == "__main__":
    print("\n🧪 Starting comprehensive UI tests...\n")

    # Test 1: Database operations
    db_success = test_database_operations()

    # Test 2: Full analysis workflow (this takes time!)
    print("\n⚠️  WARNING: The next test will actually run a full analysis.")
    print("   This will:")
    print("   - Download a 10-K from SEC")
    print("   - Convert it to PDF")
    print("   - Send it to Gemini AI")
    print("   - Take 2-5 minutes and use API credits")
    print()

    response = input("Do you want to run the full analysis test? (y/n): ")

    if response.lower() == 'y':
        analysis_success = test_full_analysis_workflow()
    else:
        print("\n⏭️  Skipping full analysis test")
        analysis_success = None

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Database Operations: {'✅ PASSED' if db_success else '❌ FAILED'}")
    if analysis_success is not None:
        print(f"Full Analysis Workflow: {'✅ PASSED' if analysis_success else '❌ FAILED'}")
    else:
        print(f"Full Analysis Workflow: ⏭️  SKIPPED")
    print("="*70)

    if db_success and (analysis_success is None or analysis_success):
        print("\n🎉 All tests passed! The UI is ready to use.")
        print("\nTo launch the Streamlit app:")
        print("  cd fintel")
        print("  streamlit run streamlit_app.py")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
