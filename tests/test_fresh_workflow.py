#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fresh Workflow Test - Verify end-to-end with new ticker (no cache).
This test uses a ticker that hasn't been analyzed before.
"""

import time
from eon.ui.database import DatabaseRepository
from eon.ui.services.analysis_service import AnalysisService
from eon.ui.services.workflow_service import WorkflowService

# Initialize services
db = DatabaseRepository()
analysis_service = AnalysisService(db)
workflow_service = WorkflowService(db, analysis_service)

print("=" * 70)
print("  FRESH WORKFLOW TEST - No Cache")
print("=" * 70)
print()
print("This test uses GOOGL which should not be in cache.")
print("It will download filings and run fresh analysis.")
print()

# Create workflow with GOOGL (likely not cached)
workflow = {
    "name": "Fresh Test: GOOGL Analysis",
    "description": "End-to-end test with fresh ticker (no cache)",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load GOOGL",
                "type": "input",
                "config": {
                    "tickers": ["GOOGL"],
                    "num_years": 1,
                    "filing_type": "10-K"
                }
            },
            {
                "step_id": "fundamental_1",
                "name": "Analyze",
                "type": "fundamental_analysis",
                "config": {
                    "run_mode": "per_filing"
                }
            },
            {
                "step_id": "export_1",
                "name": "Export",
                "type": "export",
                "config": {
                    "formats": ["json", "csv"],
                    "include_metadata": True,
                    "include_raw_data": True
                }
            }
        ]
    }
}

start_time = time.time()

try:
    # Save workflow
    print("[1/4] Saving workflow...")
    workflow_id = workflow_service.save_workflow(
        name=workflow['name'],
        description=workflow['description'],
        workflow_definition=workflow['workflow_definition']
    )
    print(f"  ✅ Workflow ID: {workflow_id}")

    # Execute
    print("\n[2/4] Executing workflow...")
    run_id = workflow_service.execute_workflow(workflow_id)
    print(f"  ✅ Run ID: {run_id}")
    print("  ⏳ This may take 1-2 minutes for fresh analysis...")

    # Monitor
    print("\n[3/4] Monitoring execution...")
    max_wait = 300  # 5 minutes
    wait_time = 0

    while wait_time < max_wait:
        status = workflow_service.get_run_status(run_id)

        if not status:
            print("  ❌ Status unavailable")
            break

        current_status = status['status']
        progress = status['current_step']
        total = status['total_steps']

        if current_status == 'completed':
            print(f"  ✅ Completed ({progress}/{total} steps)")
            break
        elif current_status == 'failed':
            errors = status.get('errors', [])
            print(f"  ❌ Failed: {errors}")
            break
        else:
            if wait_time % 10 == 0:
                print(f"  ⏳ Progress: {progress}/{total} steps ({status['progress_percent']}%)")
            time.sleep(2)
            wait_time += 2

    # Validate results
    if current_status == 'completed':
        print("\n[4/4] Validating results...")
        results = workflow_service.get_run_results(run_id)

        if results:
            print(f"  ✅ Shape: {results.shape}")
            print(f"  ✅ Items: {results.total_items}")
            print(f"  ✅ Tickers: {results.tickers}")

            exported_files = results.metadata.get('exported_files', [])
            print(f"  ✅ Exported {len(exported_files)} files:")
            for f in exported_files:
                print(f"     → {f}")

            duration = time.time() - start_time
            print(f"\n  ✅ TEST PASSED in {duration:.1f} seconds!")
            print("\n" + "=" * 70)
            print("  🎉 FRESH WORKFLOW WORKS END-TO-END!")
            print("=" * 70)
        else:
            print("  ❌ No results returned")
    else:
        print(f"\n  ❌ Workflow did not complete: {current_status}")

except Exception as e:
    print(f"\n  ❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print()
