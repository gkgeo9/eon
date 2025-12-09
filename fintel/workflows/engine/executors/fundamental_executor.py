#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FundamentalAnalysisExecutor - Runs fundamental analysis on each document.
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import uuid

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger


class FundamentalAnalysisExecutor(StepExecutor):
    """
    Run fundamental analysis on each document.

    Input: DataContainer (any shape)
    Output: DataContainer (same shape, with fundamental analyses)

    Config:
        - run_mode: "per_filing" | "aggregated"
        - custom_prompt: Optional[str]

    Behavior:
        - per_filing: Analyze each (ticker, year) independently
        - aggregated: Combine all years per ticker first, then analyze

    Integration:
        - Uses AnalysisService.run_analysis()
        - Checks cache via DatabaseRepository
        - Reuses existing analyses when possible
    """

    def __init__(self, db, analysis_service):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

        if not analysis_service:
            raise ValueError("FundamentalAnalysisExecutor requires AnalysisService")

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate that we have input data."""
        if input_data is None:
            raise ValueError("FundamentalAnalysisExecutor requires input data")
        if not input_data.tickers:
            raise ValueError("Input data has no tickers")
        if input_data.shape == (0, 0):
            raise ValueError("Input data has invalid shape")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Run fundamental analysis on all filings.

        Args:
            config: Configuration with run_mode and optional custom_prompt
            input_data: DataContainer with ticker/year structure

        Returns:
            DataContainer with fundamental analysis results
        """
        self.validate_input(input_data)

        run_mode = config.get('run_mode', 'per_filing')
        custom_prompt = config.get('custom_prompt')
        filing_type = input_data.metadata.get('filing_type', '10-K')

        self.logger.info(
            f"Running fundamental analysis: mode={run_mode}, "
            f"filings={input_data.total_items}"
        )

        results = {}
        run_ids = []

        if run_mode == 'per_filing':
            # Analyze each filing independently
            for ticker in input_data.tickers:
                results[ticker] = {}
                years = input_data.get_years_for_ticker(ticker)

                for year in years:
                    self.logger.info(f"Analyzing {ticker} {year} (fundamental)")

                    try:
                        # Check for existing analysis
                        existing = self._find_existing_analysis(
                            ticker, year, filing_type, custom_prompt
                        )

                        if existing:
                            self.logger.info(f"Using cached analysis: {ticker} {year}")
                            results[ticker][year] = existing
                        else:
                            # Run new analysis
                            run_id = self.analysis_service.run_analysis(
                                ticker=ticker,
                                analysis_type='fundamental',
                                filing_type=filing_type,
                                years=[year],
                                custom_prompt=custom_prompt
                            )
                            run_ids.append(run_id)

                            # Get result
                            analysis_results = self.db.get_analysis_results(run_id)
                            if analysis_results:
                                results[ticker][year] = analysis_results[0]['data']
                            else:
                                results[ticker][year] = None
                                self.logger.warning(f"No result for {ticker} {year}")

                    except Exception as e:
                        self.logger.error(f"Failed to analyze {ticker} {year}: {e}")
                        results[ticker][year] = None

        else:  # aggregated mode
            # For aggregated mode, run multi-year analysis per ticker
            for ticker in input_data.tickers:
                years = input_data.get_years_for_ticker(ticker)

                self.logger.info(f"Analyzing {ticker} (aggregated, {len(years)} years)")

                try:
                    # Run analysis for all years together
                    run_id = self.analysis_service.run_analysis(
                        ticker=ticker,
                        analysis_type='fundamental',
                        filing_type=filing_type,
                        years=years,
                        custom_prompt=custom_prompt
                    )
                    run_ids.append(run_id)

                    # Get results and organize by year
                    analysis_results = self.db.get_analysis_results(run_id)
                    results[ticker] = {
                        res['year']: res['data']
                        for res in analysis_results
                    }

                except Exception as e:
                    self.logger.error(f"Failed to analyze {ticker}: {e}")
                    results[ticker] = {year: None for year in years}

        # Create output container
        output = DataContainer(
            data=results,
            num_companies=input_data.num_companies,
            num_years_per_company=input_data.num_years_per_company,
            step_id=config.get('step_id', 'fundamental_1'),
            step_type='fundamental_analysis',
            source_run_ids=run_ids,
            metadata={
                'run_mode': run_mode,
                'filing_type': filing_type,
                'custom_prompt': custom_prompt,
                'input_step': input_data.step_id
            }
        )

        self.logger.info(
            f"Fundamental analysis complete: {output.total_items} results"
        )

        return output

    def _find_existing_analysis(
        self,
        ticker: str,
        year: int,
        filing_type: str,
        custom_prompt: Optional[str]
    ) -> Optional[Dict]:
        """
        Search for existing analysis that matches requirements.

        Args:
            ticker: Company ticker
            year: Fiscal year
            filing_type: Filing type
            custom_prompt: Custom prompt (None for default)

        Returns:
            Analysis result dict if found, None otherwise
        """
        try:
            # Search for completed fundamental analyses
            analyses = self.db.search_analyses(
                ticker=ticker,
                analysis_type='fundamental',
                status='completed'
            )

            if analyses.empty:
                return None

            # Check each analysis
            for _, row in analyses.iterrows():
                run_id = row['run_id']

                # Get results for this run
                results = self.db.get_analysis_results(run_id)

                for result in results:
                    if result['year'] == year:
                        # Found a match
                        return result['data']

            return None

        except Exception as e:
            self.logger.error(f"Error searching for existing analysis: {e}")
            return None

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output shape is same as input shape."""
        return input_shape if input_shape else (0, 0)
