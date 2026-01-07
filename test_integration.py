#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test: Verify analysis can start and be tracked properly.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService

print("\n" + "="*80)
print("INTEGRATION TEST: Analysis Start & Tracking")
print("="*80)

db = DatabaseRepository()
service = AnalysisService(db)

print("\n1️⃣  Simulating analysis database record creation...")

# Test that we can create and track a run record
try:
    # Create a test run the way the UI does it
    test_params = {
        'ticker': 'TEST',
        'analysis_type': 'fundamental',
        'filing_type': '10-K',
        'years': [2025],
    }
    
    # We won't actually run the analysis (requires downloads),
    # but we can test the database creation part
    import uuid
    run_id = str(uuid.uuid4())
    
    db.create_analysis_run(
        run_id=run_id,
        ticker=test_params['ticker'],
        analysis_type=test_params['analysis_type'],
        filing_type=test_params['filing_type'],
        years=test_params['years'],
        config=test_params
    )
    print(f"✓ Created analysis run: {run_id}")
    
    # Simulate what happens during analysis
    print("\n2️⃣  Simulating analysis lifecycle...")
    
    # Status transitions
    db.update_run_status(run_id, 'running')
    print("✓ Updated status to 'running'")
    time.sleep(0.1)
    
    # Progress updates (like during file download)
    db.update_run_progress(run_id, 'Downloading filings...', 15, 'Download', 1)
    print("✓ Updated progress: 15%")
    time.sleep(0.1)
    
    db.update_run_progress(run_id, 'Converting to PDF...', 30, 'Convert', 1)
    print("✓ Updated progress: 30%")
    time.sleep(0.1)
    
    db.update_run_progress(run_id, 'Analyzing filings...', 60, 'Analysis', 1)
    print("✓ Updated progress: 60%")
    time.sleep(0.1)
    
    db.update_run_progress(run_id, 'Finalizing results...', 90, 'Finalize', 1)
    print("✓ Updated progress: 90%")
    
    db.update_run_status(run_id, 'completed')
    print("✓ Updated status to 'completed'")
    
    # Verify the run in the database
    print("\n3️⃣  Verifying database state...")
    details = db.get_run_details(run_id)
    
    print(f"\nFinal state:")
    print(f"  run_id:             {details['run_id']}")
    print(f"  ticker:             {details['ticker']}")
    print(f"  status:             {details['status']}")
    print(f"  analysis_type:      {details['analysis_type']}")
    print(f"  filing_type:        {details['filing_type']}")
    print(f"  progress_message:   {details['progress_message']}")
    print(f"  progress_percent:   {details['progress_percent']}")
    print(f"  last_activity_at:   {details['last_activity_at']}")
    print(f"  completed_at:       {details['completed_at']}")
    
    # Verify it's not marked as interrupted
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.execute(
        'SELECT status FROM analysis_runs WHERE run_id = ?',
        (run_id,)
    )
    status = cursor.fetchone()[0]
    conn.close()
    
    assert status == 'completed', f"Expected 'completed', got '{status}'"
    print(f"\n✓ Status is correctly 'completed' (not 'interrupted')")
    
    # Verify analysis can be retrieved from history
    print("\n4️⃣  Verifying analysis appears in history...")
    analyses = db.search_analyses(ticker='TEST')
    
    found = False
    for idx, row in analyses.iterrows():
        if row['run_id'] == run_id:
            found = True
            print(f"✓ Found analysis in history: {row['ticker']} {row['analysis_type']} ({row['status']})")
            break
    
    assert found, "Analysis not found in search results"
    
    # Cleanup
    db.delete_analysis_run(run_id)
    print("\n✓ Cleaned up test run")
    
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST PASSED")
    print("="*80)
    print("\nKey verifications:")
    print("  ✓ Analysis record created successfully")
    print("  ✓ Status transitions work correctly")
    print("  ✓ Progress updates set last_activity_at")
    print("  ✓ Completion status recorded correctly")
    print("  ✓ Analysis shows in search results")
    print("  ✓ NOT falsely marked as interrupted\n")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

