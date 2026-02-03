#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Gemini LLM provider implementation.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

import json
import re
import time
from typing import Optional, Type, Union, Dict, Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from fintel.core import get_logger, AIProviderError
from .base import LLMProvider
from fintel.ai.rate_limiter import RateLimiter
from fintel.ai.request_queue import get_gemini_request_queue


class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM provider.

    Supports both structured (Pydantic) and unstructured outputs.

    Example:
        provider = GeminiProvider(
            api_key="your_key",
            model="gemini-2.5-flash"
        )

        # Structured output
        result = provider.generate(prompt, schema=TenKAnalysis)

        # Unstructured output
        result = provider.generate(prompt)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: Optional[int] = None,
        thinking_level: Optional[str] = None,
        use_google_search: bool = False,
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.5-flash, or use gemini-3-pro-preview)
            thinking_budget: Thinking budget for Gemini 2.x models (default: 4096)
            thinking_level: Thinking level for Gemini 3 models ("LOW", "MEDIUM", "HIGH")
            use_google_search: Enable Google Search tool for real-time web search
            rate_limiter: Optional rate limiter for API calls
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)

        # Support both Gemini 2 (thinking_budget) and Gemini 3 (thinking_level)
        self.thinking_budget = thinking_budget if thinking_budget is not None else 4096
        self.thinking_level = thinking_level  # For Gemini 3 models
        self.use_google_search = use_google_search
        self.rate_limiter = rate_limiter

        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)

        search_info = " with Google Search" if use_google_search else ""
        thinking_info = f" (thinking_level={thinking_level})" if thinking_level else f" (thinking_budget={self.thinking_budget})"
        self.logger.info(f"Initialized Gemini provider with model {model}{thinking_info}{search_info}")

    def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate a response from Gemini.

        Uses global request queue to serialize all API calls, ensuring rate limits
        are not exceeded even when running multiple analyses in parallel.

        Args:
            prompt: The prompt to send
            schema: Optional Pydantic schema for structured output
            **kwargs: Additional parameters (temperature, etc.)

        Returns:
            - If schema provided: Validated Pydantic model instance
            - If no schema: Dictionary with response

        Raises:
            AIProviderError: If generation fails
        """
        # Build configuration
        config_params = {}

        # Add thinking configuration (Gemini 2 vs Gemini 3)
        if self.thinking_level:
            # Gemini 3 style (thinkingConfig with thinkingLevel)
            config_params['thinkingConfig'] = {
                'thinkingLevel': self.thinking_level
            }
        elif not schema:
            # Gemini 2 style (ThinkingConfig with thinking_budget)
            # Only for unstructured output
            config_params['thinking_config'] = types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            )

        # Add Google Search tool if enabled
        tools = []
        if self.use_google_search:
            tools.append(types.Tool(googleSearch=types.GoogleSearch()))
            config_params['tools'] = tools
            self.logger.debug("Google Search tool enabled")

        # Add response format
        config_params['response_mime_type'] = "application/json"

        # Use global request queue to serialize the API call
        # This prevents concurrent requests from different threads/keys
        request_queue = get_gemini_request_queue()

        try:
            if schema:
                # Structured output with Pydantic validation
                self.logger.debug(f"Generating with schema: {schema.__name__}")
                config_params['response_schema'] = schema

                # Execute API call through global queue for serialization
                response = request_queue.execute_with_lock(
                    request_func=self.client.models.generate_content,
                    api_key=self.api_key,
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_params, **kwargs),
                )

                # Parse and validate with Pydantic
                result = schema.model_validate_json(response.text)
                self.logger.debug("Successfully generated structured response")

                # Record API usage in rate limiter
                # Note: Do NOT call record_and_sleep() because the request queue already
                # handled the mandatory 65s sleep. Instead, record directly to the tracker.
                if self.rate_limiter:
                    self.rate_limiter.tracker.record_request(self.api_key, error=False)

                return result

            else:
                # Unstructured JSON output
                self.logger.debug("Generating unstructured response")

                # Execute API call through global queue for serialization
                response = request_queue.execute_with_lock(
                    request_func=self.client.models.generate_content,
                    api_key=self.api_key,
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_params, **kwargs),
                )

                # Clean and parse JSON
                response_text = response.text.strip()

                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '', 1)
                if response_text.endswith('```'):
                    response_text = response_text[:-3]

                response_text = response_text.strip()

                # Parse JSON
                result = json.loads(response_text)
                self.logger.debug("Successfully generated unstructured response")

                # Record API usage in rate limiter
                # Note: Do NOT call record_and_sleep() because the request queue already
                # handled the mandatory 65s sleep. Instead, record directly to the tracker.
                if self.rate_limiter:
                    self.rate_limiter.tracker.record_request(self.api_key, error=False)

                return result

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            self.logger.error(error_msg)
            raise AIProviderError(error_msg) from e

        except Exception as e:
            error_str = str(e).lower()
            # Check for context length exceeded errors
            # These can manifest as various error messages from the API
            context_error_indicators = [
                'token count',
                'context length',
                'maximum context',
                'input too long',
                'request payload size exceeds',
                'exceeds the limit',
                'too many tokens',
                'content too large',
            ]
            if any(indicator in error_str for indicator in context_error_indicators):
                from fintel.core.exceptions import ContextLengthExceededError
                error_msg = f"Input exceeds model context limit: {str(e)}"
                self.logger.warning(error_msg)
                raise ContextLengthExceededError(error_msg) from e

            error_msg = f"Gemini generation failed: {str(e)}"
            self.logger.error(error_msg)
            raise AIProviderError(error_msg) from e

    def _parse_retry_delay(self, error: Exception) -> Optional[int]:
        """
        Parse retryDelay from API error response.

        The Gemini API returns 429 errors with a retryDelay field like:
        {'retryDelay': '55s'} or "retryDelay": "35.159591337s"

        Args:
            error: Exception from API call

        Returns:
            Retry delay in seconds (rounded up), or None if not parseable
        """
        import math
        error_str = str(error)

        # Look for retryDelay pattern - handle both integer and decimal seconds
        # Examples: 'retryDelay': '55s', 'retryDelay': '35.159591337s'
        match = re.search(r"['\"]retryDelay['\"]:\s*['\"](\d+(?:\.\d+)?)s?['\"]", error_str, re.IGNORECASE)
        if match:
            delay = float(match.group(1))
            return math.ceil(delay)  # Round up to be safe

        return None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if an error is a rate limit (429) error.

        Args:
            error: Exception from API call

        Returns:
            True if this is a rate limit error
        """
        error_str = str(error).lower()
        return '429' in error_str or 'rate limit' in error_str or 'resource_exhausted' in error_str

    def _is_transient_service_error(self, error: Exception) -> bool:
        """
        Check if an error looks like a transient service availability issue.

        Args:
            error: Exception from API call

        Returns:
            True if this is likely a transient service error
        """
        error_str = str(error).lower()
        transient_indicators = [
            '500',
            '502',
            '503',
            '504',
            'service unavailable',
            'internal error',
            'temporarily unavailable',
            'deadline exceeded',
            'unavailable',
            'backend error',
        ]
        return any(indicator in error_str for indicator in transient_indicators)

    def generate_with_retry(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        max_retries: int = 3,
        retry_delay: int = 10,
        buffer_seconds: int = 20,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate with automatic retry on failure.

        For rate limit (429) errors, parses the API's suggested retry delay
        and adds a buffer. Rate limit retries don't count against max_retries.

        Args:
            prompt: The prompt to send
            schema: Optional Pydantic schema for structured output
            max_retries: Maximum number of retry attempts for non-rate-limit errors
            retry_delay: Default seconds to wait between retries (fallback)
            buffer_seconds: Additional buffer to add to API-suggested retry delay
            **kwargs: Additional parameters

        Returns:
            - If schema provided: Validated Pydantic model instance
            - If no schema: Dictionary with response

        Raises:
            AIProviderError: If all retries fail
        """
        last_error = None
        non_rate_limit_attempts = 0
        rate_limit_retries = 0
        last_category = "other"
        max_rate_limit_retries = 10  # Allow many rate-limit retries since we wait the specified time
        total_attempts = 0
        max_total_attempts = max_retries + max_rate_limit_retries  # More generous for rate limits
        operator_action = None

        while non_rate_limit_attempts < max_retries and rate_limit_retries < max_rate_limit_retries and total_attempts < max_total_attempts:
            total_attempts += 1

            try:
                self.logger.debug(f"Generation attempt {total_attempts} (non-rate-limit: {non_rate_limit_attempts + 1}/{max_retries})")
                result = self.generate(prompt, schema, **kwargs)
                return result

            except AIProviderError as e:
                last_error = e
                is_rate_limit = self._is_rate_limit_error(e)
                is_transient_service = self._is_transient_service_error(e)

                if is_rate_limit:
                    last_category = "rate_limit"
                    operator_action = None
                    rate_limit_retries += 1
                    # Parse API-suggested retry delay
                    api_delay = self._parse_retry_delay(e)

                    if api_delay:
                        actual_delay = api_delay + buffer_seconds
                        self.logger.warning(
                            f"Rate limit hit ({rate_limit_retries}/{max_rate_limit_retries}). "
                            f"API suggests {api_delay}s delay. "
                            f"Waiting {actual_delay}s (with {buffer_seconds}s buffer)..."
                        )
                    else:
                        # Fallback: use a longer delay for rate limits
                        actual_delay = max(retry_delay * 2, 60) + buffer_seconds
                        self.logger.warning(
                            f"Rate limit hit ({rate_limit_retries}/{max_rate_limit_retries}). "
                            f"Could not parse delay. Waiting {actual_delay}s..."
                        )

                    time.sleep(actual_delay)
                    # Don't increment non_rate_limit_attempts - rate limit waits are "free"
                else:
                    # Non-rate-limit error
                    if is_transient_service:
                        last_category = "service_unavailable"
                        operator_action = "Suggested action: retry later or reduce concurrency."
                    else:
                        last_category = "other"
                        operator_action = None
                    non_rate_limit_attempts += 1
                    self.logger.warning(
                        f"Attempt {non_rate_limit_attempts}/{max_retries} failed: {e}. "
                        f"Retrying in {retry_delay} seconds..."
                    )

                    if non_rate_limit_attempts < max_retries:
                        time.sleep(retry_delay)

        # All retries failed
        error_msg = (
            f"All retries exhausted. "
            f"Non-rate-limit attempts: {non_rate_limit_attempts}/{max_retries}, "
            f"Rate-limit retries: {rate_limit_retries}/{max_rate_limit_retries}. "
            f"Last error: {last_error}. "
            f"Final category: {last_category}."
        )
        if operator_action:
            error_msg = f"{error_msg} {operator_action}"
        self.logger.error(error_msg)
        raise AIProviderError(error_msg) from last_error

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Uses the global request queue to respect rate limits and serialization.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Use request queue to respect rate limiting
            request_queue = get_gemini_request_queue()

            def _validation_request():
                return self.client.models.generate_content(
                    model=self.model,
                    contents="Hello, respond with 'OK'",
                )

            request_queue.execute_with_lock(
                request_func=_validation_request,
                api_key=self.api_key,
            )
            self.logger.info("API key validation successful")
            return True

        except Exception as e:
            self.logger.error(f"API key validation failed: {e}")
            return False

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (useful for prompt engineering).

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        try:
            # Gemini doesn't have a direct token counter, use rough estimate
            # ~4 characters per token is a common heuristic
            return len(text) // 4

        except Exception as e:
            self.logger.warning(f"Token counting failed: {e}")
            return 0
