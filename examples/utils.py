#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions for examples.
"""

from fintel.ai import APIKeyManager, RateLimiter
from fintel.core import get_config


def init_components(sleep_seconds=0):
    """
    Initialize API key manager and rate limiter for examples.

    Args:
        sleep_seconds: Seconds to sleep after each request (default: 0 for testing, use 65 for production)

    Returns:
        tuple: (api_key_manager, rate_limiter)

    Raises:
        ValueError: If no API keys are found
    """
    config = get_config()

    if not config.google_api_keys:
        raise ValueError(
            "No Google API keys found. Please set GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, "
            "etc. in .env file"
        )

    api_key_manager = APIKeyManager(
        api_keys=config.google_api_keys,
        max_requests_per_day=config.max_requests_per_day
    )

    rate_limiter = RateLimiter(
        sleep_after_request=sleep_seconds,
        max_requests_per_day=config.max_requests_per_day
    )

    return api_key_manager, rate_limiter
