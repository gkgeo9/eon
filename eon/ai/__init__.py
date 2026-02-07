#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI infrastructure for EON.

Provides API key management, rate limiting, usage tracking, and LLM provider abstractions.
"""

from .api_config import APILimits, API_LIMITS, get_api_limits
from .usage_tracker import APIUsageTracker, get_usage_tracker, reset_tracker
from .key_manager import APIKeyManager
from .rate_limiter import RateLimiter
from .request_queue import GeminiRequestQueue, get_gemini_request_queue, reset_gemini_request_queue

__all__ = [
    # Configuration
    'APILimits',
    'API_LIMITS',
    'get_api_limits',
    # Usage Tracking
    'APIUsageTracker',
    'get_usage_tracker',
    'reset_tracker',
    # Key Management
    'APIKeyManager',
    # Rate Limiting
    'RateLimiter',
    # Request Queue (global serialization)
    'GeminiRequestQueue',
    'get_gemini_request_queue',
    'reset_gemini_request_queue',
]
