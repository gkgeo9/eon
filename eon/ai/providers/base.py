#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Abstract base class for LLM providers.
Allows easy swapping between Gemini, OpenAI, Anthropic, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional, Type, Union, Dict, Any
from pydantic import BaseModel

from eon.core import get_logger


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Supports both structured (Pydantic) and unstructured (dict) outputs.

    Example:
        class MyProvider(LLMProvider):
            def generate(self, prompt, schema=None):
                # Implementation
                pass
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider
            model: Model name/ID to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            schema: Optional Pydantic schema for structured output
            **kwargs: Additional generation parameters

        Returns:
            - If schema is provided: Validated Pydantic model instance
            - If schema is None: Dictionary with unstructured response

        Raises:
            AIProviderError: If generation fails
        """
        pass

    @abstractmethod
    def generate_with_retry(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[BaseModel, Dict[str, Any]]:
        """
        Generate with automatic retry on failure.

        Args:
            prompt: The prompt to send to the LLM
            schema: Optional Pydantic schema for structured output
            max_retries: Maximum number of retry attempts
            **kwargs: Additional generation parameters

        Returns:
            - If schema is provided: Validated Pydantic model instance
            - If schema is None: Dictionary with unstructured response

        Raises:
            AIProviderError: If all retries fail
        """
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Returns:
            True if API key is valid, False otherwise
        """
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(model={self.model})"
