#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module Test Suite

Tests that all fintel modules can be imported and initialized properly.
This runs without needing API keys or downloading data.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")

    try:
        from fintel.core import get_config, get_logger
        print("  Core modules: OK")
    except Exception as e:
        print(f"  Core modules: FAILED - {e}")
        return False

    try:
        from fintel.ai import APIKeyManager, RateLimiter
        print("  AI modules: OK")
    except Exception as e:
        print(f"  AI modules: FAILED - {e}")
        return False

    try:
        from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
        print("  SEC data modules: OK")
    except Exception as e:
        print(f"  SEC data modules: FAILED - {e}")
        return False

    try:
        from fintel.analysis.fundamental import FundamentalAnalyzer
        print("  Fundamental analysis: OK")
    except Exception as e:
        print(f"  Fundamental analysis: FAILED - {e}")
        return False

    try:
        from fintel.analysis.fundamental.success_factors import (
            ExcellentCompanyAnalyzer,
            ObjectiveCompanyAnalyzer
        )
        print("  Success factors analyzers: OK")
    except Exception as e:
        print(f"  Success factors analyzers: FAILED - {e}")
        return False

    try:
        from fintel.analysis.comparative.benchmarking import BenchmarkComparator
        print("  Benchmark comparator: OK")
    except Exception as e:
        print(f"  Benchmark comparator: FAILED - {e}")
        return False

    try:
        from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
        print("  Contrarian scanner: OK")
    except Exception as e:
        print(f"  Contrarian scanner: FAILED - {e}")
        return False

    try:
        from fintel.analysis.perspectives.analyzer import PerspectiveAnalyzer
        print("  Perspective analyzer: OK")
    except Exception as e:
        print(f"  Perspective analyzer: FAILED - {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from fintel.core import get_config
        config = get_config()

        print(f"  Data dir: {config.data_dir}")
        print(f"  Cache dir: {config.cache_dir}")
        print(f"  Log dir: {config.log_dir}")
        print(f"  API keys found: {len(config.google_api_keys)}")
        print(f"  Default model: {config.default_model}")
        print(f"  Thinking budget: {config.thinking_budget}")
        print("  Configuration: OK")
        return True
    except Exception as e:
        print(f"  Configuration: FAILED - {e}")
        return False


def test_models():
    """Test that Pydantic models can be instantiated."""
    print("\nTesting Pydantic models...")

    try:
        from fintel.analysis.fundamental.models.basic import (
            TenKAnalysis,
            FinancialHighlights
        )

        # Create sample model instances
        financial_highlights = FinancialHighlights(
            revenue="$100M, up 20% YoY",
            profit="$20M net income, 20% margin",
            cash_position="$50M cash, $10M debt"
        )

        analysis = TenKAnalysis(
            business_model="Test business model description",
            unique_value="Unique value proposition",
            key_strategies=["Strategy 1", "Strategy 2"],
            financial_highlights=financial_highlights,
            risks=["Risk 1", "Risk 2"],
            management_quality="High quality management",
            innovation="Strong innovation pipeline",
            competitive_position="Market leader in segment",
            esg_factors="Strong ESG performance",
            key_takeaways=["Takeaway 1", "Takeaway 2", "Takeaway 3"]
        )

        # Test serialization
        data = analysis.model_dump()
        assert data['business_model'] == "Test business model description"

        print("  TenKAnalysis model: OK")
        return True
    except Exception as e:
        print(f"  Models: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_manager():
    """Test API key manager with dummy keys."""
    print("\nTesting API key manager...")

    try:
        from fintel.ai import APIKeyManager

        # Create manager with dummy keys
        dummy_keys = ["key1", "key2", "key3"]
        manager = APIKeyManager(api_keys=dummy_keys, max_requests_per_day=100)

        # Test key rotation
        key1 = manager.get_next_key()
        key2 = manager.get_next_key()
        key3 = manager.get_next_key()
        key4 = manager.get_next_key()  # Should cycle back

        assert key4 == key1, "Key rotation failed"

        # Test least-used selection
        manager.record_usage("key1")
        manager.record_usage("key1")
        least_used = manager.get_least_used_key()
        assert least_used in ["key2", "key3"], "Least-used selection failed"

        # Test usage tracking
        assert manager.get_usage_today("key1") == 2
        assert manager.can_make_request("key1") is True

        print("  API key manager: OK")
        return True
    except Exception as e:
        print(f"  API key manager: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """Test rate limiter."""
    print("\nTesting rate limiter...")

    try:
        from fintel.ai import RateLimiter

        # Create rate limiter with 0 sleep for testing
        limiter = RateLimiter(sleep_after_request=0, max_requests_per_day=10)

        # Test usage tracking
        limiter.record_and_sleep("test_key")
        assert limiter.get_usage_today("test_key") == 1
        assert limiter.can_make_request("test_key") is True

        # Test remaining requests
        remaining = limiter.get_remaining_today("test_key")
        assert remaining == 9

        print("  Rate limiter: OK")
        return True
    except Exception as e:
        print(f"  Rate limiter: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("FINTEL MODULE TEST SUITE")
    print("="*80)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Models", test_models()))
    results.append(("API Key Manager", test_api_key_manager()))
    results.append(("Rate Limiter", test_rate_limiter()))

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
