#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example 4: Contrarian Scanning

Identify companies with contrarian characteristics that could indicate
hidden compounder potential.
"""

from pathlib import Path
from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
from fintel.ai import APIKeyManager, RateLimiter
from fintel.core import get_logger

# Setup
logger = get_logger(__name__)

# Initialize AI components
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(max_requests_per_minute=15)

# Initialize scanner
scanner = ContrarianScanner(
    api_key_manager=api_key_manager,
    rate_limiter=rate_limiter
)

# Example: Scan multiple companies for contrarian signals
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

output_dir = Path("contrarian_scans")
output_dir.mkdir(parents=True, exist_ok=True)

results = []

for ticker in tickers:
    logger.info(f"Scanning {ticker} for contrarian signals")

    try:
        # Assumes analyses exist in: analyzed_10k/TICKER/
        analyses_dir = Path("analyzed_10k") / ticker
        output_file = output_dir / f"{ticker}_contrarian.json"

        contrarian_analysis = scanner.analyze_from_directory(
            ticker=ticker,
            analyses_dir=analyses_dir,
            output_file=output_file
        )

        results.append({
            "ticker": ticker,
            "total_score": contrarian_analysis.total_score,
            "category": contrarian_analysis.category,
            "analysis": contrarian_analysis
        })

        print(f"\n{ticker}: {contrarian_analysis.total_score}/600 - {contrarian_analysis.category}")

    except Exception as e:
        logger.error(f"{ticker}: Scan failed: {e}")

# Sort by total score
results.sort(key=lambda x: x["total_score"], reverse=True)

# Print rankings
print(f"\n{'='*80}")
print(f"CONTRARIAN SCAN RANKINGS")
print(f"{'='*80}\n")

for i, result in enumerate(results, 1):
    analysis = result["analysis"]
    print(f"{i}. {result['ticker']}: {result['total_score']}/600 - {result['category']}")

    # Show top scoring dimension
    scores = [
        ("Strategic Anomaly", analysis.strategic_anomaly.score),
        ("Asymmetric Resources", analysis.asymmetric_resources.score),
        ("Contrarian Positioning", analysis.contrarian_positioning.score),
        ("Cross-Industry DNA", analysis.cross_industry_dna.score),
        ("Early Infrastructure", analysis.early_infrastructure.score),
        ("Intellectual Capital", analysis.intellectual_capital.score),
    ]
    top_dimension = max(scores, key=lambda x: x[1])
    print(f"   Top Dimension: {top_dimension[0]} ({top_dimension[1]}/100)")
    print()

print(f"Results saved to: {output_dir}")
print(f"{'='*80}\n")
