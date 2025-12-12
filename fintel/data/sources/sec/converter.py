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
from pathlib import Path
from typing import List, Dict, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

from fintel.core import get_logger, get_config, ConversionError


class SECConverter:
    """
    Handles conversion of HTML SEC filings to PDF using headless Chrome.
    Supports all filing types (10-K, 10-Q, DEF 14A, 8-K, etc.)

    Example:
        converter = SECConverter()
        pdfs = converter.convert("AAPL", input_path, output_path, filing_type="10-K")
        converter.close()
    """

    def __init__(self, chrome_driver_path: Optional[str] = None, headless: bool = True):
        """
        Initialize the HTML to PDF converter.

        Args:
            chrome_driver_path: Optional path to ChromeDriver executable
            headless: Run browser in headless mode (default: True)
        """
        config = get_config()

        self.chrome_driver_path = chrome_driver_path or config.chrome_driver_path
        self.headless = headless if headless is not None else config.headless_browser
        self.logger = get_logger(f"{__name__}.SECConverter")
        self.driver = None

        # PDF print settings for Chrome
        self.pdf_settings = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }

    def _setup_driver(self):
        """Set up Selenium WebDriver with Chrome."""
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

            self.logger.info("Browser setup complete")
            return self.driver

        except Exception as e:
            error_msg = f"Error setting up WebDriver: {str(e)}"
            self.logger.error(error_msg)
            raise ConversionError(error_msg) from e

    def _convert_html_to_pdf(self, html_path: Path, pdf_path: Path) -> bool:
        """
        Convert a single HTML file to PDF.

        Args:
            html_path: Path to HTML file
            pdf_path: Path for output PDF

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
            self.driver.get(file_url)
            time.sleep(3)  # Wait for page to load

            # Convert to PDF
            result = self.driver.execute_cdp_cmd("Page.printToPDF", self.pdf_settings)
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

    def convert(
        self,
        ticker: str,
        input_path: Path,
        output_path: Optional[Path] = None,
        cleanup_originals: bool = True,
        filing_type: str = "10-K"
    ) -> List[Dict[str, Any]]:
        """
        Convert downloaded SEC filings to PDF.

        Args:
            ticker: Stock ticker symbol
            input_path: Path to downloaded filings (contains accession dirs)
            output_path: Optional custom output path for PDFs
            cleanup_originals: Whether to delete original HTML files after conversion
            filing_type: Type of SEC filing (e.g., '10-K', '10-Q', 'DEF 14A')

        Returns:
            List of dicts with 'pdf_path', 'year', and 'ticker' for each converted filing
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
            pdf_filename = f"{ticker}_{safe_filing_type}_{year}.pdf"
            pdf_path = output_path / pdf_filename

            self.logger.info(f"Converting {year} filing to PDF...")
            if self._convert_html_to_pdf(html_file, pdf_path):
                self.logger.info(f"Successfully converted {year} filing")
                converted_pdfs.append({
                    'pdf_path': pdf_path,
                    'year': year,
                    'ticker': ticker
                })

                # Cleanup original if requested
                if cleanup_originals:
                    try:
                        shutil.rmtree(accession_dir)
                        self.logger.info(f"Deleted original folder: {accession_dir.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete {accession_dir.name}: {str(e)}")

        self.logger.info(f"Converted {len(converted_pdfs)} filings for {ticker}")
        return converted_pdfs

    def convert_batch(
        self,
        ticker_paths: Dict[str, Path],
        output_base: Optional[Path] = None,
        cleanup_originals: bool = True,
        filing_type: str = "10-K"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert multiple tickers' filings to PDF.

        Args:
            ticker_paths: Dict mapping ticker to input path
            output_base: Base path for PDF output
            cleanup_originals: Whether to delete original HTML files
            filing_type: Type of SEC filing (e.g., '10-K', '10-Q', 'DEF 14A')

        Returns:
            Dict mapping ticker to list of converted PDFs
        """
        results = {}
        for ticker, input_path in ticker_paths.items():
            if input_path:
                output_path = output_base / ticker if output_base else None
                pdfs = self.convert(ticker, input_path, output_path, cleanup_originals, filing_type)
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
