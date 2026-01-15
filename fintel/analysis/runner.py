#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unified Analysis Runner - reduces code duplication across analysis types.

This module provides a generic runner that can execute any analysis type
following the same pattern:
1. Validate inputs
2. Check for cancellation
3. Loop through years with progress tracking
4. Execute analysis
5. Collect results
"""

from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union, Protocol, TypeVar
from fintel.core import get_logger

logger = get_logger(__name__)


class Analyzer(Protocol):
    """Protocol for analyzers that can analyze a single filing."""

    def analyze_filing(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        custom_prompt: Optional[str] = None
    ) -> Any:
        """Analyze a single filing and return the result."""
        ...


T = TypeVar('T')


class AnalysisRunner:
    """
    Generic runner for executing analyses across multiple years.

    This class encapsulates the common pattern used across all analysis types:
    - Year-by-year iteration
    - Progress tracking
    - Cancellation checking
    - Error handling

    Example:
        >>> runner = AnalysisRunner(
        ...     ticker='AAPL',
        ...     pdf_paths={2023: Path('...'), 2022: Path('...')},
        ...     progress_callback=lambda msg, pct: print(msg),
        ...     cancellation_check=lambda: None,
        ... )
        >>> results = runner.run(analyzer.analyze_filing, 'Fundamental')
    """

    def __init__(
        self,
        ticker: str,
        pdf_paths: Dict[Union[int, str], Path],
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancellation_check: Optional[Callable[[], None]] = None,
        base_progress: int = 50,
        progress_range: int = 40,
    ):
        """
        Initialize the analysis runner.

        Args:
            ticker: Company ticker symbol
            pdf_paths: Dictionary mapping year to PDF file path
            progress_callback: Callback for progress updates (message, percent)
            cancellation_check: Callback that raises if cancelled
            base_progress: Starting progress percentage
            progress_range: Range of progress percentages to use
        """
        self.ticker = ticker
        self.pdf_paths = pdf_paths
        self.progress_callback = progress_callback
        self.cancellation_check = cancellation_check
        self.base_progress = base_progress
        self.progress_range = progress_range

    def run(
        self,
        analyze_func: Callable[[Path, str, int], T],
        analysis_name: str,
        custom_prompt: Optional[str] = None,
    ) -> Dict[Union[int, str], T]:
        """
        Run the analysis function across all years.

        Args:
            analyze_func: Function that takes (pdf_path, ticker, year) and returns result
            analysis_name: Name of the analysis for logging/progress
            custom_prompt: Optional custom prompt to pass to analyze_func

        Returns:
            Dictionary mapping year to analysis result
        """
        if not self.pdf_paths:
            logger.warning(f"No PDF files provided for {analysis_name} analysis of {self.ticker}")
            return {}

        results = {}
        total_years = len(self.pdf_paths)

        for idx, (year, pdf_path) in enumerate(self.pdf_paths.items(), 1):
            # Check for cancellation before processing each year
            if self.cancellation_check:
                self.cancellation_check()

            logger.info(f"Analyzing {self.ticker} {year} ({analysis_name})")

            # Update progress
            if self.progress_callback:
                progress_pct = self.base_progress + int((idx / total_years) * self.progress_range)
                self.progress_callback(
                    f"Analyzing {self.ticker} {year} ({analysis_name})",
                    progress_pct
                )

            try:
                # Call the analysis function
                if custom_prompt is not None:
                    result = analyze_func(pdf_path, self.ticker, year, custom_prompt)
                else:
                    result = analyze_func(pdf_path, self.ticker, year)

                if result:
                    results[year] = result
                    logger.info(f"Completed {analysis_name} for {self.ticker} {year}")

            except Exception as e:
                logger.error(f"Failed to analyze {self.ticker} {year} with {analysis_name}: {e}")
                # Continue with other years

        return results

    def run_with_analyzer(
        self,
        analyzer: Analyzer,
        analysis_name: str,
        custom_prompt: Optional[str] = None,
    ) -> Dict[Union[int, str], Any]:
        """
        Run analysis using an analyzer object.

        This is a convenience method for analyzers that implement the Analyzer protocol.

        Args:
            analyzer: Analyzer object with analyze_filing method
            analysis_name: Name of the analysis for logging/progress
            custom_prompt: Optional custom prompt

        Returns:
            Dictionary mapping year to analysis result
        """
        def analyze_func(pdf_path: Path, ticker: str, year: int, prompt: Optional[str] = None):
            return analyzer.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year,
                custom_prompt=prompt
            )

        return self.run(analyze_func, analysis_name, custom_prompt)


def create_progress_callback(
    db,
    run_id: str,
    total_steps: int,
) -> Callable[[str, int], None]:
    """
    Create a progress callback that updates the database.

    Args:
        db: Database repository instance
        run_id: Analysis run ID
        total_steps: Total number of steps (years)

    Returns:
        Callback function for progress updates
    """
    step_counter = [0]  # Mutable container for closure

    def callback(message: str, percent: int) -> None:
        step_counter[0] += 1
        db.update_run_progress(
            run_id,
            progress_message=message,
            progress_percent=percent,
            current_step=f"Step {step_counter[0]}",
            total_steps=total_steps
        )

    return callback


def create_cancellation_check(registry, run_id: str) -> Callable[[], None]:
    """
    Create a cancellation check callback.

    Args:
        registry: Cancellation registry
        run_id: Analysis run ID

    Returns:
        Callback that raises AnalysisCancelledException if cancelled
    """
    def check() -> None:
        token = registry.get_token(run_id)
        if token:
            token.raise_if_cancelled()

    return check
