#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 5: Component Demonstration

Demonstrates how each Fintel component works independently without requiring
full pipeline execution. This is useful for understanding and testing individual pieces.
"""

from pathlib import Path
from fintel.core import get_config, get_logger
from utils import init_components

logger = get_logger(__name__)

def demo_config():
    """Demonstrate configuration system."""
    print("\n" + "="*80)
    print("CONFIGURATION DEMO")
    print("="*80)

    config = get_config()

    print(f"\nAPI Keys configured: {config.num_api_keys}")
    print(f"Data directory: {config.data_dir}")
    print(f"Cache directory: {config.cache_dir}")
    print(f"Log directory: {config.log_dir}")
    print(f"Default model: {config.default_model}")
    print(f"Thinking budget: {config.thinking_budget} tokens")
    print(f"Max requests per day: {config.max_requests_per_day}")
    print(f"Sleep after request: {config.sleep_after_request} seconds")
    print(f"Storage backend: {config.storage_backend}")
    print(f"SEC user email: {config.sec_user_email}")


def demo_api_key_manager():
    """Demonstrate API key management."""
    print("\n" + "="*80)
    print("API KEY MANAGER DEMO")
    print("="*80)

    api_key_manager, _ = init_components()

    print(f"\nTotal keys: {api_key_manager.total_keys}")
    print(f"Available keys: {api_key_manager.available_keys_count}")

    # Show key rotation
    print("\nKey rotation (round-robin):")
    for i in range(5):
        key = api_key_manager.get_next_key()
        print(f"  Request {i+1}: Using key {key[:15]}...")

    # Show least-used selection
    print("\nLeast-used key selection:")
    api_key_manager.record_usage(api_key_manager.api_keys[0])
    api_key_manager.record_usage(api_key_manager.api_keys[0])
    api_key_manager.record_usage(api_key_manager.api_keys[1])

    least_used = api_key_manager.get_least_used_key()
    print(f"  Least used key: {least_used[:15]}...")

    # Show usage stats
    print("\nUsage statistics (top 3 keys):")
    stats = api_key_manager.get_usage_stats()
    for key_short, stat in list(stats.items())[:3]:
        print(f"  {key_short}: {stat['used_today']}/{stat['limit']} used "
              f"({stat['percentage_used']}%)")


def demo_rate_limiter():
    """Demonstrate rate limiting."""
    print("\n" + "="*80)
    print("RATE LIMITER DEMO")
    print("="*80)

    from fintel.ai import RateLimiter

    # Create limiter with 0 sleep for demo
    limiter = RateLimiter(sleep_after_request=0, max_requests_per_day=10)

    print(f"\nConfiguration:")
    print(f"  Sleep after request: {limiter.sleep_after_request} seconds")
    print(f"  Max requests per day: {limiter.max_requests_per_day}")

    # Simulate some requests
    test_key = "test_api_key"
    print(f"\nSimulating requests with key: {test_key}")

    for i in range(3):
        limiter.record_and_sleep(test_key)
        usage = limiter.get_usage_today(test_key)
        remaining = limiter.get_remaining_today(test_key)
        can_make = limiter.can_make_request(test_key)
        print(f"  Request {i+1}: Usage={usage}, Remaining={remaining}, Can make request={can_make}")


def demo_models():
    """Demonstrate Pydantic models."""
    print("\n" + "="*80)
    print("PYDANTIC MODELS DEMO")
    print("="*80)

    from fintel.analysis.fundamental.models.basic import TenKAnalysis, FinancialHighlights

    # Create a sample analysis
    financial_highlights = FinancialHighlights(
        revenue="$500B revenue, up 15% YoY",
        profit="$100B net income, 20% margin",
        cash_position="$150B cash, $50B debt"
    )

    analysis = TenKAnalysis(
        business_model="Technology company focused on consumer electronics and services",
        unique_value="Integrated hardware-software ecosystem with premium brand positioning",
        key_strategies=[
            "Expand services revenue",
            "Develop new product categories",
            "Strengthen supply chain resilience"
        ],
        financial_highlights=financial_highlights,
        risks=[
            "Supply chain disruptions",
            "Regulatory scrutiny in multiple markets",
            "Intense competition in key product segments"
        ],
        management_quality="Strong leadership with proven track record",
        innovation="Heavy R&D investment in emerging technologies",
        competitive_position="Market leader in premium segment",
        esg_factors="Committed to carbon neutrality by 2030",
        key_takeaways=[
            "Dominant market position with pricing power",
            "Services growth offsetting hardware maturity",
            "Strong balance sheet provides strategic flexibility"
        ]
    )

    print("\nSample 10-K Analysis:")
    print(f"\nBusiness Model:\n{analysis.business_model}")
    print(f"\nKey Strategies:")
    for i, strategy in enumerate(analysis.key_strategies, 1):
        print(f"  {i}. {strategy}")
    print(f"\nFinancial Highlights:")
    print(f"  Revenue: {analysis.financial_highlights.revenue}")
    print(f"  Profit: {analysis.financial_highlights.profit}")
    print(f"  Cash Position: {analysis.financial_highlights.cash_position}")

    # Show serialization
    print("\nModel can be serialized to JSON:")
    data = analysis.model_dump()
    print(f"  Keys: {list(data.keys())}")
    print(f"  Size: {len(str(data))} characters")


def demo_pdf_extractor():
    """Demonstrate PDF text extraction (if PDF available)."""
    print("\n" + "="*80)
    print("PDF EXTRACTOR DEMO")
    print("="*80)

    from fintel.data.sources.sec import PDFExtractor

    extractor = PDFExtractor()

    # Check if any PDF files exist in data directory
    pdf_path = Path("data/pdfs")
    if pdf_path.exists():
        pdf_files = list(pdf_path.glob("**/*.pdf"))
        if pdf_files:
            sample_pdf = pdf_files[0]
            print(f"\nFound PDF: {sample_pdf.name}")
            print(f"Extracting text...")

            try:
                text = extractor.extract_text(sample_pdf)
                if text:
                    print(f"  Extracted {len(text):,} characters")
                    print(f"  Preview (first 200 chars):\n  {text[:200]}...")
                else:
                    print("  No text extracted")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print("\nNo PDF files found in data/pdfs/")
            print("  Run example 01 first to download and convert a filing")
    else:
        print("\ndata/pdfs/ directory not found")
        print("  Run example 01 first to download and convert a filing")


def main():
    """Run all demonstrations."""
    print("="*80)
    print("FINTEL COMPONENT DEMONSTRATIONS")
    print("="*80)
    print("\nThis script demonstrates each Fintel component independently.")

    try:
        demo_config()
        demo_api_key_manager()
        demo_rate_limiter()
        demo_models()
        demo_pdf_extractor()

        print("\n" + "="*80)
        print("ALL DEMONSTRATIONS COMPLETED")
        print("="*80)

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
