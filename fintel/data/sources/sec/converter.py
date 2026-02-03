#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML to PDF converter for SEC filings using Selenium.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

import os
import base64
import time
import shutil
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

from fintel.core import get_logger, get_config, ConversionError


def cleanup_orphaned_chrome_processes(logger=None) -> int:
    """
    Clean up orphaned Chrome/ChromeDriver processes.

    This is useful during long-running batch operations to prevent
    memory leaks from crashed or abandoned browser instances.

    Args:
        logger: Optional logger for output

    Returns:
        Number of processes killed
    """
    if logger is None:
        logger = get_logger(__name__)

    killed = 0
    system = platform.system().lower()

    try:
        if system in ('linux', 'darwin'):
            # Kill orphaned chromedriver processes
            for proc_name in ['chromedriver', 'chrome']:
                try:
                    result = subprocess.run(
                        ['pkill', '-f', proc_name],
                        capture_output=True,
                        timeout=10
                    )
                    # pkill returns 0 if processes were killed
                    if result.returncode == 0:
                        killed += 1
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout killing {proc_name} processes")
                except FileNotFoundError:
                    # pkill not available
                    pass

        elif system == 'windows':
            # Windows - use taskkill
            for proc_name in ['chromedriver.exe', 'chrome.exe']:
                try:
                    result = subprocess.run(
                        ['taskkill', '/F', '/IM', proc_name],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        killed += 1
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout killing {proc_name}")
                except FileNotFoundError:
                    pass

        if killed > 0:
            logger.info(f"Cleaned up {killed} orphaned Chrome process groups")
        else:
            logger.debug("No orphaned Chrome processes found")

    except Exception as e:
        logger.warning(f"Error during Chrome cleanup: {e}")

    return killed


class SECConverter:
    """
    Handles conversion of HTML SEC filings to PDF using headless Chrome.
    Supports all filing types (10-K, 10-Q, DEF 14A, 8-K, etc.)

    Example:
        converter = SECConverter()
        pdfs = converter.convert("AAPL", input_path, output_path, filing_type="10-K")
        converter.close()
    """

    def __init__(
        self,
        chrome_driver_path: Optional[str] = None,
        headless: bool = True,
        page_load_timeout: int = 60,
        script_timeout: int = 120,
        pdf_timeout: int = 180,
        conversion_retries: int = 2
    ):
        """
        Initialize the HTML to PDF converter.

        Args:
            chrome_driver_path: Optional path to ChromeDriver executable
            headless: Run browser in headless mode (default: True)
            page_load_timeout: Timeout for page loads in seconds (default: 60)
            script_timeout: Timeout for script execution in seconds (default: 120)
            pdf_timeout: Timeout for PDF generation in seconds (default: 180)
            conversion_retries: Number of retries for failed conversions (default: 2)
        """
        config = get_config()

        self.chrome_driver_path = chrome_driver_path or config.chrome_driver_path
        self.headless = headless if headless is not None else config.headless_browser
        self.logger = get_logger(f"{__name__}.SECConverter")
        self.driver = None

        # Timeout configuration
        self.page_load_timeout = page_load_timeout
        self.script_timeout = script_timeout
        self.pdf_timeout = pdf_timeout
        self.conversion_retries = conversion_retries

        # PDF print settings for Chrome
        self.pdf_settings = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }

    def _setup_driver(self):
        """Set up Selenium WebDriver with Chrome and proper timeouts."""
        if self.driver:
            return self.driver

        self.logger.info("Setting up Chrome browser...")
        try:
            options = ChromeOptions()

            if self.headless:
                options.add_argument("--headless")

            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            if self.chrome_driver_path and os.path.exists(self.chrome_driver_path):
                service = ChromeService(executable_path=self.chrome_driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                service = ChromeService()
                self.driver = webdriver.Chrome(service=service, options=options)

            # Set timeouts to prevent hanging
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.set_script_timeout(self.script_timeout)

            self.logger.info(
                f"Browser setup complete (timeouts: page={self.page_load_timeout}s, "
                f"script={self.script_timeout}s)"
            )
            return self.driver

        except Exception as e:
            error_msg = f"Error setting up WebDriver: {str(e)}"
            self.logger.error(error_msg)
            raise ConversionError(error_msg) from e

    def _restart_driver(self):
        """Restart the WebDriver to recover from timeout/crash."""
        self.logger.info("Restarting WebDriver...")
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.logger.warning(f"Error closing driver during restart: {e}")
        self.driver = None
        return self._setup_driver()

    def _convert_html_to_pdf(self, html_path: Path, pdf_path: Path, restart_on_failure: bool = True) -> bool:
        """
        Convert a single HTML file to PDF.

        Args:
            html_path: Path to HTML file
            pdf_path: Path for output PDF
            restart_on_failure: If True, restart driver on timeout errors

        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.driver = self._setup_driver()
            if not self.driver:
                return False

        try:
            # Load HTML file
            file_url = f"file:///{str(html_path.absolute()).replace(os.path.sep, '/')}"
            self.logger.debug(f"Loading HTML: {file_url}")

            try:
                self.driver.get(file_url)
            except Exception as e:
                error_str = str(e).lower()
                if 'timeout' in error_str or 'timed out' in error_str:
                    self.logger.error(f"Page load timeout for {html_path.name}: {e}")
                    if restart_on_failure:
                        self._restart_driver()
                    return False
                raise

            # Dynamic wait based on file size (larger files need more render time)
            try:
                file_size_kb = html_path.stat().st_size / 1024
                # Scale wait time: 3s minimum, up to 15s for very large files
                wait_time = min(max(3, int(file_size_kb / 100)), 15)
                self.logger.debug(f"Waiting {wait_time}s for page render (file size: {file_size_kb:.1f}KB)")
            except Exception:
                wait_time = 5  # Fallback if we can't get file size
            time.sleep(wait_time)

            # Convert to PDF
            try:
                result = self.driver.execute_cdp_cmd("Page.printToPDF", self.pdf_settings)
            except Exception as e:
                error_str = str(e).lower()
                if 'timeout' in error_str or 'timed out' in error_str or 'connectionpool' in error_str:
                    self.logger.error(f"PDF generation timeout for {html_path.name}: {e}")
                    if restart_on_failure:
                        self._restart_driver()
                    return False
                raise

            self.driver.get("about:blank")  # Clear page

            # Decode and save PDF
            pdf_data = base64.b64decode(result['data'])
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            with open(pdf_path, 'wb') as f:
                f.write(pdf_data)

            return True

        except Exception as e:
            self.logger.error(f"Error converting {html_path.name}: {str(e)}")
            if pdf_path.exists():
                pdf_path.unlink()  # Remove partial file
            return False

    @staticmethod
    def _get_filing_year_from_accession(accession_str: str) -> Optional[int]:
        """
        Extract year from SEC accession number.

        Args:
            accession_str: Accession number (e.g., '0000320193-25-000079')

        Returns:
            Filing year (e.g., 2025) or None if extraction fails
        """
        try:
            parts = accession_str.split('-')
            if len(parts) > 1 and parts[1].isdigit():
                year_short = int(parts[1])
                # Convert 2-digit year to 4-digit
                return 2000 + year_short if year_short < 50 else 1900 + year_short
        except Exception:
            pass
        return None

    @staticmethod
    def _get_filing_date_from_metadata(
        accession_dir_name: str,
        filing_metadata: Optional[List[Dict]]
    ) -> Optional[str]:
        """
        Get filing_date from metadata by matching accession number.

        Args:
            accession_dir_name: Directory name (accession number format)
            filing_metadata: List of filing metadata dicts from SEC API

        Returns:
            Filing date in YYYY-MM-DD format, or None if not found
        """
        if not filing_metadata:
            return None

        # Normalize accession number for comparison (remove dashes)
        accession_normalized = accession_dir_name.replace('-', '')

        for filing in filing_metadata:
            filing_accession = filing.get('accession_number', '')
            if filing_accession.replace('-', '') == accession_normalized:
                return filing.get('filing_date')

        return None

    def convert(
        self,
        ticker: str,
        input_path: Path,
        output_path: Optional[Path] = None,
        cleanup_originals: bool = True,
        filing_type: str = "10-K",
        filing_metadata: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert downloaded SEC filings to PDF.

        Args:
            ticker: Stock ticker symbol
            input_path: Path to downloaded filings (contains accession dirs)
            output_path: Optional custom output path for PDFs
            cleanup_originals: Whether to delete original HTML files after conversion
            filing_type: Type of SEC filing (e.g., '10-K', '10-Q', 'DEF 14A')
            filing_metadata: Optional list of filing metadata from SEC API
                            (used to get filing_date for unique filenames)

        Returns:
            List of dicts with 'pdf_path', 'year', 'filing_date', and 'ticker'
            for each converted filing
        """
        ticker = ticker.upper()

        if output_path is None:
            output_path = input_path.parent / "PDF_Filings"

        output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Converting {filing_type} filings for {ticker} to PDF")
        self.logger.info(f"Input: {input_path}")
        self.logger.info(f"Output: {output_path}")

        converted_pdfs = []

        if not input_path.exists():
            self.logger.error(f"Input path does not exist: {input_path}")
            return converted_pdfs

        # Iterate through accession number directories
        for accession_dir in input_path.iterdir():
            if not accession_dir.is_dir():
                continue

            year = self._get_filing_year_from_accession(accession_dir.name)
            if not year:
                self.logger.warning(f"Could not extract year from {accession_dir.name}")
                continue

            # Find HTML file to convert (priority order)
            html_file = None
            for priority_name in ['primary-document.html', 'filing-details.html', 'full-submission.txt']:
                candidate = accession_dir / priority_name
                if candidate.exists():
                    html_file = candidate
                    break

            if not html_file:
                # Find any HTML/HTM file
                html_files = list(accession_dir.glob("*.html")) + list(accession_dir.glob("*.htm"))
                if html_files:
                    html_file = html_files[0]
                else:
                    # Try .txt as fallback
                    txt_files = list(accession_dir.glob("*.txt"))
                    if txt_files:
                        html_file = txt_files[0]

            if not html_file:
                self.logger.warning(f"No HTML file found in {accession_dir.name}")
                continue

            # Convert to PDF
            # Replace spaces with underscores for filesystem compatibility
            safe_filing_type = filing_type.replace(" ", "_")

            # Get filing_date from metadata for unique filename
            filing_date = self._get_filing_date_from_metadata(accession_dir.name, filing_metadata)

            # Universal naming: use filing_date if available, otherwise fallback
            if filing_date:
                # Format: TICKER_FILING-TYPE_YYYY-MM-DD.pdf
                pdf_filename = f"{ticker}_{safe_filing_type}_{filing_date}.pdf"
            else:
                # Fallback: use year + accession suffix for uniqueness
                accession_suffix = accession_dir.name.split('-')[-1] if '-' in accession_dir.name else accession_dir.name[-4:]
                pdf_filename = f"{ticker}_{safe_filing_type}_{year}_{accession_suffix}.pdf"

            pdf_path = output_path / pdf_filename

            self.logger.info(f"Converting filing to PDF: {pdf_filename}")

            # Retry logic for failed conversions
            success = False
            for attempt in range(self.conversion_retries + 1):
                if self._convert_html_to_pdf(html_file, pdf_path):
                    success = True
                    break
                else:
                    if attempt < self.conversion_retries:
                        self.logger.warning(
                            f"Conversion failed for {pdf_filename}, "
                            f"retrying ({attempt + 1}/{self.conversion_retries})..."
                        )
                        # Driver restart happens inside _convert_html_to_pdf on timeout

            if success:
                self.logger.info(f"Successfully converted: {pdf_filename}")
                converted_pdfs.append({
                    'pdf_path': pdf_path,
                    'year': year,
                    'filing_date': filing_date,
                    'ticker': ticker,
                    'accession_number': accession_dir.name
                })

                # Cleanup original if requested
                if cleanup_originals:
                    try:
                        shutil.rmtree(accession_dir)
                        self.logger.info(f"Deleted original folder: {accession_dir.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete {accession_dir.name}: {str(e)}")
            else:
                self.logger.error(f"Failed to convert {pdf_filename} after {self.conversion_retries + 1} attempts")

        self.logger.info(f"Converted {len(converted_pdfs)} filings for {ticker}")
        return converted_pdfs

    def convert_batch(
        self,
        ticker_paths: Dict[str, Path],
        output_base: Optional[Path] = None,
        cleanup_originals: bool = True,
        filing_type: str = "10-K",
        ticker_metadata: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert multiple tickers' filings to PDF.

        Args:
            ticker_paths: Dict mapping ticker to input path
            output_base: Base path for PDF output
            cleanup_originals: Whether to delete original HTML files
            filing_type: Type of SEC filing (e.g., '10-K', '10-Q', 'DEF 14A')
            ticker_metadata: Optional dict mapping ticker to filing metadata list

        Returns:
            Dict mapping ticker to list of converted PDFs
        """
        results = {}
        for ticker, input_path in ticker_paths.items():
            if input_path:
                output_path = output_base / ticker if output_base else None
                filing_metadata = ticker_metadata.get(ticker) if ticker_metadata else None
                pdfs = self.convert(
                    ticker, input_path, output_path, cleanup_originals,
                    filing_type, filing_metadata
                )
                results[ticker] = pdfs

        return results

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Browser closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
