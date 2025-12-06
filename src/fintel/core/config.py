#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration management for Fintel using Pydantic Settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FintelConfig(BaseSettings):
    """
    Main configuration class for Fintel.

    Loads settings from environment variables and .env file.
    All settings can be overridden with FINTEL_ prefix.

    Example:
        export FINTEL_DATA_DIR=/path/to/data
        export FINTEL_NUM_WORKERS=10
    """

    # API Keys
    google_api_keys: List[str] = Field(
        default_factory=list,
        description="List of Google Gemini API keys for parallel processing"
    )

    # Paths
    data_dir: Path = Field(
        default=Path("./data"),
        description="Base directory for data storage"
    )
    cache_dir: Path = Field(
        default=Path("./cache"),
        description="Directory for caching API responses and intermediate data"
    )
    log_dir: Path = Field(
        default=Path("./logs"),
        description="Directory for log files"
    )

    # Processing Settings
    num_workers: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of parallel workers (typically one per API key)"
    )
    num_filings_per_company: int = Field(
        default=30,
        ge=1,
        le=50,
        description="Number of historical filings to process per company"
    )

    # API Rate Limiting
    max_requests_per_day: int = Field(
        default=500,
        ge=1,
        description="Maximum API requests per day per key"
    )
    sleep_after_request: int = Field(
        default=65,
        ge=0,
        description="Seconds to sleep after each API request (rate limiting)"
    )

    # AI Settings
    default_model: str = Field(
        default="gemini-2.5-flash",
        description="Default LLM model to use"
    )
    thinking_budget: int = Field(
        default=4096,
        ge=512,
        le=8192,
        description="Thinking budget for AI models"
    )
    use_structured_output: bool = Field(
        default=True,
        description="Use Pydantic structured output for AI responses"
    )

    # Storage Settings
    storage_backend: str = Field(
        default="parquet",
        pattern="^(json|parquet|sqlite|postgres)$",
        description="Storage backend: json, parquet, sqlite, or postgres"
    )

    # SEC Edgar Settings
    sec_company_name: str = Field(
        default="Research Script",
        description="Company name to use for SEC Edgar requests"
    )
    sec_user_email: str = Field(
        default="user@example.com",
        description="Email to use for SEC Edgar requests (required by SEC)"
    )

    # Selenium Settings
    chrome_driver_path: Optional[str] = Field(
        default=None,
        description="Path to Chrome WebDriver (None for automatic download)"
    )
    headless_browser: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )

    # Feature Flags
    enable_caching: bool = Field(
        default=True,
        description="Enable caching of API responses"
    )
    enable_progress_tracking: bool = Field(
        default=True,
        description="Enable progress tracking and resumption"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FINTEL_",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"
    )

    def __init__(self, **kwargs):
        """Initialize config and create necessary directories."""
        # Load .env file manually to ensure it's loaded before pydantic processes it
        from dotenv import load_dotenv
        load_dotenv()

        super().__init__(**kwargs)

        # Load API keys from environment if not provided
        if not self.google_api_keys:
            keys = []
            for i in range(1, 26):  # Try to load up to 25 keys
                key = os.getenv(f"GOOGLE_API_KEY_{i}")
                if key and key not in keys:
                    keys.append(key)
            # Also check for single GOOGLE_API_KEY
            single_key = os.getenv("GOOGLE_API_KEY")
            if single_key and single_key not in keys:
                keys.append(single_key)
            self.google_api_keys = keys

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def num_api_keys(self) -> int:
        """Return number of available API keys."""
        return len(self.google_api_keys)

    def get_data_path(self, *parts: str) -> Path:
        """Get path within data directory."""
        return self.data_dir.joinpath(*parts)

    def get_cache_path(self, *parts: str) -> Path:
        """Get path within cache directory."""
        return self.cache_dir.joinpath(*parts)

    def get_log_path(self, *parts: str) -> Path:
        """Get path within log directory."""
        return self.log_dir.joinpath(*parts)


# Singleton instance
_config_instance: Optional[FintelConfig] = None


def get_config(**kwargs) -> FintelConfig:
    """
    Get or create the global configuration instance.

    Args:
        **kwargs: Optional configuration overrides

    Returns:
        FintelConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = FintelConfig(**kwargs)
    return _config_instance


def reset_config():
    """Reset the global configuration instance (mainly for testing)."""
    global _config_instance
    _config_instance = None
