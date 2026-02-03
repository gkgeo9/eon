#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for Gemini API rate limiting and retry mechanisms.

Tests the dynamic retry delay parsing and buffer addition for 429 errors.
"""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestRetryDelayParsing:
    """Tests for parsing retryDelay from API error responses."""

    @pytest.fixture
    def mock_provider(self, temp_usage_dir):
        """Create a GeminiProvider with mocked dependencies."""
        from fintel.ai.providers.gemini import GeminiProvider
        from fintel.ai.rate_limiter import RateLimiter
        from fintel.ai.usage_tracker import APIUsageTracker

        tracker = APIUsageTracker(usage_dir=temp_usage_dir)
        rate_limiter = RateLimiter(sleep_after_request=0, tracker=tracker)

        with patch('fintel.ai.providers.gemini.genai.Client'):
            provider = GeminiProvider(
                api_key="test_key",
                model="gemini-2.5-flash",
                rate_limiter=rate_limiter
            )

        return provider

    @pytest.mark.unit
    def test_parse_retry_delay_single_quotes(self, mock_provider):
        """Test parsing retryDelay with single quotes."""
        # Simulate error with single-quoted retryDelay
        error_msg = "Error: {'retryDelay': '55s', 'code': 429}"

        delay = mock_provider._parse_retry_delay(Exception(error_msg))

        assert delay == 55

    @pytest.mark.unit
    def test_parse_retry_delay_double_quotes(self, mock_provider):
        """Test parsing retryDelay with double quotes."""
        # Simulate error with double-quoted retryDelay (JSON style)
        error_msg = '{"error": {"retryDelay": "30s", "code": 429}}'

        delay = mock_provider._parse_retry_delay(Exception(error_msg))

        assert delay == 30

    @pytest.mark.unit
    def test_parse_retry_delay_without_s_suffix(self, mock_provider):
        """Test parsing retryDelay without 's' suffix."""
        error_msg = "{'retryDelay': '45'}"

        delay = mock_provider._parse_retry_delay(Exception(error_msg))

        assert delay == 45

    @pytest.mark.unit
    def test_parse_retry_delay_handles_missing(self, mock_provider):
        """Test that missing retryDelay returns None."""
        error_msg = "Some other error without delay info"

        delay = mock_provider._parse_retry_delay(Exception(error_msg))

        assert delay is None

    @pytest.mark.unit
    def test_parse_retry_delay_handles_malformed(self, mock_provider):
        """Test that malformed retryDelay returns None."""
        error_msg = "retryDelay is not a number: abc"

        delay = mock_provider._parse_retry_delay(Exception(error_msg))

        assert delay is None

    @pytest.mark.unit
    def test_is_rate_limit_error_429(self, mock_provider):
        """Test detection of 429 rate limit error."""
        from fintel.core import AIProviderError

        error = AIProviderError("429 RESOURCE_EXHAUSTED: Rate limit exceeded")

        assert mock_provider._is_rate_limit_error(error) is True

    @pytest.mark.unit
    def test_is_rate_limit_error_resource_exhausted(self, mock_provider):
        """Test detection of RESOURCE_EXHAUSTED error."""
        from fintel.core import AIProviderError

        error = AIProviderError("RESOURCE_EXHAUSTED: Quota exceeded")

        assert mock_provider._is_rate_limit_error(error) is True

    @pytest.mark.unit
    def test_is_rate_limit_error_other_error(self, mock_provider):
        """Test that non-rate-limit errors return False."""
        from fintel.core import AIProviderError

        error = AIProviderError("500 Internal Server Error")

        assert mock_provider._is_rate_limit_error(error) is False


class TestRetryWithDynamicDelay:
    """Tests for generate_with_retry using dynamic delays."""

    @pytest.fixture
    def mock_provider(self, temp_usage_dir):
        """Create a GeminiProvider with mocked dependencies."""
        from fintel.ai.providers.gemini import GeminiProvider
        from fintel.ai.rate_limiter import RateLimiter
        from fintel.ai.usage_tracker import APIUsageTracker

        tracker = APIUsageTracker(usage_dir=temp_usage_dir)
        rate_limiter = RateLimiter(sleep_after_request=0, tracker=tracker)

        with patch('fintel.ai.providers.gemini.genai.Client'):
            provider = GeminiProvider(
                api_key="test_key",
                model="gemini-2.5-flash",
                rate_limiter=rate_limiter
            )

        return provider

    @pytest.mark.unit
    def test_retry_uses_api_delay_plus_buffer(self, mock_provider):
        """Test that retry waits API delay + buffer on 429 errors."""
        from fintel.core import AIProviderError

        call_count = 0
        wait_times = []

        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with rate limit
                raise AIProviderError("429 Rate limit: {'retryDelay': '5s'}")
            # Second call succeeds
            return {'result': 'success'}

        mock_provider.generate = mock_generate

        # Patch time.sleep to record wait times instead of actually waiting
        original_sleep = time.sleep

        def mock_sleep(seconds):
            wait_times.append(seconds)

        with patch('time.sleep', mock_sleep):
            result = mock_provider.generate_with_retry(
                prompt="test",
                max_retries=3,
                retry_delay=10,
                buffer_seconds=20
            )

        assert result == {'result': 'success'}
        assert call_count == 2
        # Should have waited 5s (API delay) + 20s (buffer) = 25s
        assert len(wait_times) == 1
        assert wait_times[0] == 25

    @pytest.mark.unit
    def test_rate_limit_retries_dont_count_against_max(self, mock_provider):
        """Test that rate limit retries don't count against max_retries."""
        from fintel.core import AIProviderError

        call_count = 0

        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                # First 3 calls fail with rate limit
                raise AIProviderError("429 Rate limit exceeded: {'retryDelay': '1s'}")
            # Fourth call succeeds
            return {'result': 'success'}

        mock_provider.generate = mock_generate

        with patch('time.sleep'):
            result = mock_provider.generate_with_retry(
                prompt="test",
                max_retries=2,  # Only 2 "real" retries allowed
                buffer_seconds=0  # No buffer to speed up test
            )

        # Should have succeeded because rate limit retries are "free"
        assert result == {'result': 'success'}
        assert call_count == 4  # 3 rate limit failures + 1 success

    @pytest.mark.unit
    def test_non_rate_limit_errors_count_against_max(self, mock_provider):
        """Test that non-rate-limit errors count against max_retries."""
        from fintel.core import AIProviderError

        call_count = 0

        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Always fail with a non-rate-limit error
            raise AIProviderError("500 Internal Server Error")

        mock_provider.generate = mock_generate

        with patch('time.sleep'):
            with pytest.raises(AIProviderError) as exc_info:
                mock_provider.generate_with_retry(
                    prompt="test",
                    max_retries=3,
                    retry_delay=1
                )

        # Should have failed after max_retries attempts
        assert call_count == 3
        assert "3 attempts failed" in str(exc_info.value)

    @pytest.mark.unit
    def test_fallback_delay_when_no_api_delay(self, mock_provider):
        """Test fallback delay when retryDelay can't be parsed."""
        from fintel.core import AIProviderError

        call_count = 0
        wait_times = []

        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Rate limit error without retryDelay
                raise AIProviderError("429 RESOURCE_EXHAUSTED")
            return {'result': 'success'}

        mock_provider.generate = mock_generate

        def mock_sleep(seconds):
            wait_times.append(seconds)

        with patch('time.sleep', mock_sleep):
            result = mock_provider.generate_with_retry(
                prompt="test",
                max_retries=3,
                retry_delay=10,
                buffer_seconds=20
            )

        assert result == {'result': 'success'}
        # Fallback: max(retry_delay * 2, 60) + buffer = max(20, 60) + 20 = 80
        assert len(wait_times) == 1
        assert wait_times[0] == 80


class TestRealWorldErrorPatterns:
    """Test parsing of real-world error patterns from Gemini API."""

    @pytest.fixture
    def mock_provider(self, temp_usage_dir):
        """Create a GeminiProvider with mocked dependencies."""
        from fintel.ai.providers.gemini import GeminiProvider

        with patch('fintel.ai.providers.gemini.genai.Client'):
            provider = GeminiProvider(
                api_key="test_key",
                model="gemini-2.5-flash"
            )

        return provider

    @pytest.mark.unit
    def test_parse_real_gemini_error(self, mock_provider):
        """Test parsing a real Gemini API error response."""
        # Real error from the user's logs
        real_error = """429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 250000, model: gemini-2.5-flash\\nPlease retry in 55.756167577s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerMinute-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '250000'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '55s'}]}}"""

        delay = mock_provider._parse_retry_delay(Exception(real_error))

        assert delay == 55

    @pytest.mark.unit
    def test_parse_shorter_retry_delay(self, mock_provider):
        """Test parsing a shorter retry delay."""
        error = "{'retryDelay': '15s'}"

        delay = mock_provider._parse_retry_delay(Exception(error))

        assert delay == 15
