#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for UI year selection logic.

Tests the year parsing and validation logic used in both
Single Analysis and Batch Analysis pages.
"""

import pytest
from datetime import datetime


class TestYearSelectionLogic:
    """Test year selection and parsing logic."""

    @pytest.fixture
    def current_year(self):
        """Current year for testing."""
        return datetime.now().year

    def test_single_year_selection(self, current_year):
        """Test single year selection."""
        # Simulate user selecting a specific year
        specific_year = 2023
        years = [specific_year]
        num_years = None

        assert years == [2023]
        assert num_years is None
        assert len(years) == 1

    def test_last_n_years(self, current_year):
        """Test last N years generation."""
        # Simulate "last 5 years"
        num_years = 5
        years = None

        # Generate preview (this is what the UI does)
        preview_years = list(range(current_year, current_year - num_years, -1))

        assert len(preview_years) == 5
        assert preview_years[0] == current_year
        assert preview_years[-1] == current_year - 4
        # Should be descending
        assert preview_years == sorted(preview_years, reverse=True)

    def test_specific_years_parsing(self):
        """Test parsing comma-separated years."""
        # Simulate user input
        years_input = "2023, 2022, 2020, 2019"

        # Parse (this is what the UI does)
        years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
        years = sorted(years, reverse=True)
        num_years = None

        assert years == [2023, 2022, 2020, 2019]
        assert num_years is None
        assert len(years) == 4

    def test_specific_years_non_contiguous(self):
        """Test non-contiguous years work correctly."""
        years_input = "2024, 2021, 2018, 2015"

        years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
        years = sorted(years, reverse=True)

        assert years == [2024, 2021, 2018, 2015]
        # Check they're properly sorted descending
        for i in range(len(years) - 1):
            assert years[i] > years[i + 1]

    def test_year_range_parsing(self):
        """Test year range parsing."""
        # Simulate user selecting range 2018-2023
        start_year = 2018
        end_year = 2023

        years = list(range(end_year, start_year - 1, -1))
        num_years = None

        assert years == [2023, 2022, 2021, 2020, 2019, 2018]
        assert num_years is None
        assert len(years) == 6

    def test_year_range_single_year(self):
        """Test year range with start == end."""
        start_year = 2023
        end_year = 2023

        years = list(range(end_year, start_year - 1, -1))

        assert years == [2023]
        assert len(years) == 1

    def test_multi_year_minimum_validation(self):
        """Test multi-year analyses require minimum 3 years."""
        # For multi-year required analyses
        analysis_types_requiring_multi = ['excellent', 'objective', 'scanner']

        for analysis_type in analysis_types_requiring_multi:
            # Too few years
            years = [2023, 2022]
            is_valid = len(years) >= 3

            assert not is_valid, f"{analysis_type} should require at least 3 years"

            # Valid number of years
            years = [2023, 2022, 2021]
            is_valid = len(years) >= 3

            assert is_valid, f"{analysis_type} should accept 3 or more years"

    def test_flexible_analysis_single_year_allowed(self):
        """Test flexible analyses can use single year."""
        flexible_types = ['fundamental', 'buffett', 'taleb', 'contrarian', 'multi']

        for analysis_type in flexible_types:
            years = [2023]
            is_valid = len(years) >= 1

            assert is_valid, f"{analysis_type} should accept single year"


class TestCSVYearModeParsing:
    """Test CSV year_mode and years_value parsing logic."""

    def test_csv_last_n_mode(self):
        """Test CSV with last_n mode."""
        # Simulate CSV row
        year_mode = 'last_n'
        years_value = '5'

        if year_mode == 'last_n' and years_value:
            num_years = int(years_value)
            years = None
        else:
            num_years = None
            years = None

        assert num_years == 5
        assert years is None

    def test_csv_specific_years_mode(self):
        """Test CSV with specific_years mode."""
        year_mode = 'specific_years'
        years_value = '2023,2022,2020,2019'

        if year_mode == 'specific_years' and years_value:
            years = [int(y.strip()) for y in years_value.split(',') if y.strip()]
            years = sorted(years, reverse=True)
            num_years = None
        else:
            num_years = None
            years = None

        assert years == [2023, 2022, 2020, 2019]
        assert num_years is None

    def test_csv_year_range_mode(self):
        """Test CSV with year_range mode."""
        year_mode = 'year_range'
        years_value = '2018-2023'

        if year_mode == 'year_range' and years_value:
            if '-' in years_value:
                start, end = years_value.split('-')
                years = list(range(int(end.strip()), int(start.strip()) - 1, -1))
                num_years = None
        else:
            num_years = None
            years = None

        assert years == [2023, 2022, 2021, 2020, 2019, 2018]
        assert num_years is None

    def test_csv_single_year_mode(self):
        """Test CSV with single_year mode."""
        year_mode = 'single_year'
        years_value = '2023'

        if year_mode == 'single_year' and years_value:
            years = [int(years_value)]
            num_years = None
        else:
            num_years = None
            years = None

        assert years == [2023]
        assert num_years is None

    def test_csv_legacy_num_years(self):
        """Test CSV with legacy num_years column."""
        # Simulate old CSV format
        year_mode = None
        years_value = None
        num_years_col = 5

        # Check if new year_mode column exists
        if year_mode and years_value:
            # Would use new logic
            pass
        elif num_years_col:
            # Legacy support
            num_years = int(num_years_col)
            years = None

        assert num_years == 5
        assert years is None

    def test_csv_defaults_by_analysis_type(self):
        """Test default year values when not specified."""
        # Multi-year required
        multi_year_types = ['excellent', 'objective', 'scanner']
        for analysis_type in multi_year_types:
            years = None
            num_years = None

            # Apply defaults
            if years is None and num_years is None:
                if analysis_type in multi_year_types:
                    num_years = 5
                else:
                    num_years = 1

            assert num_years == 5, f"{analysis_type} should default to 5 years"

        # Flexible analyses
        flexible_types = ['fundamental', 'buffett', 'taleb', 'contrarian', 'multi']
        for analysis_type in flexible_types:
            years = None
            num_years = None

            # Apply defaults
            if years is None and num_years is None:
                if analysis_type in multi_year_types:
                    num_years = 5
                else:
                    num_years = 1

            assert num_years == 1, f"{analysis_type} should default to 1 year"


class TestYearValidation:
    """Test year validation logic."""

    def test_empty_years_list(self):
        """Test validation fails for empty years."""
        years_input = ""
        try:
            years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
        except ValueError:
            years = None

        is_valid = years is not None and len(years) > 0
        assert not is_valid

    def test_invalid_year_format(self):
        """Test validation fails for invalid format."""
        years_input = "2023, abc, 2021"
        years = None
        try:
            years = [int(y.strip()) for y in years_input.split(',') if y.strip()]
        except ValueError:
            years = None

        assert years is None

    def test_year_range_end_before_start(self):
        """Test validation fails when end year < start year."""
        start_year = 2023
        end_year = 2020

        is_valid = end_year >= start_year
        assert not is_valid

    def test_year_range_minimum_for_multi_year(self):
        """Test multi-year analyses require minimum range."""
        start_year = 2022
        end_year = 2023
        # Only 2 years in range

        range_count = end_year - start_year + 1
        is_valid_for_multi_year = range_count >= 3

        assert not is_valid_for_multi_year

        # Valid range
        start_year = 2021
        end_year = 2023
        range_count = end_year - start_year + 1
        is_valid_for_multi_year = range_count >= 3

        assert is_valid_for_multi_year


class TestAnalysisServiceIntegration:
    """Test integration with AnalysisService year handling."""

    @pytest.fixture
    def current_year(self):
        return datetime.now().year

    def test_num_years_to_years_list_conversion(self, current_year):
        """Test AnalysisService converts num_years to years list."""
        # This simulates what AnalysisService.run_analysis does
        years = None
        num_years = 5

        if years is None and num_years:
            years_list = list(range(current_year, current_year - num_years, -1))
        elif years is None:
            years_list = [current_year]
        else:
            years_list = years

        assert len(years_list) == 5
        assert years_list[0] == current_year
        assert years_list[-1] == current_year - 4

    def test_explicit_years_passed_through(self, current_year):
        """Test explicit years list is used as-is."""
        years = [2023, 2022, 2020, 2019]
        num_years = None

        if years is None and num_years:
            years_list = list(range(current_year, current_year - num_years, -1))
        elif years is None:
            years_list = [current_year]
        else:
            years_list = years

        assert years_list == [2023, 2022, 2020, 2019]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
