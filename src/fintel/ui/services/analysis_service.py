#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Service - wraps Fintel analyzers for UI consumption.

This service layer acts as an adapter between the Streamlit UI and
the existing fintel analysis modules, handling database persistence
and progress tracking.
"""

import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fintel.core import get_config, get_logger
from fintel.ai import APIKeyManager, RateLimiter
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
from fintel.analysis.fundamental import FundamentalAnalyzer
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.ui.database import DatabaseRepository


class AnalysisService:
    """
    Service layer that wraps Fintel analyzers for UI consumption.

    Handles:
    - Database persistence of analysis runs and results
    - File caching to avoid re-downloading
    - Integration with existing analyzer classes
    - Progress tracking
    """

    def __init__(self, db: DatabaseRepository):
        """
        Initialize analysis service.

        Args:
            db: Database repository instance
        """
        self.db = db
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Initialize shared components
        self.api_key_manager = APIKeyManager(self.config.google_api_keys)
        self.rate_limiter = RateLimiter()
        self.downloader = SECDownloader()
        self.converter = SECConverter()
        self.extractor = PDFExtractor()

        self.logger.info("AnalysisService initialized")

    def run_analysis(
        self,
        ticker: str,
        analysis_type: str,
        filing_type: str = "10-K",
        years: Optional[List[int]] = None,
        num_years: Optional[int] = None,
        custom_prompt: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> str:
        """
        Run analysis and return run_id for tracking.

        This method:
        1. Creates analysis_run record (status=pending)
        2. Downloads/converts filings
        3. Runs appropriate analyzer
        4. Stores results in database
        5. Updates status

        Args:
            ticker: Company ticker symbol
            analysis_type: Type of analysis (fundamental, excellent, buffett, etc.)
            filing_type: Filing type (10-K, 10-Q, 8-K)
            years: Specific years to analyze
            num_years: Number of recent years (alternative to years)
            custom_prompt: Optional custom prompt template
            company_name: Optional company name

        Returns:
            run_id (UUID string) for tracking progress

        Raises:
            ValueError: If invalid parameters
            Exception: If analysis fails
        """
        run_id = str(uuid.uuid4())

        # Determine years to analyze
        if years is None and num_years:
            current_year = datetime.now().year
            years = list(range(current_year, current_year - num_years, -1))
        elif years is None:
            years = [datetime.now().year]  # Default to current year

        self.logger.info(
            f"Starting {analysis_type} analysis for {ticker} "
            f"({filing_type}, years: {years})"
        )

        # Create run record
        self.db.create_analysis_run(
            run_id=run_id,
            ticker=ticker,
            analysis_type=analysis_type,
            filing_type=filing_type,
            years=years,
            config={
                'custom_prompt': custom_prompt,
                'model': self.config.default_model,
                'thinking_budget': self.config.thinking_budget,
                'filing_type': filing_type
            },
            company_name=company_name
        )

        try:
            self.db.update_run_status(run_id, 'running')

            # Download/retrieve filings
            pdf_paths = self._get_or_download_filings(ticker, filing_type, years)

            # Check if we have any PDFs
            if not pdf_paths:
                raise ValueError(
                    f"No {filing_type} filings could be downloaded/found for {ticker}. "
                    "Please check the ticker symbol and try again."
                )

            self.logger.info(f"Ready to analyze {len(pdf_paths)} years: {list(pdf_paths.keys())}")

            # Run analysis based on type
            if analysis_type == 'fundamental':
                results = self._run_fundamental_analysis(
                    ticker, pdf_paths, custom_prompt
                )
            elif analysis_type == 'excellent':
                results = self._run_excellent_analysis(ticker, pdf_paths)
            elif analysis_type == 'objective':
                results = self._run_objective_analysis(ticker, pdf_paths)
            elif analysis_type == 'buffett':
                results = self._run_buffett_analysis(ticker, pdf_paths)
            elif analysis_type == 'taleb':
                results = self._run_taleb_analysis(ticker, pdf_paths)
            elif analysis_type == 'contrarian':
                results = self._run_contrarian_analysis(ticker, pdf_paths)
            elif analysis_type == 'multi':
                results = self._run_multi_perspective(ticker, pdf_paths)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")

            # Store results
            for year, result in results.items():
                if result:  # Only store successful results
                    self.db.store_result(
                        run_id=run_id,
                        ticker=ticker,
                        fiscal_year=year,
                        filing_type=filing_type,
                        result_type=type(result).__name__,
                        result_data=result.model_dump()
                    )

            self.db.update_run_status(run_id, 'completed')
            self.logger.info(f"Analysis completed successfully: {run_id}")

        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        return run_id

    def _get_or_download_filings(
        self,
        ticker: str,
        filing_type: str,
        years: List[int]
    ) -> Dict[int, Path]:
        """
        Download filings or retrieve from cache.

        Args:
            ticker: Company ticker
            filing_type: Filing type (10-K, 10-Q, etc.)
            years: List of years

        Returns:
            Dictionary mapping year to PDF path
        """
        pdf_paths = {}

        for year in years:
            # Check cache first
            cached = self.db.get_cached_file(ticker, year, filing_type)
            if cached and Path(cached).exists():
                self.logger.info(f"Using cached file for {ticker} {year}: {cached}")
                pdf_paths[year] = Path(cached)
                continue

            # Download and convert
            try:
                self.logger.info(f"Downloading {ticker} {filing_type} for {year}")

                # Download filing (get more than 1 since we can't filter by specific year easily)
                filing_dir = self.downloader.download(
                    ticker=ticker,
                    num_filings=10,  # Download recent filings to find the right year
                    filing_type=filing_type
                )

                if not filing_dir:
                    self.logger.error(f"Failed to download filings for {ticker}")
                    continue

                # Convert to PDF
                pdf_files = self.converter.convert(
                    ticker=ticker,
                    input_path=filing_dir,
                    output_path=self.config.get_data_path("pdfs")
                )

                if pdf_files:
                    # Find the PDF for the requested year (use most recent for now)
                    # TODO: Better year matching logic
                    pdf_path = pdf_files[0]['pdf_path']
                    pdf_paths[year] = Path(pdf_path)

                    # Cache it
                    self.db.cache_file(ticker, year, filing_type, str(pdf_path))
                    self.logger.info(f"Cached file for {ticker} {year}: {pdf_path}")
                else:
                    self.logger.warning(f"No PDF generated for {ticker} {year}")

            except Exception as e:
                self.logger.error(f"Failed to download/convert {ticker} {year}: {e}", exc_info=True)
                # Continue with other years

        return pdf_paths

    def _run_fundamental_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        custom_prompt: Optional[str]
    ) -> Dict[int, Any]:
        """Run fundamental analyzer for each year."""
        analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        for year, pdf_path in pdf_paths.items():
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental)")
            result = analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year,
                custom_prompt=custom_prompt
            )
            if result:
                results[year] = result

        return results

    def _run_excellent_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run excellent company analyzer (multi-year, success-focused)."""
        # For excellent company analysis, we typically analyze all years together
        # But we'll store per-year for consistency
        # This is a placeholder - you may need to implement ExcellentCompanyAnalyzer wrapper

        # Note: Excellent company analysis typically works on aggregated data
        # For now, we'll treat it similarly to fundamental but with a different prompt
        from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer

        analyzer = ExcellentCompanyAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        # This analyzer may work differently - adjust as needed
        results = {}
        # Implementation depends on how ExcellentCompanyAnalyzer works
        # Placeholder for now
        return results

    def _run_objective_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run objective company analyzer (multi-year, unbiased)."""
        # Similar to excellent but with objective prompt
        # Placeholder for now
        results = {}
        return results

    def _run_buffett_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run Buffett perspective analyzer."""
        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        for year, pdf_path in pdf_paths.items():
            self.logger.info(f"Analyzing {ticker} {year} (Buffett Lens)")
            result = analyzer.analyze_buffett(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

        return results

    def _run_taleb_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run Taleb perspective analyzer."""
        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        for year, pdf_path in pdf_paths.items():
            self.logger.info(f"Analyzing {ticker} {year} (Taleb Lens)")
            result = analyzer.analyze_taleb(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

        return results

    def _run_contrarian_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run Contrarian perspective analyzer."""
        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        for year, pdf_path in pdf_paths.items():
            self.logger.info(f"Analyzing {ticker} {year} (Contrarian Lens)")
            result = analyzer.analyze_contrarian(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

        return results

    def _run_multi_perspective(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path]
    ) -> Dict[int, Any]:
        """Run multi-perspective analyzer (Buffett + Taleb + Contrarian)."""
        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        for year, pdf_path in pdf_paths.items():
            self.logger.info(f"Analyzing {ticker} {year} (Multi-Perspective)")
            result = analyzer.analyze_multi_perspective(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

        return results

    def get_analysis_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get status and details of an analysis run.

        Args:
            run_id: Run UUID

        Returns:
            Dictionary with run details and status
        """
        details = self.db.get_run_details(run_id)

        if details:
            # If completed, include results
            if details['status'] == 'completed':
                results = self.db.get_analysis_results(run_id)
                details['results'] = results

            return details

        return {'status': 'not_found'}

    def cancel_analysis(self, run_id: str) -> bool:
        """
        Cancel a running analysis.

        Args:
            run_id: Run UUID

        Returns:
            True if cancelled successfully
        """
        # For now, just mark as failed
        # In a production system, you'd need to actually stop the thread
        status = self.db.get_run_status(run_id)

        if status == 'running':
            self.db.update_run_status(run_id, 'failed', 'Cancelled by user')
            return True

        return False
