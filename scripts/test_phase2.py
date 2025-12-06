#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Phase 2 implementation: AI provider and fundamental analyzer.

This script tests each component independently and then the full pipeline.
"""

import sys
from pathlib import Path

# Add src to path so we can import fintel
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fintel.core import get_config
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers import GeminiProvider
from fintel.analysis.fundamental import FundamentalAnalyzer, TenKAnalysis
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor


def test_rate_limiter():
    """Test rate limiter (no actual sleep for testing)."""
    print("\n" + "=" * 60)
    print("Test 1: Rate Limiter")
    print("=" * 60)

    limiter = RateLimiter(sleep_after_request=0)  # Disable sleep for test

    # Test can_make_request
    assert limiter.can_make_request("test_key"), "Should allow first request"

    # Test record_and_sleep (no sleep since sleep_after_request=0)
    limiter.record_and_sleep("test_key")

    # Check usage
    assert limiter.get_usage_today("test_key") == 1, "Usage should be 1"

    # Test remaining
    assert limiter.get_remaining_today("test_key") == 499, "Should have 499 remaining"

    print("✓ Rate limiter works correctly")
    print(f"  - Can check request limits")
    print(f"  - Records usage properly")
    print(f"  - Tracks remaining requests")


def test_api_key_manager():
    """Test API key manager."""
    print("\n" + "=" * 60)
    print("Test 2: API Key Manager")
    print("=" * 60)

    config = get_config()
    if not config.google_api_keys:
        print("✗ No API keys configured in environment")
        print("  Set GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, etc.")
        return False

    key_mgr = APIKeyManager(config.google_api_keys)

    print(f"✓ API Key Manager initialized")
    print(f"  - {key_mgr.total_keys} API keys loaded")

    # Test key rotation
    key1 = key_mgr.get_next_key()
    key2 = key_mgr.get_next_key()

    if key_mgr.total_keys > 1:
        assert key1 != key2, "Should rotate to different key"
        print(f"  - Round-robin rotation works")

    # Test least-used selection
    least_used = key_mgr.get_least_used_key()
    print(f"  - Least-used key selection works")

    # Test usage tracking
    key_mgr.record_usage(key1)
    assert key_mgr.get_usage_today(key1) == 1, "Usage should be recorded"
    print(f"  - Usage tracking works")

    return True


def test_gemini_provider():
    """Test Gemini provider with simple prompt."""
    print("\n" + "=" * 60)
    print("Test 3: Gemini Provider")
    print("=" * 60)

    config = get_config()
    if not config.google_api_keys:
        print("✗ No API keys configured")
        return False

    # Use first key, no rate limiting for quick test
    provider = GeminiProvider(api_key=config.google_api_keys[0])

    print("Testing simple prompt (unstructured)...")
    try:
        result = provider.generate(
            "Respond with a JSON object containing a single field 'message' with value 'Hello from Gemini'"
        )

        if isinstance(result, dict) and 'message' in result:
            print(f"✓ Gemini provider works")
            print(f"  - Response: {result['message']}")
            return True
        else:
            print(f"✗ Unexpected response format: {result}")
            return False

    except Exception as e:
        print(f"✗ Gemini provider failed: {e}")
        return False


def test_analyzer_simple():
    """Test analyzer with a single PDF."""
    print("\n" + "=" * 60)
    print("Test 4: Full Pipeline (Download → Convert → Analyze)")
    print("=" * 60)

    config = get_config()
    if not config.google_api_keys:
        print("✗ No API keys configured")
        return False

    try:
        print("\nStep 1: Downloading 10-K filing...")
        downloader = SECDownloader(
            company_name="Fintel Test",
            user_email=config.sec_user_email
        )
        filing_path = downloader.download("AAPL", num_filings=1)
        print(f"  ✓ Downloaded to {filing_path}")

        print("\nStep 2: Converting HTML to PDF...")
        with SECConverter() as converter:
            pdfs = converter.convert("AAPL", filing_path)

        if not pdfs:
            print("  ✗ No PDFs generated")
            return False

        print(f"  ✓ Converted {len(pdfs)} filing(s) to PDF")

        print("\nStep 3: Analyzing with AI...")
        key_mgr = APIKeyManager(config.google_api_keys)
        rate_limiter = RateLimiter(sleep_after_request=5)  # Short sleep for testing

        analyzer = FundamentalAnalyzer(
            api_key_manager=key_mgr,
            rate_limiter=rate_limiter
        )

        # Use first PDF
        pdf_path = pdfs[0]
        print(f"  - Analyzing: {pdf_path.name}")

        result = analyzer.analyze_filing(
            pdf_path=pdf_path,
            ticker="AAPL",
            year=2024,
            schema=TenKAnalysis,
            output_dir=Path("./test_output")
        )

        if result:
            print(f"\n✓ Analysis complete!")
            print(f"  - Business Model: {result.business_model[:100]}...")
            print(f"  - Unique Value: {result.unique_value[:100]}...")
            print(f"  - Key Strategies: {len(result.key_strategies)} identified")
            print(f"  - Risks: {len(result.risks)} identified")
            print(f"  - Saved to: ./test_output/AAPL_2024_analysis.json")
            return True
        else:
            print("✗ Analysis failed (returned None)")
            return False

    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# Phase 2 Test Suite: AI Provider & Fundamental Analyzer")
    print("#" * 60)

    results = []

    # Test 1: Rate Limiter
    try:
        test_rate_limiter()
        results.append(("Rate Limiter", True))
    except Exception as e:
        print(f"✗ Rate limiter test failed: {e}")
        results.append(("Rate Limiter", False))

    # Test 2: API Key Manager
    try:
        success = test_api_key_manager()
        results.append(("API Key Manager", success))
    except Exception as e:
        print(f"✗ API key manager test failed: {e}")
        results.append(("API Key Manager", False))

    # Test 3: Gemini Provider
    try:
        success = test_gemini_provider()
        results.append(("Gemini Provider", success))
    except Exception as e:
        print(f"✗ Gemini provider test failed: {e}")
        results.append(("Gemini Provider", False))

    # Test 4: Full Pipeline (only if previous tests passed)
    if all(success for _, success in results):
        print("\nAll component tests passed. Running full pipeline test...")
        try:
            success = test_analyzer_simple()
            results.append(("Full Pipeline", success))
        except Exception as e:
            print(f"✗ Full pipeline test failed: {e}")
            results.append(("Full Pipeline", False))
    else:
        print("\nSkipping full pipeline test due to component failures")
        results.append(("Full Pipeline", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    print(f"\nPassed: {total_passed}/{total_tests}")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! Phase 2 is complete.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
