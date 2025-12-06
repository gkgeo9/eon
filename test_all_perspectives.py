#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test all perspective analyzers (Taleb, Contrarian, Multi-Perspective).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.ai import APIKeyManager, RateLimiter
from fintel.core import get_config


def setup_pdf():
    """Download and convert a PDF for testing."""
    print("Setting up test PDF...")

    downloader = SECDownloader()
    filing_dir = downloader.download("AAPL", num_filings=1, filing_type="10-K")

    if not filing_dir:
        print("❌ Download failed")
        return None

    converter = SECConverter()
    pdf_files = converter.convert(
        ticker="AAPL",
        input_path=filing_dir,
        output_path=Path("data/test_pdfs")
    )

    if not pdf_files:
        print("❌ Conversion failed")
        return None

    pdf_path = pdf_files[0]['pdf_path']
    print(f"✅ PDF ready: {pdf_path}")
    return pdf_path


def test_taleb_analysis(pdf_path):
    """Test Taleb perspective analyzer."""
    print("\n" + "="*70)
    print("TEST: Taleb Lens (Antifragility & Risks)")
    print("="*70)

    config = get_config()
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter()

    analyzer = PerspectiveAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )

    print("Running Taleb analysis (1-3 minutes)...")
    result = analyzer.analyze_taleb(
        pdf_path=pdf_path,
        ticker="AAPL",
        year=2024
    )

    if result:
        print(f"✅ Taleb analysis completed!")
        print(f"   Result type: {type(result).__name__}")
        try:
            data = result.model_dump()
            print(f"   Fields: {list(data.keys())[:10]}")
            # Check for expected fields
            if 'fragility_assessment' in data:
                print(f"   Fragility: {data['fragility_assessment'][:80]}...")
            if 'verdict' in data:
                print(f"   Verdict: {data['verdict']}")
        except Exception as e:
            print(f"   Result: {str(result)[:100]}...")
        return True
    else:
        print("❌ Analysis failed")
        return False


def test_contrarian_analysis(pdf_path):
    """Test Contrarian perspective analyzer."""
    print("\n" + "="*70)
    print("TEST: Contrarian Lens (Variant Perception)")
    print("="*70)

    config = get_config()
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter()

    analyzer = PerspectiveAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )

    print("Running Contrarian analysis (1-3 minutes)...")
    result = analyzer.analyze_contrarian(
        pdf_path=pdf_path,
        ticker="AAPL",
        year=2024
    )

    if result:
        print(f"✅ Contrarian analysis completed!")
        print(f"   Result type: {type(result).__name__}")
        try:
            data = result.model_dump()
            print(f"   Fields: {list(data.keys())[:10]}")
            if 'variant_perception' in data:
                print(f"   Variant perception: {data['variant_perception'][:80]}...")
            if 'verdict' in data:
                print(f"   Verdict: {data['verdict']}")
        except Exception as e:
            print(f"   Result: {str(result)[:100]}...")
        return True
    else:
        print("❌ Analysis failed")
        return False


def test_multi_perspective_analysis(pdf_path):
    """Test Multi-Perspective analyzer (all three lenses)."""
    print("\n" + "="*70)
    print("TEST: Multi-Perspective (Buffett + Taleb + Contrarian)")
    print("="*70)

    config = get_config()
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter()

    analyzer = PerspectiveAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )

    print("Running Multi-Perspective analysis (3-5 minutes)...")
    result = analyzer.analyze_multi_perspective(
        pdf_path=pdf_path,
        ticker="AAPL",
        year=2024
    )

    if result:
        print(f"✅ Multi-Perspective analysis completed!")
        print(f"   Result type: {type(result).__name__}")
        try:
            data = result.model_dump()
            print(f"   Fields: {list(data.keys())[:10]}")
            # Check for all three perspectives
            if 'buffett_analysis' in data:
                print(f"   ✓ Buffett perspective included")
            if 'taleb_analysis' in data:
                print(f"   ✓ Taleb perspective included")
            if 'contrarian_analysis' in data:
                print(f"   ✓ Contrarian perspective included")
        except Exception as e:
            print(f"   Result: {str(result)[:100]}...")
        return True
    else:
        print("❌ Analysis failed")
        return False


if __name__ == "__main__":
    print("\n🧪 PERSPECTIVE ANALYZERS TESTING SUITE")
    print("="*70)

    # Setup
    pdf_path = setup_pdf()
    if not pdf_path:
        print("\n❌ Failed to setup PDF for testing")
        sys.exit(1)

    results = {}

    # Test Taleb
    try:
        results['taleb'] = test_taleb_analysis(pdf_path)
    except Exception as e:
        print(f"\n❌ Taleb test failed: {e}")
        import traceback
        traceback.print_exc()
        results['taleb'] = False

    # Test Contrarian
    try:
        results['contrarian'] = test_contrarian_analysis(pdf_path)
    except Exception as e:
        print(f"\n❌ Contrarian test failed: {e}")
        import traceback
        traceback.print_exc()
        results['contrarian'] = False

    # Test Multi-Perspective
    try:
        results['multi'] = test_multi_perspective_analysis(pdf_path)
    except Exception as e:
        print(f"\n❌ Multi-Perspective test failed: {e}")
        import traceback
        traceback.print_exc()
        results['multi'] = False

    # Summary
    print("\n" + "="*70)
    print("PERSPECTIVE ANALYZERS TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.capitalize():20s}: {status}")

    print("="*70)

    if all(results.values()):
        print("\n🎉 All perspective analyzer tests passed!")
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"\n⚠️  Some tests failed: {', '.join(failed)}")
