#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SuccessFactorsExecutor - Extract success factors using specialized analyzers.
"""

from typing import Dict, Any, Optional, Tuple

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger
from fintel.analysis.fundamental.success_factors import (
    ExcellentCompanyAnalyzer,
    ObjectiveCompanyAnalyzer
)
from fintel.ai import APIKeyManager, RateLimiter


class SuccessFactorsExecutor(StepExecutor):
    """
    Extract success factors using ExcellentCompanyAnalyzer or ObjectiveCompanyAnalyzer.

    Input: DataContainer with fundamental analyses
    Output: DataContainer (potentially aggregated)

    Config:
        - analyzer_type: "objective" | "excellent"
        - aggregate_by: "company" | "year" | "none"

    Behavior:
        - aggregate_by="company": Combines all years per company → (num_companies, 1)
        - aggregate_by="year": Combines all companies per year → (1, num_years)
        - aggregate_by="none": Runs on each (ticker, year) → same shape
    """

    def __init__(self, db, analysis_service):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

        if not analysis_service:
            raise ValueError("SuccessFactorsExecutor requires AnalysisService")

        # Get API key manager and rate limiter from analysis service
        self.api_key_manager = analysis_service.api_key_manager
        self.rate_limiter = analysis_service.rate_limiter

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate that we have fundamental analysis data."""
        if input_data is None:
            raise ValueError("SuccessFactorsExecutor requires input data")
        if input_data.step_type != 'fundamental_analysis':
            raise ValueError(
                f"SuccessFactorsExecutor expects fundamental analysis input, "
                f"got {input_data.step_type}"
            )
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Extract success factors.

        Args:
            config: Configuration with analyzer_type and aggregate_by
            input_data: DataContainer with fundamental analyses

        Returns:
            DataContainer with success factor analyses
        """
        self.validate_input(input_data)

        analyzer_type = config.get('analyzer_type', 'objective')
        aggregate_by = config.get('aggregate_by', 'company')

        self.logger.info(
            f"Running success factors: type={analyzer_type}, "
            f"aggregate={aggregate_by}"
        )

        # Create appropriate analyzer
        if analyzer_type == 'excellent':
            analyzer = ExcellentCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter
            )
        else:
            analyzer = ObjectiveCompanyAnalyzer(
                api_key_manager=self.api_key_manager,
                rate_limiter=self.rate_limiter
            )

        results = {}

        if aggregate_by == 'company':
            # Analyze each company across all years
            for ticker in input_data.tickers:
                self.logger.info(f"Analyzing success factors for {ticker}")

                # Get all years' analyses for this ticker
                analyses = {}
                for year in input_data.get_years_for_ticker(ticker):
                    year_data = input_data.data[ticker][year]
                    if year_data:
                        analyses[year] = year_data

                if analyses:
                    try:
                        # Run success factors analysis
                        result = analyzer.analyze_success_factors(
                            ticker=ticker,
                            analyses=analyses
                        )

                        # Store under special key (0 = aggregated)
                        results[ticker] = {0: result}

                    except Exception as e:
                        self.logger.error(
                            f"Failed to analyze success factors for {ticker}: {e}"
                        )
                        results[ticker] = {0: None}
                else:
                    self.logger.warning(f"No analyses found for {ticker}")
                    results[ticker] = {0: None}

            # Update shape: (num_companies, 1)
            num_years_per_company = {ticker: 1 for ticker in results.keys()}

        elif aggregate_by == 'year':
            # Analyze each year across all companies
            all_years = input_data.get_all_years()

            for year in all_years:
                self.logger.info(f"Analyzing success factors for year {year}")

                # Get all companies' analyses for this year
                analyses = {}
                for ticker in input_data.tickers:
                    if year in input_data.data[ticker]:
                        year_data = input_data.data[ticker][year]
                        if year_data:
                            analyses[ticker] = year_data

                if analyses:
                    try:
                        # For year aggregation, combine into one analysis
                        # Use first ticker as representative
                        first_ticker = list(analyses.keys())[0]
                        result = analyzer.analyze_success_factors(
                            ticker=f"Year_{year}",
                            analyses={0: analyses[first_ticker]}  # Simplified
                        )

                        # Store under special ticker
                        if 'ALL_COMPANIES' not in results:
                            results['ALL_COMPANIES'] = {}
                        results['ALL_COMPANIES'][year] = result

                    except Exception as e:
                        self.logger.error(
                            f"Failed to analyze success factors for year {year}: {e}"
                        )
                        if 'ALL_COMPANIES' not in results:
                            results['ALL_COMPANIES'] = {}
                        results['ALL_COMPANIES'][year] = None

            # Update shape: (1, num_years)
            num_years_per_company = {'ALL_COMPANIES': len(all_years)}

        else:  # none - run on each (ticker, year)
            # Not typically useful for success factors, but supported
            self.logger.warning(
                "Running success factors without aggregation may not be meaningful"
            )

            for ticker in input_data.tickers:
                results[ticker] = {}
                for year in input_data.get_years_for_ticker(ticker):
                    year_data = input_data.data[ticker][year]

                    if year_data:
                        try:
                            result = analyzer.analyze_success_factors(
                                ticker=ticker,
                                analyses={year: year_data}
                            )
                            results[ticker][year] = result
                        except Exception as e:
                            self.logger.error(
                                f"Failed for {ticker} {year}: {e}"
                            )
                            results[ticker][year] = None

            num_years_per_company = input_data.num_years_per_company

        # Create output container
        output = DataContainer(
            data=results,
            num_companies=len(results),
            num_years_per_company=num_years_per_company,
            step_id=config.get('step_id', 'success_1'),
            step_type='success_factors',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'analyzer_type': analyzer_type,
                'aggregate_by': aggregate_by,
                'input_step': input_data.step_id
            }
        )

        self.logger.info(
            f"Success factors complete: shape={output.shape}, "
            f"items={output.total_items}"
        )

        return output

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Output shape depends on aggregation mode.

        This would need config to determine, so we return input shape as default.
        """
        return input_shape if input_shape else (0, 0)
