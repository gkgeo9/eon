#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SEC Edgar downloader for 10-K filings.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from sec_edgar_downloader import Downloader
import requests

from fintel.core import get_logger, DownloadError, is_annual_filing, is_quarterly_filing
from fintel.data.sources.sec.request_queue import get_sec_request_queue


class SECDownloader:
    """
    Handles downloading 10-K filings from SEC EDGAR.

    Example:
        downloader = SECDownloader(
            company_name="Research Script",
            user_email="you@example.com"
        )
        filing_path = downloader.download("AAPL", num_filings=5)
    """

    def __init__(
        self,
        company_name: str = "Research Script",
        user_email: str = "user@example.com",
        base_path: Optional[Path] = None
    ):
        """
        Initialize the SEC downloader.

        Args:
            company_name: Your company/script name for SEC compliance
            user_email: Your email for SEC compliance (required by SEC)
            base_path: Base directory for downloads (default: ./data/raw/sec_filings)
        """
        self.company_name = company_name
        self.user_email = user_email

        if base_path is None:
            from fintel.core import get_config
            config = get_config()
            self.base_path = config.get_data_path("raw", "sec_filings")
        else:
            self.base_path = Path(base_path)

        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.SECDownloader")

    def _make_sec_request(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: int = 10
    ) -> requests.Response:
        """
        Make a rate-limited request to SEC EDGAR.

        All SEC API calls should go through this method to ensure
        proper rate limiting and cross-process coordination.

        Args:
            url: SEC API URL to request
            headers: Request headers (must include User-Agent for SEC compliance)
            timeout: Request timeout in seconds

        Returns:
            Response object from the SEC API

        Raises:
            requests.RequestException: If the request fails
        """
        queue = get_sec_request_queue()
        return queue.execute_with_lock(
            lambda: requests.get(url, headers=headers, timeout=timeout)
        )

    def _get_filing_path(self, identifier: str, filing_type: str) -> Path:
        return self.base_path / "sec-edgar-filings" / identifier / filing_type

    def _count_existing_filings(self, filing_path: Path) -> int:
        if not filing_path.exists():
            return 0
        return sum(1 for entry in filing_path.iterdir() if entry.is_dir())

    def download(
        self,
        ticker: str,
        num_filings: int = 5,
        filing_type: str = "10-K",
        use_cache: bool = True
    ) -> Optional[Path]:
        """
        Download filings for a single ticker.

        Args:
            ticker: Stock ticker symbol
            num_filings: Number of recent filings to download
            filing_type: Type of filing (default: 10-K)

        Returns:
            Path to downloaded filings directory, or None if failed

        Raises:
            DownloadError: If download fails
        """
        ticker = ticker.upper()
        filing_path = self._get_filing_path(ticker, filing_type)
        if use_cache:
            existing_count = self._count_existing_filings(filing_path)
            if existing_count >= num_filings:
                self.logger.info(
                    f"Using cached {filing_type} filings for {ticker} "
                    f"({existing_count} already downloaded)"
                )
                return filing_path

        self.logger.info(f"Downloading {num_filings} {filing_type} filings for {ticker}")

        try:
            dl = Downloader(
                self.company_name,
                self.user_email,
                str(self.base_path)
            )

            num_downloaded = dl.get(
                filing_type,
                ticker,
                limit=num_filings,
                download_details=True
            )

            if num_downloaded > 0:
                self.logger.info(f"Downloaded {num_downloaded} filings to {filing_path}")
                return filing_path
            else:
                self.logger.warning(f"No {filing_type} filings found for {ticker}")
                return None

        except Exception as e:
            error_msg = f"Error downloading {ticker}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e

    def download_with_metadata(
        self,
        ticker: str,
        num_filings: int = 5,
        filing_type: str = "10-K"
    ) -> Tuple[Optional[Path], List[Dict]]:
        """
        Download filings and return both path and metadata.

        This is the preferred method for downloading as it returns the filing
        metadata needed for unique filename generation (filing_date, etc.).

        Args:
            ticker: Stock ticker symbol
            num_filings: Number of recent filings to download
            filing_type: Type of filing (default: 10-K)

        Returns:
            Tuple of (filing_path, metadata_list) where:
            - filing_path: Path to downloaded filings directory, or None if failed
            - metadata_list: List of filing metadata dicts with:
                - accession_number: Unique filing identifier
                - filing_date: When filed with SEC (YYYY-MM-DD)
                - report_date: Period end date
                - fiscal_year: Fiscal year (derived from report_date)
                - primary_document: Main document filename

        Raises:
            DownloadError: If download fails
        """
        ticker = ticker.upper()
        self.logger.info(f"Downloading {num_filings} {filing_type} filings with metadata for {ticker}")

        # First, get metadata for the filings we're about to download
        try:
            metadata = self.get_available_filings(ticker, filing_type, limit=num_filings)
        except Exception as e:
            self.logger.warning(f"Could not fetch metadata for {ticker}: {e}")
            metadata = []

        # Then download the filings
        filing_path = self.download(ticker, num_filings, filing_type)

        return filing_path, metadata

    def download_batch(
        self,
        tickers: List[str],
        num_filings: int = 5,
        filing_type: str = "10-K"
    ) -> Dict[str, Optional[Path]]:
        """
        Download filings for multiple tickers.

        Args:
            tickers: List of stock ticker symbols
            num_filings: Number of recent filings to download per ticker
            filing_type: Type of filing (default: 10-K)

        Returns:
            Dictionary mapping ticker -> filing path (or None if failed)
        """
        results = {}

        for ticker in tickers:
            try:
                filing_path = self.download(ticker, num_filings, filing_type)
                results[ticker] = filing_path
            except DownloadError as e:
                self.logger.error(f"Failed to download {ticker}: {e}")
                results[ticker] = None

        successful = sum(1 for path in results.values() if path is not None)
        self.logger.info(
            f"Downloaded filings for {successful}/{len(tickers)} tickers"
        )

        return results

    def get_available_filing_types(self, ticker: str) -> List[str]:
        """
        Query SEC API to get all available filing types for a ticker.

        This queries the SEC EDGAR company submissions endpoint to retrieve
        all filing types that have been filed by the company.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of available filing types (e.g., ['10-K', '10-Q', '8-K', ...])
            Sorted by frequency (most common first)

        Raises:
            DownloadError: If unable to query SEC API or ticker not found
        """
        ticker = ticker.upper()
        self.logger.info(f"Querying available filing types for {ticker}")

        try:
            # First, get the CIK (Central Index Key) for the ticker
            # SEC provides a ticker-to-CIK mapping file
            cik = self._get_cik_from_ticker(ticker)

            if not cik:
                raise DownloadError(f"Could not find CIK for ticker {ticker}")

            # Query the company submissions endpoint
            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            self.logger.debug(f"Fetching submissions from {url}")

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()

            # Extract filing types from recent filings
            filing_types: Dict[str, int] = {}

            if 'filings' in data and 'recent' in data['filings']:
                recent = data['filings']['recent']
                if 'form' in recent:
                    for form in recent['form']:
                        filing_types[form] = filing_types.get(form, 0) + 1

            if not filing_types:
                self.logger.warning(f"No filings found for {ticker}")
                return []

            # Sort by frequency (most common first)
            sorted_types = sorted(filing_types.items(), key=lambda x: x[1], reverse=True)
            result = [form for form, _ in sorted_types]

            self.logger.info(f"Found {len(result)} filing types for {ticker}: {result[:10]}")
            return result

        except requests.RequestException as e:
            error_msg = f"Error querying SEC API for {ticker}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error getting filing types for {ticker}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e

    def _get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) from ticker symbol.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string padded to 10 digits, or None if not found
        """
        ticker = ticker.upper()

        try:
            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'www.sec.gov'
            }

            # Use the company tickers endpoint
            url = "https://www.sec.gov/files/company_tickers.json"

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()

            # Search for the ticker in the data
            for key, company in data.items():
                if company.get('ticker', '').upper() == ticker:
                    cik = str(company.get('cik_str', ''))
                    # Pad CIK to 10 digits
                    return cik.zfill(10)

            self.logger.warning(f"Ticker {ticker} not found in SEC database")
            return None

        except Exception as e:
            self.logger.error(f"Error getting CIK for {ticker}: {str(e)}")
            return None

    def get_filing_path(self, ticker: str, filing_type: str = "10-K") -> Path:
        """
        Get the path where filings for a ticker would be stored.

        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (default: 10-K)

        Returns:
            Path to filing directory
        """
        return self.base_path / "sec-edgar-filings" / ticker.upper() / filing_type

    def get_filing_periodicity(self, filing_type: str) -> str:
        """
        Determine the periodicity of a filing type.

        Args:
            filing_type: SEC filing type (e.g., 10-K, 10-Q, 8-K)

        Returns:
            One of: 'annual', 'quarterly', 'event'
        """
        # Use shared utilities for consistent filing type classification
        if is_annual_filing(filing_type):
            return 'annual'
        elif is_quarterly_filing(filing_type):
            return 'quarterly'
        else:
            return 'event'

    def get_available_filings(
        self,
        ticker: str,
        filing_type: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get list of available filings with their metadata.

        This is useful for selecting specific filings to download,
        especially for quarterly or event-based filings.

        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (e.g., 10-K, 10-Q, 8-K)
            limit: Maximum number of filings to return

        Returns:
            List of filing metadata dicts with keys:
            - accession_number: Unique filing identifier
            - filing_date: When filed with SEC
            - report_date: Period end date (fiscal period covered)
            - fiscal_year: Fiscal year (derived from report_date)
            - fiscal_quarter: Quarter for 10-Q (1, 2, or 3), None for others
            - primary_document: Main document filename
        """
        ticker = ticker.upper()
        filing_type_upper = filing_type.upper()

        try:
            cik = self._get_cik_from_ticker(ticker)
            if not cik:
                raise DownloadError(f"Could not find CIK for ticker {ticker}")

            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()
            fiscal_year_end = data.get('fiscalYearEnd', '1231')  # MMDD format

            if 'filings' not in data or 'recent' not in data['filings']:
                return []

            recent = data['filings']['recent']
            forms = recent.get('form', [])
            filing_dates = recent.get('filingDate', [])
            report_dates = recent.get('reportDate', [])
            accession_numbers = recent.get('accessionNumber', [])
            primary_docs = recent.get('primaryDocument', [])

            filings = []
            for i, form in enumerate(forms):
                # Match filing type (handle amendments like 10-K/A)
                if form.upper() == filing_type_upper or form.upper() == f"{filing_type_upper}/A":
                    if i >= len(report_dates) or not report_dates[i]:
                        continue

                    report_date = report_dates[i]
                    fiscal_year = self._get_fiscal_year(report_date, fiscal_year_end)
                    fiscal_quarter = self._get_fiscal_quarter(report_date, fiscal_year_end, filing_type_upper)

                    filings.append({
                        'accession_number': accession_numbers[i] if i < len(accession_numbers) else None,
                        'filing_date': filing_dates[i] if i < len(filing_dates) else None,
                        'report_date': report_date,
                        'fiscal_year': fiscal_year,
                        'fiscal_quarter': fiscal_quarter,
                        'primary_document': primary_docs[i] if i < len(primary_docs) else None,
                        'form': form
                    })

                    if len(filings) >= limit:
                        break

            self.logger.info(f"Found {len(filings)} {filing_type} filings for {ticker}")
            return filings

        except requests.RequestException as e:
            self.logger.error(f"Error querying SEC API for {ticker}: {str(e)}")
            raise DownloadError(f"Error querying SEC API: {str(e)}") from e

    def _get_fiscal_year(self, report_date: str, fiscal_year_end: str) -> int:
        """
        Determine fiscal year from report date and fiscal year end.

        Args:
            report_date: Report period end date (YYYY-MM-DD)
            fiscal_year_end: Fiscal year end in MMDD format

        Returns:
            Fiscal year as integer
        """
        from datetime import datetime

        report_dt = datetime.strptime(report_date, '%Y-%m-%d')

        # Parse fiscal year end (MMDD format)
        fy_month = int(fiscal_year_end[:2])
        fy_day = int(fiscal_year_end[2:])

        # If report date is after fiscal year end month, it's that calendar year's fiscal year
        # If before or equal, it's the previous calendar year's fiscal year
        if (report_dt.month, report_dt.day) > (fy_month, fy_day):
            return report_dt.year + 1
        else:
            return report_dt.year

    def _get_fiscal_quarter(
        self,
        report_date: str,
        fiscal_year_end: str,
        filing_type: str
    ) -> Optional[int]:
        """
        Determine fiscal quarter from report date.

        Only applicable for quarterly filings (10-Q).

        Args:
            report_date: Report period end date (YYYY-MM-DD)
            fiscal_year_end: Fiscal year end in MMDD format
            filing_type: Filing type

        Returns:
            Quarter (1, 2, or 3) for 10-Q, None for others
        """
        if filing_type not in ('10-Q', '10Q'):
            return None

        from datetime import datetime

        report_dt = datetime.strptime(report_date, '%Y-%m-%d')
        fy_month = int(fiscal_year_end[:2])

        # Calculate months from fiscal year start
        # Fiscal year starts the month after fiscal year end
        fy_start_month = (fy_month % 12) + 1

        # Calculate which month of fiscal year this report is in
        months_diff = (report_dt.month - fy_start_month) % 12

        # Q1 = months 1-3, Q2 = months 4-6, Q3 = months 7-9, Q4 (10-K) = months 10-12
        if months_diff < 3:
            return 1
        elif months_diff < 6:
            return 2
        elif months_diff < 9:
            return 3
        else:
            return None  # Q4 would be covered by 10-K

    def get_fiscal_year_end(self, ticker: str) -> Optional[str]:
        """
        Get the fiscal year end date for a company.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Fiscal year end in MMDD format, or None if not found
        """
        ticker = ticker.upper()

        try:
            cik = self._get_cik_from_ticker(ticker)
            if not cik:
                return None

            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()
            return data.get('fiscalYearEnd', '1231')

        except Exception as e:
            self.logger.error(f"Error getting fiscal year end for {ticker}: {str(e)}")
            return None

    # ==================== CIK-Direct Methods ====================
    # These methods bypass ticker lookup and query SEC directly with CIK.
    # Essential for delisted companies like Enron that don't appear in
    # company_tickers.json (which only lists active companies).

    def get_company_info_from_cik(self, cik: str) -> Optional[Dict]:
        """
        Get company information directly from SEC using CIK.

        This bypasses company_tickers.json and queries SEC directly,
        allowing access to delisted companies like Enron.

        Args:
            cik: CIK number (will be zero-padded to 10 digits)

        Returns:
            Dictionary with company info:
            - cik: Zero-padded CIK
            - company_name: Official company name
            - sic_code: Standard Industrial Classification code
            - sic_description: SIC description
            - state_of_incorporation: State where incorporated
            - former_names: List of former company names
            - fiscal_year_end: MMDD format
            Or None if not found
        """
        cik_padded = cik.zfill(10)

        try:
            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
            self.logger.info(f"Fetching company info for CIK {cik_padded}")

            response = self._make_sec_request(url, headers)

            if response.status_code == 404:
                self.logger.warning(f"CIK {cik} not found in SEC database")
                return None

            response.raise_for_status()
            data = response.json()

            return {
                'cik': cik_padded,
                'company_name': data.get('name', 'Unknown'),
                'sic_code': data.get('sic'),
                'sic_description': data.get('sicDescription'),
                'state_of_incorporation': data.get('stateOfIncorporation'),
                'former_names': data.get('formerNames', []),
                'fiscal_year_end': data.get('fiscalYearEnd', '1231')
            }

        except requests.RequestException as e:
            self.logger.error(f"Error fetching company info for CIK {cik}: {e}")
            return None

    def download_by_cik(
        self,
        cik: str,
        num_filings: int = 5,
        filing_type: str = "10-K",
        use_cache: bool = True
    ) -> Optional[Path]:
        """
        Download filings using CIK directly (bypasses ticker lookup).

        This is essential for delisted companies that don't appear
        in company_tickers.json.

        Args:
            cik: CIK number (will be zero-padded)
            num_filings: Number of recent filings to download
            filing_type: Type of filing (default: 10-K)

        Returns:
            Path to downloaded filings directory, or None if failed

        Raises:
            DownloadError: If download fails
        """
        cik_padded = cik.zfill(10)
        filing_path = self._get_filing_path(cik_padded, filing_type)
        if use_cache:
            existing_count = self._count_existing_filings(filing_path)
            if existing_count >= num_filings:
                self.logger.info(
                    f"Using cached {filing_type} filings for CIK {cik_padded} "
                    f"({existing_count} already downloaded)"
                )
                return filing_path

        self.logger.info(f"Downloading {num_filings} {filing_type} filings for CIK {cik_padded}")

        try:
            dl = Downloader(
                self.company_name,
                self.user_email,
                str(self.base_path)
            )

            # The sec_edgar_downloader library accepts CIK as the identifier
            num_downloaded = dl.get(
                filing_type,
                cik_padded,
                limit=num_filings,
                download_details=True
            )

            if num_downloaded > 0:
                # Filings are stored under CIK directory
                self.logger.info(f"Downloaded {num_downloaded} filings to {filing_path}")
                return filing_path
            else:
                self.logger.warning(f"No {filing_type} filings found for CIK {cik_padded}")
                return None

        except Exception as e:
            error_msg = f"Error downloading CIK {cik}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e

    def download_with_metadata_by_cik(
        self,
        cik: str,
        num_filings: int = 5,
        filing_type: str = "10-K"
    ) -> Tuple[Optional[Path], List[Dict]]:
        """
        Download filings by CIK and return both path and metadata.

        Similar to download_with_metadata but uses CIK directly.

        Args:
            cik: CIK number (will be zero-padded)
            num_filings: Number of recent filings to download
            filing_type: Type of filing (default: 10-K)

        Returns:
            Tuple of (filing_path, metadata_list)
        """
        cik_padded = cik.zfill(10)
        self.logger.info(f"Downloading {num_filings} {filing_type} filings with metadata for CIK {cik_padded}")

        # Get metadata using CIK directly
        try:
            metadata = self.get_available_filings_by_cik(cik_padded, filing_type, limit=num_filings)
        except Exception as e:
            self.logger.warning(f"Could not fetch metadata for CIK {cik}: {e}")
            metadata = []

        # Download filings
        filing_path = self.download_by_cik(cik_padded, num_filings, filing_type)

        return filing_path, metadata

    def get_available_filings_by_cik(
        self,
        cik: str,
        filing_type: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get available filings metadata using CIK directly.

        Mirrors get_available_filings() but skips ticker->CIK lookup.

        Args:
            cik: CIK number (will be zero-padded)
            filing_type: Type of filing (e.g., 10-K, 10-Q, 8-K)
            limit: Maximum number of filings to return

        Returns:
            List of filing metadata dicts
        """
        cik_padded = cik.zfill(10)
        filing_type_upper = filing_type.upper()

        try:
            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()
            fiscal_year_end = data.get('fiscalYearEnd', '1231')

            if 'filings' not in data or 'recent' not in data['filings']:
                return []

            recent = data['filings']['recent']
            forms = recent.get('form', [])
            filing_dates = recent.get('filingDate', [])
            report_dates = recent.get('reportDate', [])
            accession_numbers = recent.get('accessionNumber', [])
            primary_docs = recent.get('primaryDocument', [])

            filings = []
            for i, form in enumerate(forms):
                if form.upper() == filing_type_upper or form.upper() == f"{filing_type_upper}/A":
                    if i >= len(report_dates) or not report_dates[i]:
                        continue

                    report_date = report_dates[i]
                    fiscal_year = self._get_fiscal_year(report_date, fiscal_year_end)
                    fiscal_quarter = self._get_fiscal_quarter(report_date, fiscal_year_end, filing_type_upper)

                    filings.append({
                        'accession_number': accession_numbers[i] if i < len(accession_numbers) else None,
                        'filing_date': filing_dates[i] if i < len(filing_dates) else None,
                        'report_date': report_date,
                        'fiscal_year': fiscal_year,
                        'fiscal_quarter': fiscal_quarter,
                        'primary_document': primary_docs[i] if i < len(primary_docs) else None,
                        'form': form
                    })

                    if len(filings) >= limit:
                        break

            self.logger.info(f"Found {len(filings)} {filing_type} filings for CIK {cik_padded}")
            return filings

        except requests.RequestException as e:
            self.logger.error(f"Error querying SEC API for CIK {cik}: {str(e)}")
            raise DownloadError(f"Error querying SEC API: {str(e)}") from e

    def get_available_filing_types_by_cik(self, cik: str) -> List[str]:
        """
        Query SEC API to get all available filing types for a CIK.

        Args:
            cik: CIK number (will be zero-padded)

        Returns:
            List of available filing types sorted by frequency
        """
        cik_padded = cik.zfill(10)
        self.logger.info(f"Querying available filing types for CIK {cik_padded}")

        try:
            headers = {
                'User-Agent': f'{self.company_name} {self.user_email}',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

            response = self._make_sec_request(url, headers)
            response.raise_for_status()

            data = response.json()

            filing_types: Dict[str, int] = {}

            if 'filings' in data and 'recent' in data['filings']:
                recent = data['filings']['recent']
                if 'form' in recent:
                    for form in recent['form']:
                        filing_types[form] = filing_types.get(form, 0) + 1

            if not filing_types:
                self.logger.warning(f"No filings found for CIK {cik_padded}")
                return []

            sorted_types = sorted(filing_types.items(), key=lambda x: x[1], reverse=True)
            result = [form for form, _ in sorted_types]

            self.logger.info(f"Found {len(result)} filing types for CIK {cik_padded}: {result[:10]}")
            return result

        except requests.RequestException as e:
            error_msg = f"Error querying SEC API for CIK {cik}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e

    def get_filing_path_by_cik(self, cik: str, filing_type: str = "10-K") -> Path:
        """
        Get the path where filings for a CIK would be stored.

        Args:
            cik: CIK number (will be zero-padded)
            filing_type: Type of filing (default: 10-K)

        Returns:
            Path to filing directory
        """
        return self.base_path / "sec-edgar-filings" / cik.zfill(10) / filing_type
