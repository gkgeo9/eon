#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared utilities and constants.

This module provides a single source of truth for common constants,
helper functions, and shared logic used across the codebase.
"""

from typing import FrozenSet


# Filing type classifications - single source of truth
ANNUAL_FILINGS: FrozenSet[str] = frozenset({
    '10-K', '10-K/A', '10-KSB', '10-KSB/A',
    '20-F', '20-F/A',
    'N-CSR', 'N-CSRS',
    '40-F', '40-F/A',
    'ARS'
})

QUARTERLY_FILINGS: FrozenSet[str] = frozenset({
    '10-Q', '10-Q/A', '10-QSB', '10-QSB/A',
    '6-K', '6-K/A'
})

EVENT_FILINGS: FrozenSet[str] = frozenset({
    '8-K', '8-K/A',
    '4', '4/A',
    'DEF 14A', 'DEFA14A',
    'SC 13D', 'SC 13D/A',
    'SC 13G', 'SC 13G/A'
})


def is_annual_filing(filing_type: str) -> bool:
    """
    Check if a filing type is an annual filing.

    Args:
        filing_type: The filing type to check (e.g., '10-K', '20-F')

    Returns:
        True if this is an annual filing type
    """
    return filing_type.upper() in ANNUAL_FILINGS


def is_quarterly_filing(filing_type: str) -> bool:
    """
    Check if a filing type is a quarterly filing.

    Args:
        filing_type: The filing type to check (e.g., '10-Q', '6-K')

    Returns:
        True if this is a quarterly filing type
    """
    return filing_type.upper() in QUARTERLY_FILINGS


def is_event_filing(filing_type: str) -> bool:
    """
    Check if a filing type is an event-based filing.

    Args:
        filing_type: The filing type to check (e.g., '8-K', 'DEF 14A')

    Returns:
        True if this is an event-based filing type
    """
    return filing_type.upper() in EVENT_FILINGS


def mask_api_key(key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for safe logging.

    Args:
        key: The API key to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked key string (e.g., '...abcd')

    Examples:
        >>> mask_api_key('sk-1234567890abcdef')
        '...cdef'
        >>> mask_api_key('')
        'None'
        >>> mask_api_key(None)
        'None'
    """
    if not key:
        return 'None'
    if len(key) <= visible_chars:
        return '...' + key
    return '...' + key[-visible_chars:]


def get_filing_category(filing_type: str) -> str:
    """
    Get the category of a filing type.

    Args:
        filing_type: The filing type to categorize

    Returns:
        Category string: 'annual', 'quarterly', 'event', or 'other'
    """
    filing_upper = filing_type.upper()
    if filing_upper in ANNUAL_FILINGS:
        return 'annual'
    elif filing_upper in QUARTERLY_FILINGS:
        return 'quarterly'
    elif filing_upper in EVENT_FILINGS:
        return 'event'
    return 'other'
