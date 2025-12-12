#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parallel batch processing for SEC filings.

Orchestrates parallel analysis across multiple API keys using ProcessPoolExecutor.
Supports progress tracking and resumption for long-running batch jobs.

Extracted patterns from 10K_automator/parallel_excellent_10k_processor.py
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

from fintel.core import get_logger, get_config
from fintel.ai import APIKeyManager, RateLimiter
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.processing.progress import ProgressTracker


# Module-level worker function for ProcessPoolExecutor
# (must be at module level to be picklable)
def _process_single_company(
    ticker: str,
    api_key: str,
    num_filings: int,
    session_id: str,
    progress_dir: Path,
    output_dir: Path,
    analysis_function: str = None
) -> Dict[str, Any]:
    """
    Worker function to process a single company.

    This function must be at module level for ProcessPoolExecutor pickling.

    Args:
        ticker: Company ticker symbol
        api_key: API key for this worker
        num_filings: Number of filings to process
        session_id: Batch session ID
        progress_dir: Progress tracking directory
        output_dir: Output directory for results
        analysis_function: Optional custom analysis function name

    Returns:
        Dictionary with processing results
    """
    from fintel.core import get_logger
    from fintel.ai import RateLimiter
    from fintel.ai.providers import GeminiProvider
    from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
    from fintel.analysis.fundamental import FundamentalAnalyzer, TenKAnalysis
    from fintel.processing.progress import ProgressTracker

    logger = get_logger(f"{__name__}.worker.{ticker}")

    result = {
        "ticker": ticker,
        "success": False,
        "filings_processed": 0,
        "error": None,
        "start_time": datetime.now().isoformat(),
        "end_time": None
    }

    try:
        logger.info(f"Starting processing for {ticker}")

        # Initialize progress tracker
        tracker = ProgressTracker(session_id, progress_dir)

        # Check if already completed
        if tracker.is_completed(ticker):
            logger.info(f"{ticker} already completed, skipping")
            result["success"] = True
            result["skipped"] = True
            result["end_time"] = datetime.now().isoformat()
            return result

        # Step 1: Download filings
        logger.info(f"Downloading {num_filings} filings for {ticker}")
        downloader = SECDownloader()
        filing_path = downloader.download(ticker, num_filings=num_filings)

        if not filing_path or not filing_path.exists():
            raise Exception(f"Failed to download filings for {ticker}")

        # Step 2: Convert to PDF
        logger.info(f"Converting filings to PDF for {ticker}")
        with SECConverter() as converter:
            pdf_paths = converter.convert(ticker, filing_path)

        if not pdf_paths:
            raise Exception(f"Failed to convert filings to PDF for {ticker}")

        logger.info(f"Converted {len(pdf_paths)} filings to PDF for {ticker}")

        # Step 3: Analyze each filing
        logger.info(f"Analyzing {len(pdf_paths)} filings for {ticker}")

        # Create rate limiter for this worker
        rate_limiter = RateLimiter(sleep_after_request=65, max_requests_per_day=500)

        # Create single-key manager for this worker
        from fintel.ai.key_manager import APIKeyManager
        key_mgr = APIKeyManager([api_key])

        # Create analyzer
        from fintel.analysis.fundamental import FundamentalAnalyzer
        analyzer = FundamentalAnalyzer(
            api_key_manager=key_mgr,
            rate_limiter=rate_limiter
        )

        # Analyze each PDF
        ticker_output_dir = output_dir / ticker
        ticker_output_dir.mkdir(parents=True, exist_ok=True)

        analyses = {}
        for pdf_path in pdf_paths:
            # Extract year from filename (assumes format like "AAPL_FILING-TYPE_2024.pdf")
            try:
                year = int(pdf_path.stem.split("_")[-1])
            except (ValueError, IndexError):
                logger.warning(f"Could not extract year from {pdf_path.name}, skipping")
                continue

            logger.info(f"Analyzing {ticker} {year}")

            analysis = analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year,
                schema=TenKAnalysis,
                output_dir=ticker_output_dir
            )

            if analysis:
                analyses[year] = analysis
                result["filings_processed"] += 1

        # Mark as completed
        tracker.mark_completed(ticker)

        result["success"] = True
        result["analyses_count"] = len(analyses)
        result["end_time"] = datetime.now().isoformat()

        logger.info(f"Successfully processed {ticker}: {result['filings_processed']} filings")

    except Exception as e:
        logger.error(f"Error processing {ticker}: {e}")
        result["error"] = str(e)
        result["end_time"] = datetime.now().isoformat()

        # Mark as failed in tracker
        if "tracker" in locals():
            tracker.mark_failed(ticker, str(e))

    return result


