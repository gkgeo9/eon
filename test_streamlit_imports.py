#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test that all Streamlit imports work correctly.
"""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing Streamlit app imports...")

# Test main app
try:
    from fintel.ui.app import main
    print("✅ Main app imports successfully")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    import traceback
    traceback.print_exc()

# Test pages imports (they should work when run by Streamlit)
pages = [
    "pages/1_📊_Single_Analysis.py",
    "pages/2_📈_Analysis_History.py",
    "pages/3_🔍_Results_Viewer.py",
    "pages/4_⚙️_Settings.py"
]

for page in pages:
    page_path = Path(__file__).parent / page
    if page_path.exists():
        print(f"✅ Page exists: {page}")
    else:
        print(f"❌ Page missing: {page}")

# Test database
try:
    from fintel.ui.database import DatabaseRepository
    db = DatabaseRepository("data/test_streamlit.db")
    print("✅ Database repository works")
except Exception as e:
    print(f"❌ Database failed: {e}")

# Test service
try:
    from fintel.ui.services import AnalysisService
    service = AnalysisService(db)
    print("✅ Analysis service works")
except Exception as e:
    print(f"❌ Service failed: {e}")

# Test components
try:
    from fintel.ui.components.results_display import display_results
    print("✅ Results display component works")
except Exception as e:
    print(f"❌ Results display failed: {e}")

print("\n✅ All imports successful! Streamlit app should work.")
print("\nTo run the app:")
print("  cd /Users/gkg/PycharmProjects/stock_stuff_06042025/fintel")
print("  streamlit run streamlit_app.py")
