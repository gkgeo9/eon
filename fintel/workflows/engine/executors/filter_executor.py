#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FilterExecutor - Filter results based on criteria.
"""

from typing import Dict, Any, Optional, Tuple
import operator

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger


class FilterExecutor(StepExecutor):
    """
    Filter results based on criteria.

    Input: DataContainer
    Output: DataContainer (subset of input)

    Config:
        - field: str (JSON path to field, e.g., "moat_rating" or "metrics.revenue_growth")
        - operator: ">" | ">=" | "<" | "<=" | "==" | "!=" | "contains"
        - value: Any (value to compare against)

    Examples:
        - Filter for moat_rating > 80
        - Filter for revenue_growth >= 15
        - Filter for description contains "software"
    """

    OPERATORS = {
        '>': operator.gt,
        '>=': operator.ge,
        '<': operator.lt,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne,
    }

    def __init__(self, db, analysis_service=None):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data."""
        if input_data is None:
            raise ValueError("FilterExecutor requires input data")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Filter results based on criteria.

        Args:
            config: Configuration with field, operator, and value
            input_data: DataContainer to filter

        Returns:
            Filtered DataContainer
        """
        self.validate_input(input_data)

        field = config.get('field', '')
        op_str = config.get('operator', '==')
        value = config.get('value')

        if not field:
            raise ValueError("Filter field not specified")

        self.logger.info(
            f"Filtering: {field} {op_str} {value} "
            f"(input: {input_data.total_items} items)"
        )

        # Apply filter
        filtered_data = {}
        filtered_count = 0
        total_count = 0

        for ticker in input_data.tickers:
            filtered_data[ticker] = {}

            for year in input_data.get_years_for_ticker(ticker):
                data = input_data.data[ticker][year]
                total_count += 1

                if data is None:
                    continue

                # Extract field value
                field_value = self._extract_field(data, field)

                if field_value is None:
                    self.logger.debug(f"Field {field} not found in {ticker} {year}")
                    continue

                # Apply operator
                if self._matches(field_value, op_str, value):
                    filtered_data[ticker][year] = data
                    filtered_count += 1

        # Remove empty tickers
        filtered_data = {
            ticker: years
            for ticker, years in filtered_data.items()
            if years
        }

        # Calculate new shape
        num_years_per_company = {
            ticker: len(years)
            for ticker, years in filtered_data.items()
        }

        # Create output container
        output = DataContainer(
            data=filtered_data,
            num_companies=len(filtered_data),
            num_years_per_company=num_years_per_company,
            step_id=config.get('step_id', 'filter_1'),
            step_type='filter',
            source_run_ids=input_data.source_run_ids,
            metadata={
                'filter_field': field,
                'filter_operator': op_str,
                'filter_value': value,
                'input_items': total_count,
                'filtered_items': filtered_count,
                'pass_rate': filtered_count / total_count if total_count > 0 else 0,
                'input_step': input_data.step_id
            }
        )

        # Warn if filter eliminated everything
        if output.total_items == 0:
            output.add_warning(
                f"Filter eliminated all data: {field} {op_str} {value}",
                {'input_items': total_count}
            )

        self.logger.info(
            f"Filter complete: {filtered_count}/{total_count} items passed "
            f"({output.total_items} non-null)"
        )

        return output

    def _extract_field(self, data: Any, field: str) -> Optional[Any]:
        """
        Extract field value from data using dot notation.

        Examples:
            - "moat_rating" extracts data['moat_rating']
            - "metrics.revenue_growth" extracts data['metrics']['revenue_growth']

        Args:
            data: Data object (dict or Pydantic model)
            field: Field path (dot-separated)

        Returns:
            Field value or None if not found
        """
        parts = field.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

            if current is None:
                return None

        return current

    def _matches(self, field_value: Any, op_str: str, target_value: Any) -> bool:
        """
        Check if field value matches criteria.

        Args:
            field_value: Value from data
            op_str: Operator string
            target_value: Value to compare against

        Returns:
            True if match
        """
        try:
            if op_str == 'contains':
                # String containment
                return str(target_value).lower() in str(field_value).lower()

            # Numeric comparison
            op_func = self.OPERATORS.get(op_str)
            if not op_func:
                self.logger.warning(f"Unknown operator: {op_str}")
                return False

            # Try numeric comparison
            try:
                field_num = float(field_value)
                target_num = float(target_value)
                return op_func(field_num, target_num)
            except (ValueError, TypeError):
                # Fall back to string comparison
                return op_func(str(field_value), str(target_value))

        except Exception as e:
            self.logger.error(f"Error comparing {field_value} {op_str} {target_value}: {e}")
            return False

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output shape is subset of input shape (can't predict exactly)."""
        return input_shape if input_shape else (0, 0)
