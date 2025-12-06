#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test individual components of the UI system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_downloader():
    """Test SEC downloader."""
    print("\n" + "="*70)
    print("TEST: SEC Downloader")
    print("="*70)

    from fintel.data.sources.sec import SECDownloader

    downloader = SECDownloader()
    print(f"✅ Downloader initialized")
    print(f"   Base path: {downloader.base_path}")

    # Try downloading
    print("\nDownloading AAPL 10-K (1 filing)...")
    filing_dir = downloader.download("AAPL", num_filings=1, filing_type="10-K")

    if filing_dir and filing_dir.exists():
        print(f"✅ Downloaded to: {filing_dir}")
        # List files
        files = list(filing_dir.glob("**/*.txt"))
        print(f"   Found {len(files)} filing file(s)")
        for f in files[:3]:
            print(f"     - {f.name}")
        return True
    else:
        print(f"❌ Download failed")
        return False


def test_converter():
    """Test PDF converter."""
    print("\n" + "="*70)
    print("TEST: PDF Converter")
    print("="*70)

    from fintel.data.sources.sec import SECDownloader, SECConverter

    # First download
    downloader = SECDownloader()
    filing_dir = downloader.download("AAPL", num_filings=1)

    if not filing_dir:
        print("❌ Need filing to test converter")
        return False

    # Convert
    converter = SECConverter()
    print("Converting HTML to PDF...")

    pdf_files = converter.convert(
        ticker="AAPL",
        input_path=filing_dir,
        output_path=Path("data/test_pdfs")
    )

    if pdf_files and len(pdf_files) > 0:
        print(f"✅ Converted {len(pdf_files)} file(s)")
        for pdf_info in pdf_files:
            pdf_path = pdf_info['pdf_path']
            print(f"   PDF: {pdf_path}")
            print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
        return True
    else:
        print("❌ Conversion failed")
        return False


def test_analyzer():
    """Test analyzer with a real PDF."""
    print("\n" + "="*70)
    print("TEST: Fundamental Analyzer")
    print("="*70)

    from fintel.data.sources.sec import SECDownloader, SECConverter
    from fintel.analysis.fundamental import FundamentalAnalyzer
    from fintel.ai import APIKeyManager, RateLimiter
    from fintel.core import get_config

    # Get PDF
    downloader = SECDownloader()
    filing_dir = downloader.download("AAPL", num_filings=1)

    if not filing_dir:
        print("❌ Need filing")
        return False

    converter = SECConverter()
    pdf_files = converter.convert(
        ticker="AAPL",
        input_path=filing_dir,
        output_path=Path("data/test_pdfs")
    )

    if not pdf_files:
        print("❌ Need PDF")
        return False

    pdf_path = pdf_files[0]['pdf_path']
    print(f"Using PDF: {pdf_path}")

    # Create analyzer
    config = get_config()
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter()

    analyzer = FundamentalAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )
    print(f"✅ Analyzer created")
    print(f"   API keys available: {len(key_mgr.api_keys)}")

    # Analyze
    print("\nRunning analysis (this will take 1-3 minutes)...")
    result = analyzer.analyze_filing(
        pdf_path=pdf_path,
        ticker="AAPL",
        year=2024
    )

    if result:
        print(f"✅ Analysis completed!")
        print(f"   Result type: {type(result).__name__}")
        print(f"   Business model: {result.business_model[:100]}...")
        print(f"   Key takeaways: {len(result.key_takeaways)} items")
        for i, takeaway in enumerate(result.key_takeaways[:3], 1):
            print(f"     {i}. {takeaway[:80]}...")
        return True
    else:
        print("❌ Analysis failed")
        return False


def test_perspective_analyzer():
    """Test perspective analyzers (Buffett, Taleb, Contrarian)."""
    print("\n" + "="*70)
    print("TEST: Perspective Analyzer (Buffett Lens)")
    print("="*70)

    from fintel.data.sources.sec import SECDownloader, SECConverter
    from fintel.analysis.perspectives import PerspectiveAnalyzer
    from fintel.ai import APIKeyManager, RateLimiter
    from fintel.core import get_config

    # Get PDF
    downloader = SECDownloader()
    filing_dir = downloader.download("AAPL", num_filings=1)

    if not filing_dir:
        print("❌ Need filing")
        return False

    converter = SECConverter()
    pdf_files = converter.convert(
        ticker="AAPL",
        input_path=filing_dir,
        output_path=Path("data/test_pdfs")
    )

    if not pdf_files:
        print("❌ Need PDF")
        return False

    pdf_path = pdf_files[0]['pdf_path']

    # Create analyzer
    config = get_config()
    key_mgr = APIKeyManager(config.google_api_keys)
    rate_limiter = RateLimiter()

    analyzer = PerspectiveAnalyzer(
        api_key_manager=key_mgr,
        rate_limiter=rate_limiter
    )
    print(f"✅ Perspective analyzer created")

    # Analyze with Buffett lens
    print("\nRunning Buffett analysis (1-3 minutes)...")
    result = analyzer.analyze_buffett(
        pdf_path=pdf_path,
        ticker="AAPL",
        year=2024
    )

    if result:
        print(f"✅ Buffett analysis completed!")
        print(f"   Result type: {type(result).__name__}")
        # Try to access fields (schema may vary)
        try:
            print(f"   Fields: {list(result.model_dump().keys())[:10]}")
        except:
            print(f"   Result: {str(result)[:100]}...")
        return True
    else:
        print("❌ Analysis failed")
        return False


if __name__ == "__main__":
    print("\n🧪 COMPONENT TESTING SUITE")
    print("="*70)

    results = {}

    # Test 1: Downloader
    try:
        results['downloader'] = test_downloader()
    except Exception as e:
        print(f"\n❌ Downloader test failed: {e}")
        results['downloader'] = False

    # Test 2: Converter
    try:
        results['converter'] = test_converter()
    except Exception as e:
        print(f"\n❌ Converter test failed: {e}")
        results['converter'] = False

    # Test 3: Analyzer
    try:
        results['analyzer'] = test_analyzer()
    except Exception as e:
        print(f"\n❌ Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        results['analyzer'] = False

    # Test 4: Perspective Analyzer
    try:
        results['perspective'] = test_perspective_analyzer()
    except Exception as e:
        print(f"\n❌ Perspective test failed: {e}")
        import traceback
        traceback.print_exc()
        results['perspective'] = False

    # Summary
    print("\n" + "="*70)
    print("COMPONENT TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.capitalize():20s}: {status}")

    print("="*70)

    if all(results.values()):
        print("\n🎉 All component tests passed!")
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"\n⚠️  Some tests failed: {', '.join(failed)}")
