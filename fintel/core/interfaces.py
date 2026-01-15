#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Protocol definitions for dependency injection.

These protocols define the interfaces that components must implement,
enabling loose coupling and easier testing through dependency injection.
"""

from typing import Protocol, Optional, List, Dict, Any, Tuple
from pathlib import Path


class IKeyManager(Protocol):
    """Protocol for API key management."""

    @property
    def api_keys(self) -> List[str]:
        """List of managed API keys."""
        ...

    def reserve_key(self) -> Optional[str]:
        """
        Atomically reserve and return the best available API key.

        Returns:
            Reserved API key, or None if no keys available
        """
        ...

    def release_key(self, api_key: str) -> None:
        """
        Release a previously reserved API key.

        Args:
            api_key: The API key to release
        """
        ...

    def record_usage(self, api_key: str, error: bool = False) -> None:
        """
        Record API usage for a key.

        Args:
            api_key: The API key that was used
            error: Whether the request resulted in an error
        """
        ...

    def get_least_used_key(self) -> Optional[str]:
        """
        Get the API key with the least usage today.

        Returns:
            API key string with lowest usage, or None if all exhausted
        """
        ...

    def can_make_request(self, api_key: str) -> bool:
        """Check if a key can make another request today."""
        ...


class IRateLimiter(Protocol):
    """Protocol for rate limiting."""

    def record_and_sleep(self, api_key: str, error: bool = False) -> None:
        """
        Record API usage and sleep for the configured duration.

        Args:
            api_key: The API key that was just used
            error: Whether the request resulted in an error
        """
        ...

    def can_make_request(self, api_key: str) -> bool:
        """
        Check if a key can make another request today.

        Args:
            api_key: The API key to check

        Returns:
            True if under daily limit, False otherwise
        """
        ...

    def get_usage_today(self, api_key: str) -> int:
        """
        Get usage count for a key today.

        Args:
            api_key: The API key to check

        Returns:
            Number of requests made today
        """
        ...


class IDownloader(Protocol):
    """Protocol for SEC filing downloads."""

    def download_with_metadata(
        self,
        ticker: str,
        num_filings: int,
        filing_type: str
    ) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
        """
        Download filings with metadata.

        Args:
            ticker: Company ticker symbol
            num_filings: Number of filings to download
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            Tuple of (filing_directory, filing_metadata_list)
        """
        ...

    def download_with_metadata_by_cik(
        self,
        cik: str,
        num_filings: int,
        filing_type: str
    ) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
        """
        Download filings by CIK with metadata.

        Args:
            cik: Company CIK number
            num_filings: Number of filings to download
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            Tuple of (filing_directory, filing_metadata_list)
        """
        ...

    def get_company_info_from_cik(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company information from CIK.

        Args:
            cik: Company CIK number

        Returns:
            Dictionary with company information, or None if not found
        """
        ...


class IExtractor(Protocol):
    """Protocol for PDF text extraction."""

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        ...


class IConfig(Protocol):
    """Protocol for configuration access."""

    @property
    def google_api_keys(self) -> List[str]:
        """List of Google API keys."""
        ...

    @property
    def default_model(self) -> str:
        """Default LLM model name."""
        ...

    @property
    def thinking_budget(self) -> int:
        """Token budget for LLM thinking."""
        ...

    def get_data_path(self, subdir: str) -> Path:
        """
        Get path to a data subdirectory.

        Args:
            subdir: Subdirectory name

        Returns:
            Path to the subdirectory
        """
        ...


class IRepository(Protocol):
    """Protocol for database repository operations."""

    def create_analysis_run(
        self,
        run_id: str,
        ticker: str,
        analysis_type: str,
        filing_type: str,
        years: List[int],
        config: Dict[str, Any],
        company_name: Optional[str] = None
    ) -> None:
        """Create a new analysis run record."""
        ...

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update the status of an analysis run."""
        ...

    def update_run_progress(
        self,
        run_id: str,
        progress_message: Optional[str] = None,
        progress_percent: Optional[int] = None,
        current_step: Optional[str] = None,
        total_steps: Optional[int] = None
    ) -> None:
        """Update progress information for an analysis run."""
        ...

    def get_run_status(self, run_id: str) -> Optional[str]:
        """Get the current status of an analysis run."""
        ...

    def store_result(
        self,
        run_id: str,
        ticker: str,
        fiscal_year: int,
        filing_type: str,
        result_type: str,
        result_data: Dict[str, Any]
    ) -> None:
        """Store analysis result."""
        ...

    def get_cached_file(
        self,
        ticker: str,
        year: int,
        filing_type: str
    ) -> Optional[str]:
        """Get cached file path if exists."""
        ...

    def cache_file(
        self,
        ticker: str,
        year: int,
        filing_type: str,
        file_path: str,
        filing_date: Optional[str] = None
    ) -> None:
        """Cache a file path."""
        ...
