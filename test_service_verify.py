#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fintel.ui.database import DatabaseRepository

db = DatabaseRepository("data/test_service.db")

# Get recent analyses
print("Recent analyses:")
runs = db.search_analyses(limit=10)
print(runs[['ticker', 'analysis_type', 'status']].to_string())

# Check specific run
run_id = runs.iloc[0]['run_id']
print(f"\nChecking run: {run_id}")
results = db.get_analysis_results(run_id)
print(f"Results: {len(results)}")
for r in results:
    print(f"  Year: {r['year']}, Type: {r['type']}")
    print(f"  Data keys: {list(r['data'].keys())[:10]}")
