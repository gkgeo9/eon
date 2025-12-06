#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 3: Random Company Analysis

Analyze an UNKNOWN/RANDOM company with objective assessment.

This uses the OBJECTIVE prompt that doesn't assume success or failure.
Use this for companies you're researching with no prior bias.
"""

from pathlib import Path
from fintel.analysis.fundamental.success_factors import ObjectiveCompanyAnalyzer
from fintel.analysis.comparative.benchmarking import BenchmarkComparator
from fintel.ai import APIKeyManager, RateLimiter
from fintel.core import get_logger

# Setup
logger = get_logger(__name__)

# Initialize AI components
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(max_requests_per_minute=15)

# Initialize analyzers
objective_analyzer = ObjectiveCompanyAnalyzer(
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

comparator = BenchmarkComparator(
    baseline_path=Path("top_50_meta_analysis.json"),
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

# Example: Analyze an unknown company
ticker = "XYZ"

logger.info(f"Analyzing {ticker} (objective assessment)")

# Step 1: Analyze multi-year patterns objectively
analyses_dir = Path("analyzed_10k") / ticker
output_dir = Path("random_company_factors")
output_dir.mkdir(parents=True, exist_ok=True)

success_factors = objective_analyzer.analyze_from_directory(
    ticker=ticker,
    analyses_dir=analyses_dir,
    output_dir=output_dir
)

print(f"\n{'='*80}")
print(f"OBJECTIVE ANALYSIS: {ticker}")
print(f"{'='*80}")
print(f"\nDistinguishing Characteristics:")
for i, char in enumerate(success_factors.distinguishing_characteristics, 1):
    print(f"{i}. {char}")

print(f"\nPerformance Factors:")
for factor in success_factors.performance_factors[:5]:
    print(f"\n  Factor: {factor.factor}")
    print(f"  Impact: {factor.business_impact}")
    print(f"  Development: {factor.development}")

# Step 2: Compare against top 50 to assess compounder potential
logger.info(f"Comparing {ticker} against top 50 baseline")

comparison_path = output_dir / f"{ticker}_comparison.json"
comparison = comparator.compare_against_baseline(
    success_factors=success_factors,
    output_file=comparison_path
)

# Print summary
comparator.print_summary(comparison)

# Interpret results
potential = comparison.compounder_potential
print(f"\n{'='*80}")
print(f"COMPOUNDER POTENTIAL ASSESSMENT")
print(f"{'='*80}")
if potential.score >= 75:
    print("⭐ This company shows STRONG alignment with proven compounders")
    print("   Consider deeper research as a potential investment")
elif potential.score >= 60:
    print("⚡ This company shows DEVELOPING potential")
    print("   Monitor key areas for improvement")
else:
    print("⚠️  This company has LIMITED alignment with compounders")
    print("   Significant gaps in foundational success factors")

logger.info(f"Analysis complete. Results saved to {output_dir}")
