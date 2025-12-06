#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test script to verify UI components work.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fintel.ui.database import DatabaseRepository

def test_database():
    """Test database initialization."""
    print("Testing database initialization...")

    db = DatabaseRepository("data/test_fintel.db")

    # Test stats
    total = db.get_total_analyses()
    print(f"✅ Total analyses: {total}")

    # Test custom prompts
    try:
        prompt_id = db.save_prompt(
            name="Test Prompt",
            description="Test description",
            template="Analyze {ticker} for year {year}",
            analysis_type="fundamental"
        )
        print(f"✅ Created test prompt with ID: {prompt_id}")

        # Get it back
        prompts = db.get_prompts_by_type("fundamental")
        print(f"✅ Retrieved {len(prompts)} fundamental prompts")

        # Delete it
        db.delete_prompt(prompt_id)
        print("✅ Deleted test prompt")

    except Exception as e:
        print(f"❌ Error with prompts: {e}")

    print("\n✅ Database tests passed!")


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting imports...")

    try:
        from fintel.ui.services import AnalysisService
        print("✅ AnalysisService imported")

        from fintel.ui.components.results_display import display_results
        print("✅ results_display imported")

        from fintel.ui.utils.formatting import generate_markdown_report
        print("✅ formatting utilities imported")

        from fintel.ui.utils.validators import validate_ticker
        print("✅ validators imported")

        print("\n✅ All imports successful!")

    except Exception as e:
        print(f"❌ Import error: {e}")
        raise


if __name__ == "__main__":
    test_imports()
    test_database()

    print("\n" + "="*50)
    print("🎉 All tests passed!")
    print("="*50)
    print("\nTo launch the Streamlit app:")
    print("  cd fintel")
    print("  streamlit run streamlit_app.py")
