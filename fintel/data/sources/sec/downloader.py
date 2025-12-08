#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SEC Edgar downloader for 10-K filings.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

from pathlib import Path
from typing import List, Dict, Optional, Set
from sec_edgar_downloader import Downloader
import requests
import time

from fintel.core import get_logger, DownloadError


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

    def download(
        self,
        ticker: str,
        num_filings: int = 5,
        filing_type: str = "10-K"
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
                filing_path = self.base_path / "sec-edgar-filings" / ticker / filing_type
                self.logger.info(f"Downloaded {num_downloaded} filings to {filing_path}")
                return filing_path
            else:
                self.logger.warning(f"No {filing_type} filings found for {ticker}")
                return None

        except Exception as e:
            error_msg = f"Error downloading {ticker}: {str(e)}"
            self.logger.error(error_msg)
            raise DownloadError(error_msg) from e

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

            # SEC requires a delay between requests
            time.sleep(0.1)

            response = requests.get(url, headers=headers, timeout=10)
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

            # SEC requires a delay between requests
            time.sleep(0.1)

            response = requests.get(url, headers=headers, timeout=10)
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
