#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
InputStepExecutor - Handles company & year input definition.
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger


class InputStepExecutor(StepExecutor):
    """
    Handles company & year input definition.

    Input: None (first step in workflow)
    Output: DataContainer with placeholder structure
    Shape: (num_tickers, num_years)

    Config:
        - tickers: List[str] - Company ticker symbols
        - years: List[int] OR num_years: int - Years to analyze
        - filing_type: str - Type of SEC filing (10-K, 10-Q, etc.)
    """

    def __init__(self, db, analysis_service=None):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Input step should have no input data (it's the first step)."""
        if input_data is not None:
            raise ValueError("InputStepExecutor expects no input data (it should be the first step)")
        return True

    def execute(self, config: Dict[str, Any], input_data: Optional[DataContainer]) -> DataContainer:
        """
        Create input data structure.

        Args:
            config: Configuration with tickers, years, filing_type
            input_data: None (first step)

        Returns:
            DataContainer with placeholder structure
        """
        self.validate_input(input_data)

        # Parse configuration
        tickers = config.get('tickers', [])
        filing_type = config.get('filing_type', '10-K')

        # Determine years
        if 'years' in config:
            years = config['years']
        elif 'num_years' in config:
            num_years = config['num_years']
            current_year = datetime.now().year
            years = list(range(current_year, current_year - num_years, -1))
        else:
            years = [datetime.now().year]

        if not tickers:
            raise ValueError("No tickers provided in configuration")

        self.logger.info(
            f"Input step: {len(tickers)} tickers × {len(years)} years = "
            f"{len(tickers) * len(years)} total filings"
        )

        # Build placeholder structure
        data = {}
        missing_filings = []

        for ticker in tickers:
            ticker = ticker.upper().strip()
            data[ticker] = {}

            for year in years:
                # Check if filing exists in cache
                cached_file = self.db.get_cached_file(ticker, year, filing_type)

                if cached_file:
                    # File exists, create placeholder
                    data[ticker][year] = None  # Placeholder for future analysis
                    self.logger.debug(f"Found cached file: {ticker} {year}")
                else:
                    # File doesn't exist, but still create placeholder
                    # The analysis step will handle downloading
                    data[ticker][year] = None
                    self.logger.debug(f"No cache for: {ticker} {year} - will download")

        # Create DataContainer
        num_years_per_company = {ticker: len(years) for ticker in data.keys()}

        container = DataContainer(
            data=data,
            num_companies=len(tickers),
            num_years_per_company=num_years_per_company,
            step_id=config.get('step_id', 'input_1'),
            step_type='input',
            metadata={
                'filing_type': filing_type,
                'tickers': tickers,
                'years': years,
                'missing_filings': missing_filings
            }
        )

        self.logger.info(
            f"Created input structure: shape={container.shape}, "
            f"placeholders={container.total_items}"
        )

        return container

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Output shape is determined by config, not input.

        For input step, we need the config to determine shape.
        This is a special case.
        """
        # This will be called with config during validation
        return (0, 0)  # Placeholder; actual shape depends on config
