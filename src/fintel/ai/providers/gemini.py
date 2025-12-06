#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Gemini LLM provider implementation.
Extracted and refactored from standardized_sec_ai/tenk_processor.py
"""

import json
import time
from typing import Optional, Type, Union, Dict, Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from fintel.core import get_logger, AIProviderError
from .base import LLMProvider
from fintel.ai.rate_limiter import RateLimiter


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
        thinking_budget: int = 4096,
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.5-flash)
            thinking_budget: Thinking budget for the model
            rate_limiter: Optional rate limiter for API calls
            **kwargs: Additional configuration
        """
        super().__init__(api_key, model, **kwargs)
        self.thinking_budget = thinking_budget
        self.rate_limiter = rate_limiter

        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)
        self.logger.info(f"Initialized Gemini provider with model {model}")

    def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate a response from Gemini.

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
        try:
            if schema:
                # Structured output with Pydantic validation
                self.logger.debug(f"Generating with schema: {schema.__name__}")

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        **kwargs
                    ),
                )

                # Parse and validate with Pydantic
                result = schema.model_validate_json(response.text)
                self.logger.debug("Successfully generated structured response")

                # Record API usage and sleep (if rate limiter configured)
                if self.rate_limiter:
                    self.rate_limiter.record_and_sleep(self.api_key)

                return result

            else:
                # Unstructured JSON output
                self.logger.debug("Generating unstructured response")

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=self.thinking_budget
                        ),
                        **kwargs
                    ),
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

                # Record API usage and sleep (if rate limiter configured)
                if self.rate_limiter:
                    self.rate_limiter.record_and_sleep(self.api_key)

                return result

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            self.logger.error(error_msg)
            raise AIProviderError(error_msg) from e

        except Exception as e:
            error_msg = f"Gemini generation failed: {str(e)}"
            self.logger.error(error_msg)
            raise AIProviderError(error_msg) from e

    def generate_with_retry(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        max_retries: int = 3,
        retry_delay: int = 10,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate with automatic retry on failure.

        Args:
            prompt: The prompt to send
            schema: Optional Pydantic schema for structured output
            max_retries: Maximum number of retry attempts
            retry_delay: Seconds to wait between retries
            **kwargs: Additional parameters

        Returns:
            - If schema provided: Validated Pydantic model instance
            - If no schema: Dictionary with response

        Raises:
            AIProviderError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Generation attempt {attempt + 1}/{max_retries}")
                result = self.generate(prompt, schema, **kwargs)
                return result

            except AIProviderError as e:
                last_error = e
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {retry_delay} seconds..."
                )

                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    time.sleep(retry_delay)

        # All retries failed
        error_msg = f"All {max_retries} attempts failed. Last error: {last_error}"
        self.logger.error(error_msg)
        raise AIProviderError(error_msg) from last_error

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Simple test prompt
            self.client.models.generate_content(
                model=self.model,
                contents="Hello, respond with 'OK'",
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
