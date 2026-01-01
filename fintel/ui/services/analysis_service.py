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

from fintel.core import (
    get_config, get_logger,
    DownloadError, ConversionError, ExtractionError,
    AnalysisError, AIProviderError, RateLimitError, ValidationError
)
from fintel.ai import APIKeyManager, RateLimiter
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
from fintel.analysis.fundamental import FundamentalAnalyzer
from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer, ObjectiveCompanyAnalyzer
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
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
        # APIKeyManager and RateLimiter now use the persistent APIUsageTracker
        # which stores usage data in JSON files for accurate cross-process tracking
        self.api_key_manager = APIKeyManager(self.config.google_api_keys)
        self.rate_limiter = RateLimiter()
        self.downloader = SECDownloader()
        # Note: converter is NOT shared - each thread needs its own browser instance
        # to avoid PDF mixing when running parallel analyses
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
            self.db.update_run_progress(
                run_id,
                progress_message=f"Downloading {filing_type} filings for {ticker}...",
                progress_percent=10
            )
            pdf_paths = self._get_or_download_filings(ticker, filing_type, years, run_id)

            # Check if we have any PDFs
            if not pdf_paths:
                raise ValueError(
                    f"No {filing_type} filings could be downloaded/found for {ticker}. "
                    "Please check the ticker symbol and try again."
                )

            self.logger.info(f"Ready to analyze {len(pdf_paths)} years: {list(pdf_paths.keys())}")

            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} filings...",
                progress_percent=50
            )

            # Run analysis based on type
            if analysis_type == 'fundamental':
                results = self._run_fundamental_analysis(
                    ticker, pdf_paths, custom_prompt, run_id
                )
            elif analysis_type == 'excellent':
                results = self._run_excellent_analysis(ticker, pdf_paths, run_id)
            elif analysis_type == 'objective':
                results = self._run_objective_analysis(ticker, pdf_paths, run_id)
            elif analysis_type == 'buffett':
                results = self._run_buffett_analysis(ticker, pdf_paths, run_id)
            elif analysis_type == 'taleb':
                results = self._run_taleb_analysis(ticker, pdf_paths, run_id)
            elif analysis_type == 'contrarian':
                results = self._run_contrarian_analysis(ticker, pdf_paths, run_id)
            elif analysis_type == 'multi':
                results = self._run_multi_perspective(ticker, pdf_paths, run_id)
            elif analysis_type == 'scanner':
                results = self._run_contrarian_scanner(ticker, pdf_paths, run_id)
            elif analysis_type.startswith('custom:'):
                workflow_id = analysis_type.replace('custom:', '')
                results = self._run_custom_workflow(
                    ticker, pdf_paths, workflow_id, run_id
                )
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

        except DownloadError as e:
            error_msg = f"Download failed: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except ConversionError as e:
            error_msg = f"PDF conversion failed: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except ExtractionError as e:
            error_msg = f"Text extraction failed: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except AIProviderError as e:
            error_msg = f"AI analysis failed: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except ValueError as e:
            error_msg = f"Invalid configuration: {str(e)}"
            self.logger.error(error_msg)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        return run_id

    def _get_or_download_filings(
        self,
        ticker: str,
        filing_type: str,
        years: List[int],
        run_id: str
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
        years_to_download = []

        # First, check cache for all years
        for year in years:
            cached = self.db.get_cached_file(ticker, year, filing_type)
            if cached and Path(cached).exists():
                self.logger.info(f"Using cached file for {ticker} {year}: {cached}")
                pdf_paths[year] = Path(cached)
            else:
                years_to_download.append(year)

        # If all years are cached, we're done
        if not years_to_download:
            return pdf_paths

        # Download and convert once for all uncached years
        try:
            self.logger.info(f"Downloading {ticker} {filing_type} for years: {years_to_download}")

            # Download enough filings to cover all requested years
            # Calculate how many filings we need (add buffer for safety)
            max_year = max(years_to_download)
            min_year = min(years_to_download)
            current_year = datetime.now().year
            years_back = current_year - min_year + 3  # Add 3 year buffer
            num_filings = min(years_back, 20)  # Cap at 20 filings

            self.db.update_run_progress(
                run_id,
                progress_message=f"Downloading {num_filings} {filing_type} filings from SEC...",
                progress_percent=15
            )

            filing_dir = self.downloader.download(
                ticker=ticker,
                num_filings=num_filings,
                filing_type=filing_type
            )

            if not filing_dir:
                self.logger.error(f"Failed to download filings for {ticker}")
                return pdf_paths

            self.db.update_run_progress(
                run_id,
                progress_message=f"Converting HTML filings to PDF...",
                progress_percent=30
            )

            # Convert to PDF - converter extracts year from accession number
            # Organize PDFs by ticker: pdfs/{TICKER}/
            # IMPORTANT: Create a new converter instance for each analysis to avoid
            # browser state mixing when running parallel analyses
            ticker_pdf_path = self.config.get_data_path("pdfs") / ticker.upper()
            with SECConverter() as converter:
                pdf_files = converter.convert(
                    ticker=ticker,
                    input_path=filing_dir,
                    output_path=ticker_pdf_path,
                    filing_type=filing_type
                )

            if not pdf_files:
                self.logger.warning(f"No PDFs generated for {ticker}")
                return pdf_paths

            # Build year->pdf mapping from converted files
            available_pdfs = {pdf_info['year']: pdf_info for pdf_info in pdf_files}
            self.logger.info(f"Converted {len(pdf_files)} filings for {ticker}. Available years: {sorted(available_pdfs.keys())}")

            # Match requested years with available PDFs
            for year in years_to_download:
                if year in available_pdfs:
                    pdf_info = available_pdfs[year]
                    pdf_path = pdf_info['pdf_path']
                    pdf_paths[year] = Path(pdf_path)

                    # Cache it
                    self.db.cache_file(ticker, year, filing_type, str(pdf_path))
                    self.logger.info(f"Matched and cached {ticker} {year}: {pdf_path}")
                else:
                    self.logger.warning(
                        f"No PDF found for {ticker} year {year}. "
                        f"Available years: {sorted(available_pdfs.keys())}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to download/convert {ticker}: {e}", exc_info=True)

        return pdf_paths

    def _run_fundamental_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        custom_prompt: Optional[str],
        run_id: str
    ) -> Dict[int, Any]:
        """Run fundamental analyzer for each year."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for fundamental analysis of {ticker}")
            return {}

        analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental)")

            # Update progress for this specific year
            progress_pct = 50 + int((idx / total_years) * 40)  # 50-90% range
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Fundamental)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

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
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run excellent company analyzer (multi-year, success-focused)."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for excellent analysis of {ticker}")
            return {}

        # First, run fundamental analysis for each year
        fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        fundamental_analyses = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental for Excellent)")

            # Update progress for this specific year
            progress_pct = 50 + int((idx / total_years) * 30)  # 50-80% range
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Fundamental for Excellent)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            result = fundamental_analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                fundamental_analyses[year] = result

        # Now run excellent company analysis on all years together
        if fundamental_analyses:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Synthesizing Excellent Company analysis for {ticker}",
                progress_percent=85
            )

            excellent_analyzer = ExcellentCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter
            )

            self.logger.info(f"Running Excellent Company analysis for {ticker}")
            excellent_result = excellent_analyzer.analyze_success_factors(
                ticker=ticker,
                analyses=fundamental_analyses
            )

            # Return as a special year key (0 means multi-year aggregated)
            return {0: excellent_result} if excellent_result else {}

        return {}

    def _run_objective_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run objective company analyzer (multi-year, unbiased)."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for objective analysis of {ticker}")
            return {}

        # First, run fundamental analysis for each year
        fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        fundamental_analyses = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental for Objective)")

            progress_pct = 50 + int((idx / total_years) * 30)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Fundamental for Objective)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            result = fundamental_analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                fundamental_analyses[year] = result

        # Now run objective company analysis on all years together
        if fundamental_analyses:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Synthesizing Objective Company analysis for {ticker}",
                progress_percent=85
            )

            objective_analyzer = ObjectiveCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter
            )

            self.logger.info(f"Running Objective Company analysis for {ticker}")
            objective_result = objective_analyzer.analyze_success_factors(
                ticker=ticker,
                analyses=fundamental_analyses
            )

            # Return as a special year key (0 means multi-year aggregated)
            return {0: objective_result} if objective_result else {}

        return {}

    def _run_buffett_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run Buffett perspective analyzer."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for Buffett analysis of {ticker}")
            return {}

        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Buffett Lens)")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Buffett Lens)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

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
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run Taleb perspective analyzer."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for Taleb analysis of {ticker}")
            return {}

        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Taleb Lens)")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Taleb Lens)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

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
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run Contrarian perspective analyzer."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for Contrarian analysis of {ticker}")
            return {}

        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Contrarian Lens)")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Contrarian Lens)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

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
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run multi-perspective analyzer (Buffett + Taleb + Contrarian)."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for multi-perspective analysis of {ticker}")
            return {}

        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Multi-Perspective)")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Multi-Perspective)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            result = analyzer.analyze_multi_perspective(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

        return results

    def _run_contrarian_scanner(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str
    ) -> Dict[int, Any]:
        """Run contrarian scanner (multi-year, hidden gems detection)."""
        # First, run fundamental analysis for each year
        fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        fundamental_analyses = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental for Scanner)")

            progress_pct = 50 + int((idx / total_years) * 25)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Fundamental for Scanner)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            result = fundamental_analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                fundamental_analyses[year] = result

        # Now run objective analysis first (scanner needs this)
        if fundamental_analyses:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Running Objective analysis for {ticker}",
                progress_percent=80
            )

            objective_analyzer = ObjectiveCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter
            )

            self.logger.info(f"Running Objective analysis for scanner: {ticker}")
            objective_result = objective_analyzer.analyze_success_factors(
                ticker=ticker,
                analyses=fundamental_analyses
            )

            if objective_result:
                # Save objective result to a temp file for scanner to load
                import tempfile
                import json

                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(objective_result.model_dump(), f, indent=2)
                    temp_path = Path(f.name)

                try:
                    self.db.update_run_progress(
                        run_id,
                        progress_message=f"Running Contrarian Scanner for {ticker}",
                        progress_percent=90
                    )

                    # Now run contrarian scanner
                    scanner = ContrarianScanner(
                        api_key_manager=self.api_key_manager,
                        rate_limiter=self.rate_limiter
                    )

                    self.logger.info(f"Running Contrarian Scanner for {ticker}")
                    scanner_result = scanner.scan_company(
                        ticker=ticker,
                        success_factors_path=temp_path,
                        years=len(fundamental_analyses)
                    )

                    # Return as a special year key (0 means multi-year aggregated)
                    return {0: scanner_result} if scanner_result else {}
                finally:
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()

        return {}

    def _run_custom_workflow(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        workflow_id: str,
        run_id: str
    ) -> Dict[int, Any]:
        """
        Run a custom workflow analysis.

        Args:
            ticker: Company ticker
            pdf_paths: Dictionary mapping year to PDF path
            workflow_id: Custom workflow identifier
            run_id: Analysis run ID

        Returns:
            Dictionary mapping year to analysis result
        """
        # Import custom workflows
        try:
            from custom_workflows import get_workflow
        except ImportError:
            raise ValueError("Custom workflows module not available")

        # Get the workflow class
        workflow_class = get_workflow(workflow_id)
        if not workflow_class:
            raise ValueError(f"Unknown custom workflow: {workflow_id}")

        workflow = workflow_class()

        # Validate years
        workflow.validate_config(len(pdf_paths))

        self.logger.info(f"Running custom workflow '{workflow.name}' for {ticker}")

        # Import AI provider
        from fintel.ai.providers.gemini import GeminiProvider

        results = {}
        total_years = len(pdf_paths)

        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            self.logger.info(f"Analyzing {ticker} {year} ({workflow.name})")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} ({workflow.name})",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            try:
                # Extract text from PDF
                text = self.extractor.extract_text(pdf_path)

                # Format prompt
                prompt = workflow.prompt_template.format(
                    ticker=ticker,
                    year=year
                )
                full_prompt = f"{prompt}\n\nHere's the filing content:\n\n{text}"

                # Reserve API key atomically for parallel safety
                api_key = self.api_key_manager.reserve_key()
                if not api_key:
                    self.logger.error("No API keys available for custom workflow")
                    continue

                try:
                    provider = GeminiProvider(
                        api_key=api_key,
                        model=self.config.default_model,
                        thinking_budget=self.config.thinking_budget,
                        rate_limiter=self.rate_limiter
                    )

                    result = provider.generate_with_retry(
                        prompt=full_prompt,
                        schema=workflow.schema,
                        max_retries=3,
                        retry_delay=10
                    )

                    self.api_key_manager.record_usage(api_key)

                    if result:
                        results[year] = result
                        self.logger.info(f"Completed {workflow.name} analysis for {ticker} {year}")

                finally:
                    # Always release the key
                    self.api_key_manager.release_key(api_key)

            except Exception as e:
                self.logger.error(f"Failed to analyze {ticker} {year} with {workflow.name}: {e}")
                continue

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
