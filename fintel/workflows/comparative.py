#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comparative analysis workflows.

High-level orchestration for complete comparative analysis pipelines:
1. Excellent company analysis → Compare to top 50
2. Random company analysis → Compare to top 50
3. Batch contrarian scanning

Consolidates the full 10K_automator workflow into convenient methods.
"""

from pathlib import Path
from typing import List, Optional, Union
from pydantic import BaseModel

from fintel.core import get_logger, get_config
from fintel.ai import APIKeyManager, RateLimiter
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.fundamental import FundamentalAnalyzer
from fintel.analysis.fundamental.success_factors import (
    ExcellentCompanyAnalyzer,
    ObjectiveCompanyAnalyzer
)
from fintel.analysis.comparative.benchmarking import BenchmarkComparator
from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
from fintel.processing.progress import ProgressTracker


class ComparativeAnalysisWorkflow:
    """
    Complete comparative analysis workflows.

    Orchestrates the full pipeline from 10-K download through
    comparative analysis against top 50 baseline.

    Example:
        # Initialize workflow
        workflow = ComparativeAnalysisWorkflow(
            api_key_manager=key_mgr,
            rate_limiter=rate_limiter,
            baseline_path=Path("top_50_meta_analysis.json")
        )

        # Analyze an excellent company
        result = workflow.analyze_excellent_company(
            ticker="AAPL",
            num_years=10,
            output_dir=Path("output")
        )

        # Analyze a random company
        result = workflow.analyze_random_company(
            ticker="XYZ",
            num_years=10,
            output_dir=Path("output")
        )

        # Batch contrarian scan
        results = workflow.batch_contrarian_scan(
            tickers=["AAPL", "MSFT", "GOOGL"],
            output_dir=Path("contrarian_scans")
        )
    """

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        baseline_path: Path,
        data_dir: Optional[Path] = None,
        model: str = None,
        thinking_budget: int = None
    ):
        """
        Initialize the comparative analysis workflow.

        Args:
            api_key_manager: Manager for API key rotation
            rate_limiter: Rate limiter for API calls
            baseline_path: Path to top 50 meta-analysis JSON
            data_dir: Directory for downloaded 10-Ks (default: ./data)
            model: LLM model name (default from config)
            thinking_budget: Thinking budget (default from config)
        """
        self.api_key_manager = api_key_manager
        self.rate_limiter = rate_limiter
        self.baseline_path = baseline_path
        self.data_dir = data_dir or Path("data")
        self.model = model
        self.thinking_budget = thinking_budget

        self.logger = get_logger(f"{__name__}.ComparativeAnalysisWorkflow")

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all analysis components."""
        self.logger.info("Initializing workflow components")

        # Data acquisition
        self.downloader = SECDownloader(cache_dir=self.data_dir / "filings")
        self.converter = SECConverter()

        # Fundamental analysis
        self.fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            model=self.model,
            thinking_budget=self.thinking_budget
        )

        # Success factor analyzers (two paths)
        self.excellent_analyzer = ExcellentCompanyAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            model=self.model,
            thinking_budget=self.thinking_budget
        )

        self.objective_analyzer = ObjectiveCompanyAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            model=self.model,
            thinking_budget=self.thinking_budget
        )

        # Comparative analysis
        self.benchmark_comparator = BenchmarkComparator(
            baseline_path=self.baseline_path,
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            model=self.model,
            thinking_budget=self.thinking_budget
        )

        self.contrarian_scanner = ContrarianScanner(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            model=self.model,
            thinking_budget=self.thinking_budget
        )

        self.logger.info("Workflow components initialized")

    def analyze_excellent_company(
        self,
        ticker: str,
        num_years: int = 10,
        output_dir: Optional[Path] = None
    ) -> dict:
        """
        Complete analysis workflow for KNOWN EXCELLENT companies.

        Pipeline:
        1. Download 10-Ks for past N years
        2. Run fundamental analysis on each
        3. Analyze success factors (excellent company prompt)
        4. Compare against top 50 baseline
        5. Save all results

        Args:
            ticker: Company ticker symbol
            num_years: Number of years to analyze
            output_dir: Output directory (default: ./output/{ticker})

        Returns:
            Dictionary with paths to all generated files
        """
        if not output_dir:
            output_dir = Path("output") / ticker

        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Starting excellent company analysis for {ticker}")

        results = {
            "ticker": ticker,
            "analysis_type": "excellent",
            "filings": [],
            "analyses": [],
            "success_factors": None,
            "benchmark_comparison": None
        }

        try:
            # Step 1: Download 10-Ks
            self.logger.info(f"Step 1/4: Downloading {num_years} years of 10-Ks for {ticker}")
            filings_dir = output_dir / "filings"
            filings_dir.mkdir(exist_ok=True)

            # TODO: Implement download logic
            # For now, assume filings already exist

            # Step 2: Run fundamental analysis
            self.logger.info(f"Step 2/4: Running fundamental analysis")
            analyses_dir = output_dir / "analyses"
            analyses_dir.mkdir(exist_ok=True)

            # TODO: Implement batch fundamental analysis
            # For now, assume analyses already exist

            # Step 3: Analyze success factors (excellent path)
            self.logger.info(f"Step 3/4: Analyzing success factors (excellent company prompt)")
            success_factors_dir = output_dir / "success_factors"
            success_factors_dir.mkdir(exist_ok=True)

            success_factors = self.excellent_analyzer.analyze_from_directory(
                ticker=ticker,
                analyses_dir=analyses_dir,
                output_dir=success_factors_dir
            )

            success_factors_path = success_factors_dir / f"{ticker}_success_factors.json"
            results["success_factors"] = str(success_factors_path)

            # Step 4: Compare against top 50
            self.logger.info(f"Step 4/4: Comparing against top 50 baseline")
            comparison_dir = output_dir / "comparisons"
            comparison_dir.mkdir(exist_ok=True)

            comparison_path = comparison_dir / f"{ticker}_benchmark_comparison.json"
            comparison = self.benchmark_comparator.compare_against_baseline(
                success_factors=success_factors,
                output_file=comparison_path
            )

            results["benchmark_comparison"] = str(comparison_path)

            # Print summary
            self.benchmark_comparator.print_summary(comparison)

            self.logger.info(f"Excellent company analysis complete for {ticker}")
            return results

        except Exception as e:
            self.logger.error(f"Excellent company analysis failed for {ticker}: {e}")
            raise

    def analyze_random_company(
        self,
        ticker: str,
        num_years: int = 10,
        output_dir: Optional[Path] = None
    ) -> dict:
        """
        Complete analysis workflow for RANDOM/UNKNOWN companies.

        Pipeline:
        1. Download 10-Ks for past N years
        2. Run fundamental analysis on each
        3. Analyze success factors (objective prompt)
        4. Compare against top 50 baseline
        5. Save all results

        Args:
            ticker: Company ticker symbol
            num_years: Number of years to analyze
            output_dir: Output directory (default: ./output/{ticker})

        Returns:
            Dictionary with paths to all generated files
        """
        if not output_dir:
            output_dir = Path("output") / ticker

        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Starting random company analysis for {ticker}")

        results = {
            "ticker": ticker,
            "analysis_type": "random",
            "filings": [],
            "analyses": [],
            "success_factors": None,
            "benchmark_comparison": None
        }

        try:
            # Step 1: Download 10-Ks
            self.logger.info(f"Step 1/4: Downloading {num_years} years of 10-Ks for {ticker}")
            filings_dir = output_dir / "filings"
            filings_dir.mkdir(exist_ok=True)

            # TODO: Implement download logic

            # Step 2: Run fundamental analysis
            self.logger.info(f"Step 2/4: Running fundamental analysis")
            analyses_dir = output_dir / "analyses"
            analyses_dir.mkdir(exist_ok=True)

            # TODO: Implement batch fundamental analysis

            # Step 3: Analyze success factors (objective path)
            self.logger.info(f"Step 3/4: Analyzing success factors (objective prompt)")
            success_factors_dir = output_dir / "success_factors"
            success_factors_dir.mkdir(exist_ok=True)

            success_factors = self.objective_analyzer.analyze_from_directory(
                ticker=ticker,
                analyses_dir=analyses_dir,
                output_dir=success_factors_dir
            )

            success_factors_path = success_factors_dir / f"{ticker}_success_factors.json"
            results["success_factors"] = str(success_factors_path)

            # Step 4: Compare against top 50
            self.logger.info(f"Step 4/4: Comparing against top 50 baseline")
            comparison_dir = output_dir / "comparisons"
            comparison_dir.mkdir(exist_ok=True)

            comparison_path = comparison_dir / f"{ticker}_benchmark_comparison.json"
            comparison = self.benchmark_comparator.compare_against_baseline(
                success_factors=success_factors,
                output_file=comparison_path
            )

            results["benchmark_comparison"] = str(comparison_path)

            # Print summary
            self.benchmark_comparator.print_summary(comparison)

            self.logger.info(f"Random company analysis complete for {ticker}")
            return results

        except Exception as e:
            self.logger.error(f"Random company analysis failed for {ticker}: {e}")
            raise

    def batch_contrarian_scan(
        self,
        tickers: List[str],
        output_dir: Optional[Path] = None,
        resume: bool = True
    ) -> dict:
        """
        Run contrarian scanner on multiple companies.

        Args:
            tickers: List of ticker symbols
            output_dir: Output directory (default: ./contrarian_scans)
            resume: Resume from previous progress

        Returns:
            Dictionary mapping ticker to contrarian analysis path
        """
        if not output_dir:
            output_dir = Path("contrarian_scans")

        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Starting contrarian scan for {len(tickers)} companies")

        results = {}

        # Initialize progress tracker
        progress_file = output_dir / "progress.json"
        tracker = ProgressTracker(
            total_items=len(tickers),
            checkpoint_file=progress_file
        ) if resume else None

        for i, ticker in enumerate(tickers, 1):
            # Check if already completed
            if tracker and tracker.is_completed(ticker):
                self.logger.info(f"[{i}/{len(tickers)}] {ticker}: Already completed, skipping")
                continue

            self.logger.info(f"[{i}/{len(tickers)}] Running contrarian scan for {ticker}")

            try:
                # Load analyses (assume they exist)
                analyses_dir = Path("analyzed_10k") / ticker

                if not analyses_dir.exists():
                    self.logger.warning(f"{ticker}: No analyses found in {analyses_dir}, skipping")
                    continue

                # Run contrarian scan
                output_file = output_dir / f"{ticker}_contrarian.json"
                contrarian_analysis = self.contrarian_scanner.analyze_from_directory(
                    ticker=ticker,
                    analyses_dir=analyses_dir,
                    output_file=output_file
                )

                results[ticker] = str(output_file)

                # Mark as completed
                if tracker:
                    tracker.mark_completed(ticker)

                self.logger.info(f"{ticker}: Contrarian scan complete")

            except Exception as e:
                self.logger.error(f"{ticker}: Contrarian scan failed: {e}")
                if tracker:
                    tracker.mark_failed(ticker, str(e))

        self.logger.info(f"Batch contrarian scan complete: {len(results)}/{len(tickers)} successful")
        return results


__all__ = [
    'ComparativeAnalysisWorkflow',
]