class ParallelProcessor:
    """
    Orchestrates parallel processing of multiple companies across API keys.

    Uses ProcessPoolExecutor to distribute work across multiple workers,
    each with its own API key and rate limiter.

    Example:
        processor = ParallelProcessor(
            api_keys=config.google_api_keys,
            session_id="batch_2024_12_05"
        )

        results = processor.process_batch(
            tickers=["AAPL", "MSFT", "GOOGL"],
            num_filings=10,
            output_dir=Path("./results")
        )
    """

    def __init__(
        self,
        api_keys: List[str],
        session_id: str,
        progress_dir: Path = None,
        max_workers: int = None
    ):
        """
        Initialize parallel processor.

        Args:
            api_keys: List of API keys (one worker per key)
            session_id: Unique session ID for this batch
            progress_dir: Directory for progress tracking
            max_workers: Max parallel workers (default: len(api_keys))
        """
        self.api_keys = api_keys
        self.session_id = session_id
        self.progress_dir = progress_dir or Path("./progress")
        self.progress_dir.mkdir(parents=True, exist_ok=True)

        # One worker per API key (or less if specified)
        self.max_workers = max_workers or len(api_keys)

        # Initialize progress tracker
        self.tracker = ProgressTracker(session_id, self.progress_dir)

        self.logger = get_logger(f"{__name__}.ParallelProcessor")
        self.logger.info(
            f"Initialized parallel processor: {self.max_workers} workers, "
            f"session {session_id}"
        )

    def process_batch(
        self,
        tickers: List[str],
        num_filings: int,
        output_dir: Path,
        skip_completed: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process a batch of tickers in parallel.

        Args:
            tickers: List of ticker symbols to process
            num_filings: Number of filings to process per ticker
            output_dir: Output directory for results
            skip_completed: Skip tickers already completed (default: True)

        Returns:
            Dictionary mapping ticker to processing result
        """
        self.logger.info(
            f"Starting batch processing: {len(tickers)} tickers, "
            f"{num_filings} filings each"
        )

        # Filter out completed tickers
        if skip_completed:
            remaining = self.tracker.get_remaining(tickers)
            self.logger.info(
                f"Filtered {len(tickers) - len(remaining)} completed tickers, "
                f"{len(remaining)} remaining"
            )
            tickers = remaining

        if not tickers:
            self.logger.info("No tickers to process")
            return {}

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Distribute tickers across workers
        ticker_batches = self._distribute_tickers(tickers)

        results = {}
        start_time = time.time()

        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = []
            for worker_id, ticker_batch in enumerate(ticker_batches):
                api_key = self.api_keys[worker_id % len(self.api_keys)]

                for ticker in ticker_batch:
                    future = executor.submit(
                        _process_single_company,
                        ticker=ticker,
                        api_key=api_key,
                        num_filings=num_filings,
                        session_id=self.session_id,
                        progress_dir=self.progress_dir,
                        output_dir=output_dir
                    )
                    futures.append((ticker, future))

            # Collect results as they complete
            completed = 0
            total = len(futures)

            for ticker, future in futures:
                try:
                    result = future.result()
                    results[ticker] = result
                    completed += 1

                    status = "" if result["success"] else ""
                    self.logger.info(
                        f"{status} {ticker} ({completed}/{total}, "
                        f"{(completed/total)*100:.1f}%)"
                    )

                except Exception as e:
                    self.logger.error(f"Error processing {ticker}: {e}")
                    results[ticker] = {
                        "ticker": ticker,
                        "success": False,
                        "error": str(e)
                    }
                    completed += 1

        elapsed = time.time() - start_time
        self.logger.info(
            f"Batch processing complete: {completed}/{total} tickers "
            f"in {elapsed/60:.1f} minutes"
        )

        # Save summary
        self._save_summary(results, output_dir)

        return results

    def _distribute_tickers(self, tickers: List[str]) -> List[List[str]]:
        """
        Distribute tickers evenly across workers.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of ticker batches (one per worker)
        """
        batches = [[] for _ in range(self.max_workers)]

        for i, ticker in enumerate(tickers):
            worker_id = i % self.max_workers
            batches[worker_id].append(ticker)

        self.logger.debug(
            f"Distributed {len(tickers)} tickers across {self.max_workers} workers: "
            f"{[len(b) for b in batches]}"
        )

        return batches

    def _save_summary(self, results: Dict[str, Dict], output_dir: Path):
        """
        Save batch processing summary.

        Args:
            results: Processing results
            output_dir: Output directory
        """
        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_tickers": len(results),
            "successful": sum(1 for r in results.values() if r.get("success")),
            "failed": sum(1 for r in results.values() if not r.get("success")),
            "results": results
        }

        summary_file = output_dir / f"batch_summary_{self.session_id}.json"

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Saved batch summary to {summary_file}")

    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress statistics.

        Returns:
            Dictionary with progress stats
        """
        return self.tracker.get_stats()
