#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the Nuclear workflow to verify the fix works.
"""

import time
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.analysis_service import AnalysisService
from fintel.ui.services.workflow_service import WorkflowService

# Initialize services
db = DatabaseRepository()
analysis_service = AnalysisService(db)
workflow_service = WorkflowService(db, analysis_service)

print("=" * 70)
print("  TESTING NUCLEAR WORKFLOW")
print("=" * 70)
print()
print("Workflow: Nuclear (NNE, OKLO, SMR)")
print("Steps:")
print("  1. Input - Get 3 tickers, 1 year, 10-K")
print("  2. Perspective Analysis - Buffett perspective")
print("  3. Aggregate - merge_all (FIXED from 'group')")
print("  4. Custom Analysis - Compare companies")
print()

workflow_id = 14  # Nuclear workflow

try:
    # Execute workflow
    print("[1/3] Executing workflow...")
    run_id = workflow_service.execute_workflow(workflow_id)
    print(f"  ✅ Run ID: {run_id}")
    print("  ⏳ This will take a few minutes (3 companies × Buffett analysis + comparison)...")
    print()

    # Monitor progress
    print("[2/3] Monitoring execution...")
    max_wait = 600  # 10 minutes
    wait_time = 0
    last_step = -1

    while wait_time < max_wait:
        status = workflow_service.get_run_status(run_id)

        if not status:
            print("  ❌ Status unavailable")
            break

        current_status = status['status']
        progress = status['current_step']
        total = status['total_steps']

        # Show progress update when step changes
        if progress != last_step:
            print(f"  ⏳ Step {progress}/{total} ({status['progress_percent']}%)")
            last_step = progress

        if current_status == 'completed':
            print(f"  ✅ Workflow completed!")
            break
        elif current_status == 'failed':
            errors = status.get('errors', [])
            print(f"  ❌ Failed at step {progress}/{total}")
            if errors:
                for error in errors:
                    print(f"     Error: {error.get('message', 'Unknown error')}")
            break
        else:
            time.sleep(3)
            wait_time += 3

    if wait_time >= max_wait:
        print(f"  ⏳ Timeout after {max_wait}s - workflow still running")
        print(f"     Check status later with run_id: {run_id}")

    # Get results if completed
    if current_status == 'completed':
        print()
        print("[3/3] Retrieving results...")
        results = workflow_service.get_run_results(run_id)

        if results:
            print(f"  ✅ Shape: {results.shape}")
            print(f"  ✅ Items: {results.total_items}")
            print(f"  ✅ Tickers: {results.tickers}")

            # Show comparison result
            if results.data:
                for ticker, years_data in results.data.items():
                    for year, data in years_data.items():
                        if data:
                            print()
                            print("  📊 Comparison Result:")
                            print(f"     {data}")
                            break
                    break

            print()
            print("  ✅ NUCLEAR WORKFLOW TEST PASSED!")
            print()
            print("=" * 70)
            print("  🎉 ALL STEPS EXECUTED SUCCESSFULLY!")
            print("=" * 70)
        else:
            print("  ❌ No results returned")

except Exception as e:
    print(f"\n  ❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print()
