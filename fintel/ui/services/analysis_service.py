#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analysis Service - wraps Fintel analyzers for UI consumption.

This service layer acts as an adapter between the Streamlit UI and
the existing fintel analysis modules, handling database persistence
and progress tracking.
"""

import uuid
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable, TYPE_CHECKING
from datetime import datetime

from fintel.core import (
    get_config, get_logger, FintelConfig,
    DownloadError, ConversionError, ExtractionError,
    AnalysisError, AIProviderError, RateLimitError, ValidationError,
    IKeyManager, IRateLimiter, IDownloader, IExtractor,
    is_annual_filing, is_quarterly_filing,
)
from fintel.ai import APIKeyManager, RateLimiter
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
from fintel.analysis.fundamental import FundamentalAnalyzer
from fintel.analysis.fundamental.success_factors import ExcellentCompanyAnalyzer, ObjectiveCompanyAnalyzer
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.analysis.comparative.contrarian_scanner import ContrarianScanner
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.cancellation import (
    get_cancellation_registry,
    CancellationToken,
    AnalysisCancelledException
)

if TYPE_CHECKING:
    from fintel.core import IConfig


class AnalysisService:
    """
    Service layer that wraps Fintel analyzers for UI consumption.

    Handles:
    - Database persistence of analysis runs and results
    - File caching to avoid re-downloading
    - Integration with existing analyzer classes
    - Progress tracking
    """

    def __init__(
        self,
        db: DatabaseRepository,
        config: Optional[FintelConfig] = None,
        key_manager: Optional[IKeyManager] = None,
        rate_limiter: Optional[IRateLimiter] = None,
        downloader: Optional[IDownloader] = None,
        extractor: Optional[IExtractor] = None,
    ):
        """
        Initialize analysis service with dependency injection support.

        All dependencies are optional for backward compatibility. If not provided,
        they will be created using default implementations.

        Args:
            db: Database repository instance
            config: Configuration object (defaults to get_config())
            key_manager: API key manager (defaults to APIKeyManager)
            rate_limiter: Rate limiter (defaults to RateLimiter)
            downloader: SEC downloader (defaults to SECDownloader)
            extractor: PDF extractor (defaults to PDFExtractor)
        """
        self.db = db
        self.config = config or get_config()
        self.logger = get_logger(__name__)

        # Initialize shared components with dependency injection
        # If not provided, create defaults for backward compatibility
        self.api_key_manager = key_manager or APIKeyManager(self.config.google_api_keys)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.downloader = downloader or SECDownloader()
        # Note: converter is NOT shared - each thread needs its own browser instance
        # to avoid PDF mixing when running parallel analyses
        self.extractor = extractor or PDFExtractor()

        self.logger.info("AnalysisService initialized")

    def run_analysis(
        self,
        ticker: str,
        analysis_type: str,
        filing_type: str = "10-K",
        years: Optional[List[int]] = None,
        num_years: Optional[int] = None,
        custom_prompt: Optional[str] = None,
        company_name: Optional[str] = None,
        api_key: Optional[str] = None,
        input_mode: str = 'ticker',
        cik: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
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
            ticker: Company ticker symbol or CIK (based on input_mode)
            analysis_type: Type of analysis (fundamental, excellent, buffett, etc.)
            filing_type: Filing type (10-K, 10-Q, 8-K)
            years: Specific years to analyze
            num_years: Number of recent years (alternative to years)
            custom_prompt: Optional custom prompt template
            company_name: Optional company name
            api_key: Optional pre-reserved API key (for batch processing Fix #1)
            input_mode: 'ticker' or 'cik' - determines how ticker param is interpreted
            cik: Explicit CIK value (if known from ticker lookup)
            year_progress_callback: Optional callback(current_year, completed_count, total_count)
                                   called after each year is processed

        Returns:
            run_id (UUID string) for tracking progress

        Raises:
            ValueError: If invalid parameters
            Exception: If analysis fails
        """
        run_id = str(uuid.uuid4())

        # Handle CIK mode - resolve company info if needed
        resolved_cik = cik
        resolved_company_name = company_name
        display_identifier = ticker

        if input_mode == 'cik':
            resolved_cik = ticker.zfill(10)
            display_identifier = f"CIK:{resolved_cik}"

            # Get company name from SEC if not provided
            if not resolved_company_name:
                # Check cache first
                cached = self.db.get_cached_cik_company(resolved_cik)
                if cached:
                    resolved_company_name = cached.get('company_name', f'CIK {resolved_cik}')
                else:
                    # Query SEC directly
                    company_info = self.downloader.get_company_info_from_cik(resolved_cik)
                    if company_info:
                        resolved_company_name = company_info.get('company_name', f'CIK {resolved_cik}')
                        # Cache for future use
                        self.db.cache_cik_company(
                            cik=resolved_cik,
                            company_name=resolved_company_name,
                            former_names=company_info.get('former_names'),
                            sic_code=company_info.get('sic_code'),
                            sic_description=company_info.get('sic_description'),
                            state_of_incorporation=company_info.get('state_of_incorporation'),
                            fiscal_year_end=company_info.get('fiscal_year_end')
                        )
                    else:
                        resolved_company_name = f'CIK {resolved_cik}'
        elif cik:
            resolved_cik = cik.zfill(10)

        # Determine years to analyze
        # Note: When num_years is specified, we'll request those years but be flexible
        # about which ones are actually available (handled in _get_or_download_filings)
        if years is None and num_years:
            current_year = datetime.now().year
            # Request from current year, but actual available years may differ
            # (e.g., in early January, current year filings may not exist yet)
            years = list(range(current_year, current_year - num_years, -1))
        elif years is None:
            # Default to previous year since current year often not available
            current_year = datetime.now().year
            years = [current_year - 1]

        # Store original requested count for flexible matching
        requested_num_years = num_years

        self.logger.info(
            f"Starting {analysis_type} analysis for {display_identifier} "
            f"({filing_type}, years: {years}, mode: {input_mode})"
        )

        # Create run record with CIK support
        self.db.create_analysis_run_with_cik(
            run_id=run_id,
            ticker=ticker if input_mode == 'ticker' else resolved_cik,
            analysis_type=analysis_type,
            filing_type=filing_type,
            years=years,
            config={
                'custom_prompt': custom_prompt,
                'model': self.config.default_model,
                'thinking_budget': self.config.thinking_budget,
                'filing_type': filing_type,
                'input_mode': input_mode
            },
            company_name=resolved_company_name,
            cik=resolved_cik,
            input_mode=input_mode
        )

        # Create cancellation token for this run
        registry = get_cancellation_registry()
        token = registry.create_token(run_id)
        token.set_thread(threading.current_thread())

        try:
            self.db.update_run_status(run_id, 'running')

            # Check for cancellation before starting
            token.raise_if_cancelled()

            # Download/retrieve filings
            self.db.update_run_progress(
                run_id,
                progress_message=f"Downloading {filing_type} filings for {display_identifier}...",
                progress_percent=10
            )
            # Pass the appropriate identifier based on mode
            identifier_for_download = resolved_cik if input_mode == 'cik' else ticker
            pdf_paths = self._get_or_download_filings(
                identifier_for_download, filing_type, years, run_id,
                input_mode=input_mode
            )

            # Check for cancellation after download
            token.raise_if_cancelled()

            # Check if we have any PDFs
            if not pdf_paths:
                raise ValueError(
                    f"No {filing_type} filings could be downloaded/found for {display_identifier}. "
                    "Please check the identifier and try again."
                )

            self.logger.info(f"Ready to analyze {len(pdf_paths)} years: {list(pdf_paths.keys())}")

            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} filings...",
                progress_percent=50
            )

            # Run analysis based on type
            # api_key is passed to support pre-reserved keys from batch processing (Fix #1)
            # year_progress_callback is passed for batch queue progress tracking
            if analysis_type == 'fundamental':
                results = self._run_fundamental_analysis(
                    ticker, pdf_paths, custom_prompt, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback
                )
            elif analysis_type == 'excellent':
                results = self._run_excellent_analysis(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'objective':
                results = self._run_objective_analysis(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'buffett':
                results = self._run_buffett_analysis(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'taleb':
                results = self._run_taleb_analysis(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'contrarian':
                results = self._run_contrarian_analysis(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'multi':
                results = self._run_multi_perspective(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type == 'scanner':
                results = self._run_contrarian_scanner(ticker, pdf_paths, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback)
            elif analysis_type.startswith('custom:'):
                workflow_id = analysis_type.replace('custom:', '')
                results = self._run_custom_workflow(
                    ticker, pdf_paths, workflow_id, run_id, api_key=api_key,
                    year_progress_callback=year_progress_callback
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
            error_msg = str(e)
            self.logger.error("AI analysis failed", exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        except AnalysisError as e:
            error_msg = str(e)
            self.logger.error("Analysis failed", exc_info=True)
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

        except AnalysisCancelledException:
            self.logger.info(f"Analysis {run_id} cancelled by user")
            self.db.update_run_status(run_id, 'cancelled', 'Cancelled by user')
            raise

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            raise

        finally:
            # Always cleanup cancellation token
            registry.cleanup_token(run_id)

        return run_id

    def _get_or_download_filings(
        self,
        ticker: str,
        filing_type: str,
        years: List[int],
        run_id: str,
        flexible_years: bool = True,
        input_mode: str = 'ticker'
    ) -> Dict[int, Path]:
        """
        Download filings or retrieve from cache.

        This method is flexible about year matching:
        - For annual filings (10-K, 20-F): Tries to match requested years, falls back to most recent
        - For event-based filings (8-K, 4, DEF 14A): Uses most recent N filings regardless of year

        Args:
            ticker: Company ticker or CIK (based on input_mode)
            filing_type: Filing type (10-K, 10-Q, 8-K, etc.)
            years: List of years to try (for annual filings) or implicit count (for event filings)
            run_id: Analysis run ID for progress updates
            flexible_years: If True, use available filings when requested years aren't found
            input_mode: 'ticker' or 'cik' - determines download method

        Returns:
            Dictionary mapping year to PDF path (year may be inferred from filing date)
        """
        pdf_paths = {}

        # For CIK mode, use CIK as identifier
        identifier = ticker.zfill(10) if input_mode == 'cik' else ticker

        # Determine if this is an annual filing or event-based
        # Annual filings have one per year; event filings can have multiple per year
        annual = is_annual_filing(filing_type)
        quarterly = is_quarterly_filing(filing_type)

        self.logger.info(f"Filing type {filing_type} - Annual: {annual}, Quarterly: {quarterly}, Mode: {input_mode}")

        # For event-based filings, use count-based logic
        if not annual and not quarterly:
            return self._get_event_filings(identifier, filing_type, len(years), run_id, input_mode=input_mode)

        # For annual/quarterly filings, try year-based matching
        years_to_download = []

        # First, check cache for all years
        for year in years:
            cached = self.db.get_cached_file(identifier, year, filing_type)
            if cached:
                cached_path = Path(cached)
                if cached_path.exists():
                    self.logger.info(f"[CACHE HIT] Using cached PDF for {identifier} {year}: {cached}")
                    pdf_paths[year] = cached_path
                else:
                    # File was deleted from disk, remove stale cache entry
                    self.logger.warning(
                        f"[CACHE STALE] Cached file missing for {identifier} {year}, "
                        f"clearing cache entry and re-downloading: {cached}"
                    )
                    self.db.clear_file_cache_entry(identifier, year, filing_type)
                    years_to_download.append(year)
            else:
                self.logger.debug(f"[CACHE MISS] No cache entry for {identifier} {year}")
                years_to_download.append(year)

        # If all years are cached, we're done
        if not years_to_download:
            self.logger.info(f"All {len(years)} requested filings found in cache for {identifier}")
            return pdf_paths

        self.logger.info(
            f"Cache status for {identifier}: {len(pdf_paths)} cached, "
            f"{len(years_to_download)} need download: {years_to_download}"
        )

        # Download and convert once for all uncached years
        try:
            self.logger.info(f"Downloading {identifier} {filing_type} for years: {years_to_download} (mode: {input_mode})")

            # Download enough filings to cover all requested years
            # For annual filings: one per year, so download len(years) + buffer
            # For quarterly: 4 per year, so download len(years) * 4 + buffer
            num_to_request = len(years_to_download)
            if quarterly:
                num_to_request = num_to_request * 4  # 4 quarters per year
            num_to_request = min(num_to_request + 5, 20)  # Add buffer, cap at 20

            self.db.update_run_progress(
                run_id,
                progress_message=f"Downloading {num_to_request} {filing_type} filings from SEC...",
                progress_percent=15
            )

            # Use CIK-direct download method if in CIK mode
            if input_mode == 'cik':
                filing_dir, filing_metadata = self.downloader.download_with_metadata_by_cik(
                    cik=identifier,
                    num_filings=num_to_request,
                    filing_type=filing_type
                )
            else:
                # Use standard ticker-based download
                filing_dir, filing_metadata = self.downloader.download_with_metadata(
                    ticker=identifier,
                    num_filings=num_to_request,
                    filing_type=filing_type
                )

            if not filing_dir:
                self.logger.error(f"Failed to download filings for {identifier}")
                return pdf_paths

            self.db.update_run_progress(
                run_id,
                progress_message=f"Converting HTML filings to PDF...",
                progress_percent=30
            )

            # Convert to PDF - pass filing_metadata for unique filename generation
            # Use identifier (CIK or ticker) for the PDF directory
            pdf_dir_name = identifier.upper() if input_mode == 'ticker' else f"CIK_{identifier}"
            ticker_pdf_path = self.config.get_data_path("pdfs") / pdf_dir_name
            with SECConverter() as converter:
                pdf_files = converter.convert(
                    ticker=identifier,
                    input_path=filing_dir,
                    output_path=ticker_pdf_path,
                    filing_type=filing_type,
                    filing_metadata=filing_metadata
                )

            if not pdf_files:
                self.logger.warning(f"No PDFs generated for {identifier}")
                return pdf_paths

            # Build mapping from filing_date -> fiscal_year using SEC metadata
            # This is crucial because:
            # - converter.year = filing year (from accession number, e.g., 2024)
            # - metadata.fiscal_year = actual fiscal year (e.g., 2023 for FY2023 filed in 2024)
            # We need to use fiscal_year for caching and lookup, not filing year
            filing_date_to_fiscal_year = {}
            if filing_metadata:
                for meta in filing_metadata:
                    fd = meta.get('filing_date')
                    fy = meta.get('fiscal_year')
                    if fd and fy:
                        filing_date_to_fiscal_year[fd] = fy
                self.logger.debug(f"Built filing_date->fiscal_year mapping: {filing_date_to_fiscal_year}")

            # Build fiscal_year->pdf mapping from converted files
            # Use fiscal_year from metadata (not converter's year from accession)
            available_pdfs = {}
            for pdf_info in pdf_files:
                filing_date = pdf_info.get('filing_date')
                accession_year = pdf_info['year']  # Filing year from accession (e.g., 2024)

                # Look up correct fiscal_year from metadata
                fiscal_year = filing_date_to_fiscal_year.get(filing_date, accession_year)

                # If no metadata match, derive fiscal year:
                # For annual filings (10-K), fiscal year is typically the year before filing
                if fiscal_year == accession_year and filing_metadata and annual:
                    # Fallback: for 10-K filed in early part of year, fiscal year is previous year
                    if filing_date and filing_date[5:7] in ('01', '02', '03', '04'):
                        fiscal_year = accession_year - 1
                        self.logger.debug(f"Derived fiscal_year={fiscal_year} for {filing_date} (filed early in year)")

                pdf_info['fiscal_year'] = fiscal_year
                available_pdfs[fiscal_year] = pdf_info

            available_years_sorted = sorted(available_pdfs.keys(), reverse=True)
            self.logger.info(f"Converted {len(pdf_files)} {filing_type} filings for {identifier}. Available fiscal years: {available_years_sorted}")

            # Match requested years with available PDFs
            for year in years_to_download:
                if year in available_pdfs:
                    pdf_info = available_pdfs[year]
                    pdf_path = pdf_info['pdf_path']
                    filing_date = pdf_info.get('filing_date')
                    fiscal_year = pdf_info.get('fiscal_year', year)
                    pdf_paths[year] = Path(pdf_path)

                    # Cache using fiscal_year (not filing year from accession)
                    self.db.cache_file(
                        identifier, fiscal_year, filing_type, str(pdf_path),
                        filing_date=filing_date
                    )
                    self.logger.info(f"Matched and cached {identifier} FY{fiscal_year} (filed {filing_date}): {pdf_path}")
                else:
                    self.logger.info(
                        f"Fiscal year {year} not available for {identifier}. "
                        f"Available fiscal years: {available_years_sorted}"
                    )

            # Flexible matching: if we didn't find all requested years,
            # fill in with the most recent available years we haven't used yet
            if flexible_years and len(pdf_paths) < len(years):
                needed_count = len(years) - len(pdf_paths)
                already_used = set(pdf_paths.keys())

                for avail_year in available_years_sorted:
                    if needed_count <= 0:
                        break
                    if avail_year not in already_used:
                        pdf_info = available_pdfs[avail_year]
                        pdf_path = pdf_info['pdf_path']
                        filing_date = pdf_info.get('filing_date')
                        fiscal_year = pdf_info.get('fiscal_year', avail_year)
                        pdf_paths[avail_year] = Path(pdf_path)

                        # Cache using fiscal_year
                        self.db.cache_file(
                            identifier, fiscal_year, filing_type, str(pdf_path),
                            filing_date=filing_date
                        )
                        self.logger.info(
                            f"Flexible match: using {identifier} FY{fiscal_year} "
                            f"(requested year not available): {pdf_path}"
                        )
                        needed_count -= 1

        except Exception as e:
            self.logger.error(f"Failed to download/convert {ticker}: {e}", exc_info=True)

        return pdf_paths

    def _get_event_filings(
        self,
        ticker: str,
        filing_type: str,
        count: int,
        run_id: str,
        input_mode: str = 'ticker'
    ) -> Dict[str, Path]:
        """
        Get N most recent event-based filings (8-K, 4, DEF 14A, etc.).

        For event filings, we use filing_date as the key since there can be
        multiple filings per year. This ensures unique identification.

        Args:
            ticker: Company ticker or CIK (based on input_mode)
            filing_type: Filing type (8-K, 4, DEF 14A, etc.)
            count: Number of filings to fetch
            run_id: Analysis run ID for progress updates
            input_mode: 'ticker' or 'cik' - determines download method

        Returns:
            Dictionary mapping filing_date (or index) to PDF path
        """
        identifier = ticker.zfill(10) if input_mode == 'cik' else ticker
        self.logger.info(f"Getting {count} most recent {filing_type} filings for {identifier} (mode: {input_mode})")

        pdf_paths = {}

        # First, check cache for existing event filings
        cached_filings = self.db.get_all_cached_filings(identifier, filing_type)
        cached_count = 0

        for cached in cached_filings:
            if cached_count >= count:
                break

            cached_path = Path(cached['file_path']) if cached.get('file_path') else None
            filing_date = cached.get('filing_date')

            if cached_path and cached_path.exists() and filing_date:
                self.logger.info(f"[CACHE HIT] Using cached {filing_type} for {identifier} filed {filing_date}")
                pdf_paths[filing_date] = cached_path
                cached_count += 1
            elif cached_path and not cached_path.exists():
                # Stale cache entry - file missing
                self.logger.warning(
                    f"[CACHE STALE] Cached file missing for {identifier} {filing_type} "
                    f"filed {filing_date}, will re-download"
                )

        # If we have enough cached filings, return early
        if cached_count >= count:
            self.logger.info(f"All {count} requested {filing_type} filings found in cache for {identifier}")
            return pdf_paths

        # Need to download more filings
        needed_count = count - cached_count
        self.logger.info(
            f"Cache status for {identifier} {filing_type}: {cached_count} cached, "
            f"{needed_count} need download"
        )

        try:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Downloading {needed_count} {filing_type} filings from SEC...",
                progress_percent=15
            )

            # Download more than needed to account for already-cached ones
            download_count = needed_count + 5  # Buffer for overlap

            # Use CIK-direct download method if in CIK mode
            if input_mode == 'cik':
                filing_dir, filing_metadata = self.downloader.download_with_metadata_by_cik(
                    cik=identifier,
                    num_filings=download_count,
                    filing_type=filing_type
                )
            else:
                filing_dir, filing_metadata = self.downloader.download_with_metadata(
                    ticker=identifier,
                    num_filings=download_count,
                    filing_type=filing_type
                )

            if not filing_dir:
                self.logger.error(f"Failed to download filings for {identifier}")
                return pdf_paths

            self.db.update_run_progress(
                run_id,
                progress_message=f"Converting {filing_type} filings to PDF...",
                progress_percent=30
            )

            pdf_dir_name = identifier.upper() if input_mode == 'ticker' else f"CIK_{identifier}"
            ticker_pdf_path = self.config.get_data_path("pdfs") / pdf_dir_name
            with SECConverter() as converter:
                pdf_files = converter.convert(
                    ticker=identifier,
                    input_path=filing_dir,
                    output_path=ticker_pdf_path,
                    filing_type=filing_type,
                    filing_metadata=filing_metadata
                )

            if not pdf_files:
                self.logger.warning(f"No PDFs generated for {identifier}")
                return pdf_paths

            # For event filings, use filing_date as key (or index if no date)
            # Sort by filing_date (most recent first)
            sorted_pdfs = sorted(
                pdf_files,
                key=lambda x: x.get('filing_date') or str(x.get('year', '')),
                reverse=True
            )

            for idx, pdf_info in enumerate(sorted_pdfs):
                # Stop if we have enough filings
                if len(pdf_paths) >= count:
                    break

                pdf_path = pdf_info['pdf_path']
                filing_date = pdf_info.get('filing_date')
                actual_year = pdf_info.get('year')

                # Skip if already in our results (from cache)
                if filing_date and filing_date in pdf_paths:
                    self.logger.debug(f"Skipping {filing_date} - already cached")
                    continue

                # Use filing_date as key, fallback to index for compatibility
                if filing_date:
                    pdf_paths[filing_date] = Path(pdf_path)
                    # Cache with filing_date
                    self.db.cache_file(
                        identifier, actual_year or 0, filing_type, str(pdf_path),
                        filing_date=filing_date
                    )
                    self.logger.info(f"[CACHE STORED] {filing_type} filed {filing_date} for {identifier}")
                else:
                    # Fallback: use sequence index
                    pdf_paths[idx + 1] = Path(pdf_path)

                self.logger.info(
                    f"Event filing: {filing_type} filed {filing_date or f'(seq {idx+1})'} "
                    f"from {actual_year} -> {pdf_path}"
                )

            self.logger.info(f"Retrieved {len(pdf_paths)} {filing_type} filings for {ticker}")
            return pdf_paths

        except Exception as e:
            self.logger.error(f"Failed to get event filings for {ticker}: {e}", exc_info=True)
            return pdf_paths

    def _run_fundamental_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[Union[int, str], Path],
        custom_prompt: Optional[str],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[Union[int, str], Any]:
        """
        Run fundamental analyzer for each year.

        Args:
            api_key: Optional pre-reserved API key from batch processing (Fix #1).
                     When provided, this key should be used instead of reserving a new one.
            year_progress_callback: Optional callback(current_year, completed_count, total_count)
        """
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for fundamental analysis of {ticker}")
            return {}

        # Get cancellation token for this run
        token = get_cancellation_registry().get_token(run_id)

        # Create analyzer - if api_key is provided, it's from batch queue Fix #1
        # The analyzer will use the api_key_manager internally
        analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            api_key=api_key  # Pass pre-reserved key if available
        )

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            # Check for cancellation before processing each year
            if token:
                token.raise_if_cancelled()

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

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

        return results

    def _run_excellent_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run excellent company analyzer (multi-year, success-focused)."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for excellent analysis of {ticker}")
            return {}

        # First, run fundamental analysis for each year
        fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            api_key=api_key
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

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

        # Now run excellent company analysis on all years together
        if fundamental_analyses:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Synthesizing Excellent Company analysis for {ticker}",
                progress_percent=85
            )

            excellent_analyzer = ExcellentCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter,
                api_key=api_key
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
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run objective company analyzer (multi-year, unbiased)."""
        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for objective analysis of {ticker}")
            return {}

        # First, run fundamental analysis for each year
        fundamental_analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            api_key=api_key
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

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

        # Now run objective company analysis on all years together
        if fundamental_analyses:
            self.db.update_run_progress(
                run_id,
                progress_message=f"Synthesizing Objective Company analysis for {ticker}",
                progress_percent=85
            )

            objective_analyzer = ObjectiveCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter,
                api_key=api_key
            )

            self.logger.info(f"Running Objective Company analysis for {ticker}")
            objective_result = objective_analyzer.analyze_success_factors(
                ticker=ticker,
                analyses=fundamental_analyses
            )

            # Return as a special year key (0 means multi-year aggregated)
            return {0: objective_result} if objective_result else {}

        return {}

    def _run_perspective_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        perspective: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """
        Run perspective analysis for a given perspective type.

        This unified method handles all perspective-based analyses (Buffett, Taleb,
        Contrarian, Multi-Perspective) with a single implementation.

        Args:
            ticker: Company ticker symbol
            pdf_paths: Dictionary mapping year to PDF path
            run_id: Analysis run ID for progress updates
            perspective: Perspective type ('buffett', 'taleb', 'contrarian', 'multi')
            api_key: Optional pre-reserved API key
            year_progress_callback: Optional callback(current_year, completed_count, total_count)

        Returns:
            Dictionary mapping year to analysis result
        """
        perspective_names = {
            'buffett': 'Buffett Lens',
            'taleb': 'Taleb Lens',
            'contrarian': 'Contrarian Lens',
            'multi': 'Multi-Perspective',
        }
        display_name = perspective_names.get(perspective, perspective.title())

        # Validate PDF paths
        if not pdf_paths or len(pdf_paths) == 0:
            self.logger.warning(f"No PDF files provided for {display_name} analysis of {ticker}")
            return {}

        # Get cancellation token
        token = get_cancellation_registry().get_token(run_id)

        analyzer = PerspectiveAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter,
            api_key=api_key
        )

        # Map perspective to analyzer method
        analyze_methods = {
            'buffett': analyzer.analyze_buffett,
            'taleb': analyzer.analyze_taleb,
            'contrarian': analyzer.analyze_contrarian,
            'multi': analyzer.analyze_multi_perspective,
        }
        analyze_method = analyze_methods.get(perspective)
        if not analyze_method:
            raise ValueError(f"Unknown perspective: {perspective}")

        results = {}
        total_years = len(pdf_paths)
        for idx, (year, pdf_path) in enumerate(pdf_paths.items(), 1):
            # Check for cancellation
            if token:
                token.raise_if_cancelled()

            self.logger.info(f"Analyzing {ticker} {year} ({display_name})")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} ({display_name})",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )

            result = analyze_method(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year
            )
            if result:
                results[year] = result

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

        return results

    def _run_buffett_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run Buffett perspective analyzer."""
        return self._run_perspective_analysis(ticker, pdf_paths, run_id, 'buffett', api_key, year_progress_callback)

    def _run_taleb_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run Taleb perspective analyzer."""
        return self._run_perspective_analysis(ticker, pdf_paths, run_id, 'taleb', api_key, year_progress_callback)

    def _run_contrarian_analysis(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run Contrarian perspective analyzer."""
        return self._run_perspective_analysis(ticker, pdf_paths, run_id, 'contrarian', api_key, year_progress_callback)

    def _run_multi_perspective(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """Run multi-perspective analyzer (Buffett + Taleb + Contrarian)."""
        return self._run_perspective_analysis(ticker, pdf_paths, run_id, 'multi', api_key, year_progress_callback)

    def _run_contrarian_scanner(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
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

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

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
        run_id: str,
        api_key: Optional[str] = None,
        year_progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> Dict[int, Any]:
        """
        Run a custom workflow analysis.

        Args:
            ticker: Company ticker
            pdf_paths: Dictionary mapping year to PDF path
            api_key: Optional pre-reserved API key from batch processing
            workflow_id: Custom workflow identifier
            run_id: Analysis run ID
            year_progress_callback: Optional callback(current_year, completed_count, total_count)

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

            # Call progress callback after each year
            if year_progress_callback:
                try:
                    year_progress_callback(year, idx, total_years)
                except Exception as e:
                    self.logger.warning(f"Year progress callback error: {e}")

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

    def cancel_analysis(self, run_id: str, timeout: float = 30.0) -> bool:
        """
        Cancel a running analysis with actual thread termination.

        This method signals the cancellation token and waits for the
        analysis thread to stop gracefully.

        Args:
            run_id: Run UUID
            timeout: Seconds to wait for graceful termination

        Returns:
            True if cancelled successfully, False otherwise
        """
        status = self.db.get_run_status(run_id)

        if status != 'running':
            self.logger.warning(f"Run {run_id} is not running (status: {status})")
            return False

        registry = get_cancellation_registry()
        success = registry.cancel_run(run_id, timeout=timeout)

        if success:
            # Token cleanup and status update happen in the analysis thread
            # via the exception handler, but we ensure status is updated
            current_status = self.db.get_run_status(run_id)
            if current_status == 'running':
                self.db.update_run_status(run_id, 'cancelled', 'Cancelled by user')
            self.logger.info(f"Successfully cancelled analysis {run_id}")
        else:
            # Thread didn't terminate in time, but we've signaled cancellation
            # It will stop at the next cancellation check point
            self.logger.warning(
                f"Cancellation signaled for {run_id} but thread didn't terminate "
                f"within {timeout}s. It will stop at the next check point."
            )
            self.db.update_run_status(
                run_id, 'cancelled',
                'Cancellation requested (may take a moment to stop)'
            )

        return True

    def get_interrupted_runs(self, stale_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Get runs that appear to be interrupted.

        Args:
            stale_minutes: Consider run stale if no activity for this many minutes

        Returns:
            List of interrupted run details
        """
        return self.db.get_interrupted_runs(stale_minutes)

    def resume_analysis(self, run_id: str) -> bool:
        """
        Resume an interrupted analysis from where it left off.

        Args:
            run_id: Run UUID to resume

        Returns:
            True if resumed successfully
        """
        # Get run details
        details = self.db.get_run_details(run_id)
        if not details:
            self.logger.error(f"Run {run_id} not found")
            return False

        # Check if can be resumed
        if not self.db.prepare_for_resume(run_id):
            self.logger.error(f"Run {run_id} cannot be resumed")
            return False

        try:
            import json as json_module

            ticker = details['ticker']
            analysis_type = details['analysis_type']
            filing_type = details['filing_type']
            years = json_module.loads(details['years_analyzed']) if details['years_analyzed'] else []
            completed_years = self.db.get_completed_years(run_id)
            custom_prompt = None

            # Get custom prompt from config if it exists
            if details.get('config_json'):
                config = json_module.loads(details['config_json'])
                custom_prompt = config.get('custom_prompt')

            # Calculate remaining years
            remaining_years = [y for y in years if y not in completed_years]

            if not remaining_years:
                self.logger.info(f"Run {run_id} has no remaining years to analyze")
                self.db.update_run_status(run_id, 'completed')
                return True

            self.logger.info(
                f"Resuming {analysis_type} analysis for {ticker}: "
                f"completed={completed_years}, remaining={remaining_years}"
            )

            # Download/retrieve filings for remaining years
            self.db.update_run_progress(
                run_id,
                progress_message=f"Resuming: downloading {filing_type} filings...",
                progress_percent=10
            )
            pdf_paths = self._get_or_download_filings(ticker, filing_type, remaining_years, run_id)

            if not pdf_paths:
                raise ValueError(f"No filings found for remaining years: {remaining_years}")

            # Run analysis for remaining years
            if analysis_type == 'fundamental':
                results = self._run_fundamental_analysis_with_tracking(
                    ticker, pdf_paths, custom_prompt, run_id
                )
            elif analysis_type.startswith('custom:'):
                workflow_id = analysis_type.replace('custom:', '')
                results = self._run_custom_workflow_with_tracking(
                    ticker, pdf_paths, workflow_id, run_id
                )
            else:
                # For other analysis types, use original methods
                # These don't support per-year resumption as well
                results = self._run_analysis_by_type(
                    analysis_type, ticker, pdf_paths, custom_prompt, run_id
                )

            # Store results
            for year, result in results.items():
                if result:
                    self.db.store_result(
                        run_id=run_id,
                        ticker=ticker,
                        fiscal_year=year,
                        filing_type=filing_type,
                        result_type=type(result).__name__,
                        result_data=result.model_dump()
                    )

            self.db.update_run_status(run_id, 'completed')
            self.logger.info(f"Resumed analysis completed: {run_id}")
            return True

        except Exception as e:
            error_msg = f"Resume failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(run_id, 'failed', error_msg)
            return False

    def _run_analysis_by_type(
        self,
        analysis_type: str,
        ticker: str,
        pdf_paths: Dict[int, Path],
        custom_prompt: Optional[str],
        run_id: str
    ) -> Dict[int, Any]:
        """Run analysis based on type (helper for resume)."""
        if analysis_type == 'fundamental':
            return self._run_fundamental_analysis(ticker, pdf_paths, custom_prompt, run_id)
        elif analysis_type == 'excellent':
            return self._run_excellent_analysis(ticker, pdf_paths, run_id)
        elif analysis_type == 'objective':
            return self._run_objective_analysis(ticker, pdf_paths, run_id)
        elif analysis_type == 'buffett':
            return self._run_buffett_analysis(ticker, pdf_paths, run_id)
        elif analysis_type == 'taleb':
            return self._run_taleb_analysis(ticker, pdf_paths, run_id)
        elif analysis_type == 'contrarian':
            return self._run_contrarian_analysis(ticker, pdf_paths, run_id)
        elif analysis_type == 'multi':
            return self._run_multi_perspective(ticker, pdf_paths, run_id)
        elif analysis_type == 'scanner':
            return self._run_contrarian_scanner(ticker, pdf_paths, run_id)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

    def _run_fundamental_analysis_with_tracking(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        custom_prompt: Optional[str],
        run_id: str
    ) -> Dict[int, Any]:
        """Run fundamental analyzer with per-year completion tracking."""
        if not pdf_paths:
            return {}

        analyzer = FundamentalAnalyzer(
            api_key_manager=self.api_key_manager,
            rate_limiter=self.rate_limiter
        )

        results = {}
        total_years = len(pdf_paths)

        for idx, (year, pdf_path) in enumerate(sorted(pdf_paths.items(), reverse=True), 1):
            self.logger.info(f"Analyzing {ticker} {year} (Fundamental)")

            # Update progress and activity
            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} (Fundamental)",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )
            self.db.update_last_activity(run_id)

            try:
                result = analyzer.analyze_filing(
                    pdf_path=pdf_path,
                    ticker=ticker,
                    year=year,
                    custom_prompt=custom_prompt
                )
                if result:
                    results[year] = result
                    # Mark year as completed for resume tracking
                    self.db.mark_year_completed(run_id, year)
                    self.logger.info(f"Completed and tracked {ticker} {year}")

            except Exception as e:
                self.logger.error(f"Failed to analyze {ticker} {year}: {e}")
                # Continue with other years

        return results

    def _run_custom_workflow_with_tracking(
        self,
        ticker: str,
        pdf_paths: Dict[int, Path],
        workflow_id: str,
        run_id: str
    ) -> Dict[int, Any]:
        """Run custom workflow with per-year completion tracking."""
        try:
            from custom_workflows import get_workflow
        except ImportError:
            raise ValueError("Custom workflows module not available")

        workflow_class = get_workflow(workflow_id)
        if not workflow_class:
            raise ValueError(f"Unknown custom workflow: {workflow_id}")

        workflow = workflow_class()
        workflow.validate_config(len(pdf_paths))

        self.logger.info(f"Running custom workflow '{workflow.name}' for {ticker}")

        from fintel.ai.providers.gemini import GeminiProvider

        results = {}
        total_years = len(pdf_paths)

        for idx, (year, pdf_path) in enumerate(sorted(pdf_paths.items(), reverse=True), 1):
            self.logger.info(f"Analyzing {ticker} {year} ({workflow.name})")

            progress_pct = 50 + int((idx / total_years) * 40)
            self.db.update_run_progress(
                run_id,
                progress_message=f"Analyzing {ticker} {year} ({workflow.name})",
                progress_percent=progress_pct,
                current_step=f"Year {year}",
                total_steps=total_years
            )
            self.db.update_last_activity(run_id)

            try:
                text = self.extractor.extract_text(pdf_path)
                prompt = workflow.prompt_template.format(ticker=ticker, year=year)
                full_prompt = f"{prompt}\n\nHere's the filing content:\n\n{text}"

                api_key = self.api_key_manager.reserve_key()
                if not api_key:
                    self.logger.error("No API keys available")
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
                        self.db.mark_year_completed(run_id, year)
                        self.logger.info(f"Completed {workflow.name} for {ticker} {year}")

                finally:
                    self.api_key_manager.release_key(api_key)

            except Exception as e:
                self.logger.error(f"Failed {ticker} {year}: {e}")
                continue

        return results

    def create_multi_year_synthesis(
        self,
        run_id: str,
        synthesis_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a synthesis analysis that combines all years from a single analysis run.

        This takes a multi-year analysis (e.g., 10 years of Amazon 10-Ks) and creates
        an additional synthesis that combines insights from all years into a comprehensive
        longitudinal analysis.

        Args:
            run_id: The original multi-year analysis run ID
            synthesis_prompt: Optional custom prompt for synthesis

        Returns:
            New run_id of the synthesis analysis, or None if failed
        """
        from fintel.ai.providers.gemini import GeminiProvider
        import json as json_module

        # Get original run details
        run_details = self.db.get_run_details(run_id)
        if not run_details:
            self.logger.error(f"Run {run_id} not found")
            return None

        ticker = run_details['ticker']
        analysis_type = run_details['analysis_type']
        filing_type = run_details.get('filing_type', '10-K')

        # Get all year results
        results = self.db.get_analysis_results(run_id)
        if not results or len(results) < 2:
            self.logger.error(f"Run {run_id} has less than 2 year results")
            return None

        self.logger.info(f"Creating multi-year synthesis for {ticker} with {len(results)} years")

        # Create synthesis run record
        synthesis_run_id = str(uuid.uuid4())
        years = [r.get('year') for r in results if r.get('year')]

        self.db.create_analysis_run(
            run_id=synthesis_run_id,
            ticker=ticker,
            analysis_type='multi_year_synthesis',
            filing_type=filing_type,
            years=years,
            config={
                'source_run_id': run_id,
                'source_analysis_type': analysis_type,
                'num_years': len(results)
            },
            company_name=run_details.get('company_name', ticker)
        )

        try:
            self.db.update_run_status(synthesis_run_id, 'running')
            self.db.update_run_progress(
                synthesis_run_id,
                progress_message=f"Synthesizing {len(results)} years of analysis...",
                progress_percent=10
            )

            # Build synthesis prompt
            default_prompt = f"""
You are analyzing {len(results)} years of {analysis_type} analysis for {ticker}.

Your task is to synthesize all the individual year analyses into a comprehensive longitudinal assessment:

1. **Executive Summary**: High-level synthesis of the company's trajectory over all years
2. **Key Trends**: Major trends observed across the years (improving, declining, stable)
3. **Turning Points**: Significant changes or pivotal moments in the company's evolution
4. **Consistency Analysis**: What has remained consistent vs. what has changed
5. **Trajectory Assessment**: Where the company appears to be heading
6. **Risk Evolution**: How risks have evolved over time
7. **Investment Timeline**: Key periods that would have been good/bad for investment
8. **Forward Outlook**: Projections based on historical patterns
9. **Key Metrics Over Time**: Summarize important metrics across years if available

Be comprehensive but focus on actionable insights from the longitudinal perspective.
"""
            prompt = synthesis_prompt or default_prompt

            # Build context with all year analyses
            context_parts = [prompt, f"\n\n=== {ticker} ANALYSIS BY YEAR ===\n"]

            # Sort by year
            sorted_results = sorted(results, key=lambda r: r.get('year', 0))

            for result in sorted_results:
                year = result.get('year', 'N/A')
                data = result.get('data', {})

                context_parts.append(f"\n--- YEAR {year} ---\n")

                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (list, dict)):
                            context_parts.append(f"  {key}: {json_module.dumps(value, indent=2)}\n")
                        else:
                            context_parts.append(f"  {key}: {value}\n")
                else:
                    context_parts.append(f"  {data}\n")

            full_prompt = "".join(context_parts)

            self.db.update_run_progress(
                synthesis_run_id,
                progress_message="Running AI synthesis...",
                progress_percent=50
            )

            # Reserve API key
            api_key = self.api_key_manager.reserve_key()
            if not api_key:
                raise Exception("No API keys available for synthesis")

            try:
                provider = GeminiProvider(
                    api_key=api_key,
                    model=self.config.default_model,
                    thinking_budget=self.config.thinking_budget,
                    rate_limiter=self.rate_limiter
                )

                # Schema for multi-year synthesis
                from pydantic import BaseModel, Field
                from typing import List as TypeList

                class TrendItem(BaseModel):
                    area: str = Field(description="Area of analysis")
                    trend: str = Field(description="Trend direction: improving, declining, stable, mixed")
                    details: str = Field(description="Explanation of the trend")

                class TurningPoint(BaseModel):
                    year: int
                    event: str
                    impact: str

                class MultiYearSynthesis(BaseModel):
                    executive_summary: str = Field(description="High-level synthesis")
                    key_trends: TypeList[TrendItem] = Field(description="Major trends across years")
                    turning_points: TypeList[TurningPoint] = Field(description="Pivotal moments")
                    consistent_strengths: TypeList[str] = Field(description="Strengths maintained over time")
                    consistent_weaknesses: TypeList[str] = Field(description="Persistent challenges")
                    notable_changes: TypeList[str] = Field(description="Significant changes observed")
                    trajectory_assessment: str = Field(description="Where the company is heading")
                    risk_evolution: str = Field(description="How risks have evolved")
                    investment_insights: TypeList[str] = Field(description="Investment timing insights")
                    forward_outlook: str = Field(description="Future projections")
                    overall_score_trend: str = Field(description="If scores available, how they've trended")
                    recommendations: TypeList[str] = Field(description="Action recommendations")

                result = provider.generate_with_retry(
                    prompt=full_prompt,
                    schema=MultiYearSynthesis,
                    max_retries=3,
                    retry_delay=10
                )

                self.api_key_manager.record_usage(api_key)

                if result:
                    # Store synthesis result
                    self.db.store_result(
                        run_id=synthesis_run_id,
                        ticker=ticker,
                        fiscal_year=0,  # 0 indicates synthesis
                        filing_type=filing_type,
                        result_type='MultiYearSynthesis',
                        result_data=result.model_dump()
                    )

                    self.db.update_run_status(synthesis_run_id, 'completed')
                    self.logger.info(f"Multi-year synthesis completed: {synthesis_run_id}")
                    return synthesis_run_id
                else:
                    raise Exception("AI returned no result")

            finally:
                self.api_key_manager.release_key(api_key)

        except Exception as e:
            error_msg = f"Multi-year synthesis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.db.update_run_status(synthesis_run_id, 'failed', error_msg)
            return None


def create_analysis_service(
    db: DatabaseRepository,
    config: Optional[FintelConfig] = None,
) -> AnalysisService:
    """
    Factory function to create an AnalysisService with production dependencies.

    This is the recommended way to create an AnalysisService for production use.
    It creates all necessary dependencies using the provided or default configuration.

    Args:
        db: Database repository instance
        config: Optional configuration (uses get_config() if not provided)

    Returns:
        Fully configured AnalysisService instance

    Example:
        >>> from fintel.ui.database import DatabaseRepository
        >>> db = DatabaseRepository()
        >>> service = create_analysis_service(db)
        >>> run_id = service.run_analysis('AAPL', 'fundamental')
    """
    config = config or get_config()

    return AnalysisService(
        db=db,
        config=config,
        key_manager=APIKeyManager(config.google_api_keys),
        rate_limiter=RateLimiter(),
        downloader=SECDownloader(),
        extractor=PDFExtractor(),
    )
