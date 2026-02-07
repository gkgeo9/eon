#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF text extractor for SEC filings.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

from pathlib import Path
from typing import Optional

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from eon.core import get_logger, ExtractionError


class PDFExtractor:
    """
    Extracts text content from PDF files.

    Example:
        extractor = PDFExtractor()
        text = extractor.extract_text(pdf_path)
    """

    def __init__(self):
        """Initialize the PDF extractor."""
        self.logger = get_logger(f"{__name__}.PDFExtractor")

        if not PYPDF2_AVAILABLE:
            self.logger.warning(
                "PyPDF2 not installed. Install with: pip install PyPDF2"
            )

    def extract_text(self, pdf_path: Path) -> Optional[str]:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None if extraction fails

        Raises:
            ExtractionError: If extraction fails
        """
        if not PYPDF2_AVAILABLE:
            raise ExtractionError(
                "PyPDF2 is not installed. Install with: pip install PyPDF2"
            )

        if not pdf_path.exists():
            raise ExtractionError(f"PDF file not found: {pdf_path}")

        try:
            self.logger.info(f"Extracting text from {pdf_path.name}")

            reader = PdfReader(str(pdf_path))
            text = ""

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                except Exception as e:
                    self.logger.warning(
                        f"Could not extract text from page {page_num}: {e}"
                    )

            num_pages = len(reader.pages)
            text_length = len(text)

            self.logger.info(
                f"Extracted {text_length:,} characters from {num_pages} pages"
            )

            if not text.strip():
                self.logger.warning("No text extracted from PDF")
                return None

            return text

        except Exception as e:
            error_msg = f"Error extracting text from {pdf_path.name}: {str(e)}"
            self.logger.error(error_msg)
            raise ExtractionError(error_msg) from e

    def extract_text_chunked(
        self,
        pdf_path: Path,
        chunk_size: int = 100
    ) -> list[str]:
        """
        Extract text from PDF in chunks (useful for large files).

        Args:
            pdf_path: Path to PDF file
            chunk_size: Number of pages per chunk

        Returns:
            List of text chunks

        Raises:
            ExtractionError: If extraction fails
        """
        if not PYPDF2_AVAILABLE:
            raise ExtractionError(
                "PyPDF2 is not installed. Install with: pip install PyPDF2"
            )

        if not pdf_path.exists():
            raise ExtractionError(f"PDF file not found: {pdf_path}")

        try:
            self.logger.info(f"Extracting text in chunks from {pdf_path.name}")

            reader = PdfReader(str(pdf_path))
            num_pages = len(reader.pages)
            chunks = []

            for start_page in range(0, num_pages, chunk_size):
                end_page = min(start_page + chunk_size, num_pages)
                chunk_text = ""

                for page_num in range(start_page, end_page):
                    try:
                        page_text = reader.pages[page_num].extract_text()
                        if page_text:
                            chunk_text += page_text + "\n\n"
                    except Exception as e:
                        self.logger.warning(
                            f"Could not extract text from page {page_num + 1}: {e}"
                        )

                if chunk_text.strip():
                    chunks.append(chunk_text)
                    self.logger.debug(
                        f"Extracted chunk {len(chunks)} (pages {start_page + 1}-{end_page})"
                    )

            self.logger.info(f"Extracted {len(chunks)} chunks from {num_pages} pages")
            return chunks

        except Exception as e:
            error_msg = f"Error extracting chunked text from {pdf_path.name}: {str(e)}"
            self.logger.error(error_msg)
            raise ExtractionError(error_msg) from e

    def get_page_count(self, pdf_path: Path) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages

        Raises:
            ExtractionError: If reading fails
        """
        if not PYPDF2_AVAILABLE:
            raise ExtractionError(
                "PyPDF2 is not installed. Install with: pip install PyPDF2"
            )

        if not pdf_path.exists():
            raise ExtractionError(f"PDF file not found: {pdf_path}")

        try:
            reader = PdfReader(str(pdf_path))
            return len(reader.pages)
        except Exception as e:
            error_msg = f"Error reading {pdf_path.name}: {str(e)}"
            self.logger.error(error_msg)
            raise ExtractionError(error_msg) from e
