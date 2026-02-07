#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Results display component.

Routes to the legacy display implementation.
Future work: Implement modular formatters.
"""

__all__ = ['display_results']


def display_results(run_details: dict, results: list):
    """
    Display analysis results with enhanced UX.

    This is a backward-compatible wrapper that routes to the new modular formatters.

    Args:
        run_details: Analysis run metadata
        results: List of result dictionaries
    """
    # Import the original display logic for now
    # In future, this will use the new modular formatters
    from eon.ui.components.results_display_legacy import display_results as legacy_display
    return legacy_display(run_details, results)
