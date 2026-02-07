#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for workflow execution.
Creates 5 test workflows with increasing complexity and executes them.
"""

import json
from eon.ui.database import DatabaseRepository
from eon.ui.services.analysis_service import AnalysisService
from eon.ui.services.workflow_service import WorkflowService

# Initialize services
db = DatabaseRepository()
analysis_service = AnalysisService(db)
workflow_service = WorkflowService(db, analysis_service)

# Test Workflow 1: Single step - Input only
workflow_1 = {
    "name": "Test 1: Input Only",
    "description": "Single step workflow - just define input",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load Companies",
                "type": "input",
                "config": {
                    "tickers": ["AAPL"],
                    "num_years": 1,
                    "filing_type": "10-K"
                }
            }
        ]
    }
}

# Test Workflow 2: Two steps - Input + Fundamental Analysis
workflow_2 = {
    "name": "Test 2: Input + Analysis",
    "description": "Two step workflow - input and fundamental analysis",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load Companies",
                "type": "input",
                "config": {
                    "tickers": ["AAPL"],
                    "num_years": 1,
                    "filing_type": "10-K"
                }
            },
            {
                "step_id": "fundamental_1",
                "name": "Analyze Fundamentals",
                "type": "fundamental_analysis",
                "config": {
                    "run_mode": "per_filing"
                }
            }
        ]
    }
}

# Test Workflow 3: Three steps - Input + Analysis + Export
workflow_3 = {
    "name": "Test 3: Input + Analysis + Export",
    "description": "Three step workflow with export",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load Companies",
                "type": "input",
                "config": {
                    "tickers": ["AAPL"],
                    "num_years": 1,
                    "filing_type": "10-K"
                }
            },
            {
                "step_id": "fundamental_1",
                "name": "Analyze Fundamentals",
                "type": "fundamental_analysis",
                "config": {
                    "run_mode": "per_filing"
                }
            },
            {
                "step_id": "export_1",
                "name": "Export Results",
                "type": "export",
                "config": {
                    "formats": ["json"],
                    "include_metadata": True,
                    "include_raw_data": True
                }
            }
        ]
    }
}

# Test Workflow 4: Four steps - Input + Analysis + Success Factors + Export
workflow_4 = {
    "name": "Test 4: Input + Analysis + Success + Export",
    "description": "Four step workflow with success factors",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load Companies",
                "type": "input",
                "config": {
                    "tickers": ["AAPL", "MSFT"],
                    "num_years": 2,
                    "filing_type": "10-K"
                }
            },
            {
                "step_id": "fundamental_1",
                "name": "Analyze Fundamentals",
                "type": "fundamental_analysis",
                "config": {
                    "run_mode": "per_filing"
                }
            },
            {
                "step_id": "success_1",
                "name": "Extract Success Factors",
                "type": "success_factors",
                "config": {
                    "analyzer_type": "objective",
                    "aggregate_by": "company"
                }
            },
            {
                "step_id": "export_1",
                "name": "Export Results",
                "type": "export",
                "config": {
                    "formats": ["json"],
                    "include_metadata": True,
                    "include_raw_data": True
                }
            }
        ]
    }
}

# Test Workflow 5: Five steps - Full pipeline
workflow_5 = {
    "name": "Test 5: Full Pipeline",
    "description": "Five step workflow with all major components",
    "workflow_definition": {
        "steps": [
            {
                "step_id": "input_1",
                "name": "Load Companies",
                "type": "input",
                "config": {
                    "tickers": ["AAPL"],
                    "num_years": 1,
                    "filing_type": "10-K"
                }
            },
            {
                "step_id": "fundamental_1",
                "name": "Analyze Fundamentals",
                "type": "fundamental_analysis",
                "config": {
                    "run_mode": "per_filing"
                }
            },
            {
                "step_id": "success_1",
                "name": "Extract Success Factors",
                "type": "success_factors",
                "config": {
                    "analyzer_type": "objective",
                    "aggregate_by": "company"
                }
            },
            {
                "step_id": "aggregate_1",
                "name": "Aggregate Results",
                "type": "aggregate",
                "config": {
                    "operation": "merge_all"
                }
            },
            {
                "step_id": "export_1",
                "name": "Export Results",
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

# Test workflows
workflows = [workflow_1, workflow_2, workflow_3, workflow_4, workflow_5]

print("=" * 60)
print("WORKFLOW EXECUTION TEST")
print("=" * 60)
print()

for i, wf in enumerate(workflows, 1):
    print(f"\n{'=' * 60}")
    print(f"TEST {i}: {wf['name']}")
    print(f"{'=' * 60}")
    print(f"Description: {wf['description']}")
    print(f"Steps: {len(wf['workflow_definition']['steps'])}")
    print()

    try:
        # Save workflow
        print(f"[1/3] Saving workflow...")
        workflow_id = workflow_service.save_workflow(
            name=wf['name'],
            description=wf['description'],
            workflow_definition=wf['workflow_definition']
        )
        print(f"  ✓ Workflow saved with ID: {workflow_id}")

        # Execute workflow
        print(f"[2/3] Executing workflow...")
        run_id = workflow_service.execute_workflow(workflow_id)
        print(f"  ✓ Workflow execution started with run_id: {run_id}")

        # Check status
        print(f"[3/3] Checking execution status...")
        status = workflow_service.get_run_status(run_id)

        if status:
            print(f"  ✓ Status: {status['status']}")
            print(f"  ✓ Progress: {status['current_step']}/{status['total_steps']} steps")

            if status['status'] == 'completed':
                # Get results
                results = workflow_service.get_run_results(run_id)
                if results:
                    print(f"  ✓ Results shape: {results.shape}")
                    print(f"  ✓ Total items: {results.total_items}")
                    if hasattr(results, 'metadata') and 'exported_files' in results.metadata:
                        print(f"  ✓ Exported files: {len(results.metadata['exported_files'])}")

                print(f"\n  ✅ TEST {i} PASSED!")
            elif status['status'] == 'failed':
                print(f"\n  ❌ TEST {i} FAILED!")
                print(f"  Errors: {status.get('errors', [])}")

                # Get logs for debugging
                logs = workflow_service.get_step_logs(run_id)
                if logs:
                    print(f"\n  Last 5 log entries:")
                    for log in logs[-5:]:
                        print(f"    [{log['log_level']}] {log['step_id']}: {log['message']}")
            else:
                print(f"\n  ⚠️  TEST {i} - Unexpected status: {status['status']}")
        else:
            print(f"  ❌ Could not retrieve status")
            print(f"\n  ❌ TEST {i} FAILED!")

    except Exception as e:
        print(f"\n  ❌ TEST {i} FAILED WITH EXCEPTION!")
        print(f"  Error: {type(e).__name__}: {str(e)}")
        import traceback
        print("\n  Traceback:")
        print(traceback.format_exc())

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("All tests completed. Check results above for details.")
print()
