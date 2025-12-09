#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AggregateExecutor - Aggregate/combine results.
"""

from typing import Dict, Any, Optional, Tuple, List

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger


class AggregateExecutor(StepExecutor):
    """
    Aggregate/combine results.

    Input: DataContainer
    Output: DataContainer (different shape)

    Config:
        - operation: "merge_all" | "group_by_company" | "group_by_year" | "top_n" | "average_metrics"
        - n: int (for top_n)
        - score_field: str (for top_n)

    Shape transformations:
        - merge_all: (N, M) → (1, 1)
        - group_by_company: (N, M) → (N, 1)
        - group_by_year: (N, M) → (1, M)
        - top_n: (N, M) → (n, M) or (N, m)
    """

    def __init__(self, db, analysis_service=None):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data."""
        if input_data is None:
            raise ValueError("AggregateExecutor requires input data")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Aggregate results.

        Args:
            config: Configuration with operation type
            input_data: DataContainer to aggregate

        Returns:
            Aggregated DataContainer
        """
        self.validate_input(input_data)

        operation = config.get('operation', 'merge_all')

        self.logger.info(
            f"Aggregating: operation={operation}, "
            f"input_shape={input_data.shape}"
        )

        # Route to appropriate aggregation method
        if operation == 'merge_all':
            result = self._merge_all(input_data, config)
        elif operation == 'group_by_company':
            result = self._group_by_company(input_data, config)
        elif operation == 'group_by_year':
            result = self._group_by_year(input_data, config)
        elif operation == 'top_n':
            result = self._top_n(input_data, config)
        elif operation == 'average_metrics':
            result = self._average_metrics(input_data, config)
        else:
            raise ValueError(f"Unknown aggregation operation: {operation}")

        self.logger.info(f"Aggregation complete: output_shape={result.shape}")

        return result

    def _merge_all(self, input_data: DataContainer, config: Dict) -> DataContainer:
        """Merge all data into single result (N, M) → (1, 1)."""
        # Collect all data items
        all_data = []
        for ticker in input_data.tickers:
            for year in input_data.get_years_for_ticker(ticker):
                data = input_data.data[ticker][year]
                if data:
                    all_data.append({
                        'ticker': ticker,
                        'year': year,
                        'data': data
                    })

        # Create merged result
        merged = {
            'items': all_data,
            'summary': {
                'total_companies': input_data.num_companies,
                'total_items': len(all_data),
                'tickers': input_data.tickers
            }
        }

        output = DataContainer(
            data={'ALL': {0: merged}},
            num_companies=1,
            num_years_per_company={'ALL': 1},
            step_id=config.get('step_id', 'aggregate_1'),
            step_type='aggregate',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'operation': 'merge_all',
                'input_shape': input_data.shape,
                'input_step': input_data.step_id
            }
        )

        return output

    def _group_by_company(self, input_data: DataContainer, config: Dict) -> DataContainer:
        """Group by company (N, M) → (N, 1)."""
        results = {}

        for ticker in input_data.tickers:
            years_data = []

            for year in input_data.get_years_for_ticker(ticker):
                data = input_data.data[ticker][year]
                if data:
                    years_data.append({
                        'year': year,
                        'data': data
                    })

            # Store grouped data
            results[ticker] = {
                0: {  # Special key for aggregated
                    'years': years_data,
                    'summary': {
                        'ticker': ticker,
                        'years_count': len(years_data),
                        'years_list': [item['year'] for item in years_data]
                    }
                }
            }

        output = DataContainer(
            data=results,
            num_companies=len(results),
            num_years_per_company={ticker: 1 for ticker in results},
            step_id=config.get('step_id', 'aggregate_1'),
            step_type='aggregate',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'operation': 'group_by_company',
                'input_shape': input_data.shape,
                'input_step': input_data.step_id
            }
        )

        return output

    def _group_by_year(self, input_data: DataContainer, config: Dict) -> DataContainer:
        """Group by year (N, M) → (1, M)."""
        all_years = input_data.get_all_years()
        results = {'ALL_COMPANIES': {}}

        for year in all_years:
            companies_data = []

            for ticker in input_data.tickers:
                if year in input_data.data[ticker]:
                    data = input_data.data[ticker][year]
                    if data:
                        companies_data.append({
                            'ticker': ticker,
                            'data': data
                        })

            results['ALL_COMPANIES'][year] = {
                'companies': companies_data,
                'summary': {
                    'year': year,
                    'companies_count': len(companies_data),
                    'tickers': [item['ticker'] for item in companies_data]
                }
            }

        output = DataContainer(
            data=results,
            num_companies=1,
            num_years_per_company={'ALL_COMPANIES': len(all_years)},
            step_id=config.get('step_id', 'aggregate_1'),
            step_type='aggregate',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'operation': 'group_by_year',
                'input_shape': input_data.shape,
                'input_step': input_data.step_id
            }
        )

        return output

    def _top_n(self, input_data: DataContainer, config: Dict) -> DataContainer:
        """Take top N by score field."""
        n = config.get('n', 10)
        score_field = config.get('score_field', 'total_score')

        self.logger.info(f"Taking top {n} by {score_field}")

        # Collect all items with scores
        scored_items = []

        for ticker in input_data.tickers:
            for year in input_data.get_years_for_ticker(ticker):
                data = input_data.data[ticker][year]

                if data:
                    score = self._extract_score(data, score_field)
                    if score is not None:
                        scored_items.append({
                            'ticker': ticker,
                            'year': year,
                            'data': data,
                            'score': score
                        })

        # Sort by score (descending)
        scored_items.sort(key=lambda x: x['score'], reverse=True)

        # Take top N
        top_items = scored_items[:n]

        # Organize by ticker
        results = {}
        for item in top_items:
            ticker = item['ticker']
            year = item['year']

            if ticker not in results:
                results[ticker] = {}

            results[ticker][year] = item['data']

        # Calculate shape
        num_years_per_company = {
            ticker: len(years)
            for ticker, years in results.items()
        }

        output = DataContainer(
            data=results,
            num_companies=len(results),
            num_years_per_company=num_years_per_company,
            step_id=config.get('step_id', 'aggregate_1'),
            step_type='aggregate',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'operation': 'top_n',
                'n': n,
                'score_field': score_field,
                'input_shape': input_data.shape,
                'input_items': len(scored_items),
                'input_step': input_data.step_id
            }
        )

        return output

    def _average_metrics(self, input_data: DataContainer, config: Dict) -> DataContainer:
        """Calculate average of numeric metrics."""
        # This is a simplified implementation
        # In a real system, you'd need to specify which metrics to average

        self.logger.warning(
            "average_metrics is a simplified implementation - "
            "please specify metrics in config"
        )

        # For now, just count items
        summary = {
            'total_items': input_data.total_items,
            'num_companies': input_data.num_companies,
            'shape': input_data.shape
        }

        output = DataContainer(
            data={'SUMMARY': {0: summary}},
            num_companies=1,
            num_years_per_company={'SUMMARY': 1},
            step_id=config.get('step_id', 'aggregate_1'),
            step_type='aggregate',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'operation': 'average_metrics',
                'input_shape': input_data.shape,
                'input_step': input_data.step_id
            }
        )

        return output

    def _extract_score(self, data: Any, field: str) -> Optional[float]:
        """Extract numeric score from data."""
        try:
            parts = field.split('.')
            current = data

            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return None

            return float(current) if current is not None else None

        except (ValueError, TypeError):
            return None

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output shape depends on operation."""
        # This would need config to determine
        return (1, 1)  # Default for most aggregations
