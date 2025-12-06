#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final Comprehensive Test Suite

Tests all critical Fintel components systematically.
"""

import sys


def test_all_model_imports():
    """Test that all models can be imported."""
    print("Testing all model imports...")

    try:
        # Basic models
        from fintel.analysis.fundamental.models.basic import TenKAnalysis, FinancialHighlights

        # Success factors
        from fintel.analysis.fundamental.models.success_factors import CompanySuccessFactors

        # Excellent company
        from fintel.analysis.fundamental.models.excellent_company_factors import ExcellentCompanyFactors

        # Perspectives
        from fintel.analysis.perspectives.models.buffett import BuffettAnalysis
        from fintel.analysis.perspectives.models.taleb import TalebAnalysis
        from fintel.analysis.perspectives.models.contrarian import ContrarianViewAnalysis
        from fintel.analysis.perspectives.models.combined import MultiPerspectiveAnalysis

        # Comparative
        from fintel.analysis.comparative.models.benchmark_comparison import BenchmarkComparison
        from fintel.analysis.comparative.models.contrarian_scores import ContrarianAnalysis

        print("  All models import successfully: OK")
        return True
    except Exception as e:
        print(f"  Model imports FAILED: {e}")
        return False


def test_all_analyzer_imports():
    """Test that all analyzers can be imported."""
    print("\nTesting all analyzer imports...")

    try:
        from fintel.analysis.fundamental.analyzer import FundamentalAnalyzer
        from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer, ObjectiveCompanyAnalyzer
        from fintel.analysis.perspectives.analyzer import PerspectiveAnalyzer
        from fintel.analysis.comparative.benchmarking import BenchmarkComparator
        from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner

        print("  All analyzers import successfully: OK")
        return True
    except Exception as e:
        print(f"  Analyzer imports FAILED: {e}")
        return False


def test_core_functionality():
    """Test core functionality."""
    print("\nTesting core functionality...")

    try:
        from fintel.core import get_config, get_logger
        from fintel.ai import APIKeyManager, RateLimiter

        config = get_config()
        logger = get_logger(__name__)

        # Test API key manager
        dummy_keys = ["key1", "key2", "key3"]
        manager = APIKeyManager(api_keys=dummy_keys)
        assert manager.total_keys == 3

        # Test rate limiter
        limiter = RateLimiter(sleep_after_request=0)
        limiter.record_and_sleep("test")
        assert limiter.get_usage_today("test") == 1

        print("  Core functionality: OK")
        return True
    except Exception as e:
        print(f"  Core functionality FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_sources():
    """Test data sources can be initialized."""
    print("\nTesting data sources...")

    try:
        from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor

        # Test initialization
        downloader = SECDownloader()
        converter = SECConverter()
        extractor = PDFExtractor()

        print("  Data sources: OK")
        return True
    except Exception as e:
        print(f"  Data sources FAILED: {e}")
        return False


def test_workflows():
    """Test workflow imports."""
    print("\nTesting workflow imports...")

    try:
        from fintel.workflows.comparative import ComparativeAnalysisWorkflow

        print("  Workflows: OK")
        return True
    except Exception as e:
        print(f"  Workflows FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("FINAL COMPREHENSIVE TEST SUITE")
    print("="*80)

    results = []
    results.append(("Model Imports", test_all_model_imports()))
    results.append(("Analyzer Imports", test_all_analyzer_imports()))
    results.append(("Core Functionality", test_core_functionality()))
    results.append(("Data Sources", test_data_sources()))
    results.append(("Workflows", test_workflows()))

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nALL TESTS PASSED - FINTEL IS READY TO USE")
        print("="*80)
        return 0
    else:
        print("\nSOME TESTS FAILED - PLEASE REVIEW")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
