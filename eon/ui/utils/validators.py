#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validation utilities for user inputs.
"""

from typing import Tuple


def validate_ticker(ticker: str) -> Tuple[bool, str]:
    """
    Validate ticker symbol.

    Args:
        ticker: Ticker symbol

    Returns:
        (is_valid, error_message)
    """
    if not ticker or len(ticker.strip()) == 0:
        return False, "Ticker cannot be empty"

    ticker = ticker.strip().upper()

    if len(ticker) > 10:
        return False, "Ticker is too long (max 10 characters)"

    if not ticker.isalpha():
        return False, "Ticker must contain only letters"

    return True, ""


def validate_cik(cik: str) -> Tuple[bool, str]:
    """
    Validate CIK (Central Index Key) number.

    CIK format: Up to 10 digits, leading zeros optional.
    Example: 0001018724 or 1018724 (both valid for Enron)

    Args:
        cik: CIK number string

    Returns:
        (is_valid, error_message)
    """
    if not cik or len(cik.strip()) == 0:
        return False, "CIK cannot be empty"

    cik = cik.strip()

    # Remove leading zeros for validation
    cik_normalized = cik.lstrip('0')

    if len(cik_normalized) == 0:
        return False, "CIK cannot be all zeros"

    if len(cik) > 10:
        return False, "CIK is too long (max 10 digits)"

    if not cik.isdigit():
        return False, "CIK must contain only digits"

    return True, ""


def validate_company_identifier(identifier: str, mode: str = 'ticker') -> Tuple[bool, str]:
    """
    Validate company identifier based on input mode.

    Args:
        identifier: Ticker symbol or CIK number
        mode: 'ticker' or 'cik'

    Returns:
        (is_valid, error_message)
    """
    if mode == 'cik':
        return validate_cik(identifier)
    else:
        return validate_ticker(identifier)


def validate_prompt_template(template: str) -> Tuple[bool, str]:
    """
    Validate prompt template.

    Args:
        template: Prompt template string

    Returns:
        (is_valid, error_message)
    """
    if not template or len(template.strip()) < 50:
        return False, "Prompt must be at least 50 characters"

    # Check for required placeholders
    if '{ticker}' not in template and '{year}' not in template:
        return False, "Prompt should include {ticker} and/or {year} placeholders"

    # Check length
    if len(template) > 50000:
        return False, "Prompt exceeds maximum length (50,000 chars)"

    return True, ""


def validate_prompt_name(name: str) -> Tuple[bool, str]:
    """
    Validate prompt name.

    Args:
        name: Prompt name

    Returns:
        (is_valid, error_message)
    """
    if not name or len(name.strip()) < 3:
        return False, "Name must be at least 3 characters"

    if len(name) > 100:
        return False, "Name is too long (max 100 characters)"

    return True, ""
