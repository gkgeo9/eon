#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Result types for explicit error handling.

This module provides Result types that make success/failure explicit,
preventing silent failures where errors are logged but callers don't know
something went wrong.
"""

from dataclasses import dataclass, field
from typing import TypeVar, Generic, Optional, List, Any


T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """
    A result that explicitly indicates success or failure.

    This type should be used instead of returning empty collections on failure,
    which creates "silent failures" where callers don't know something went wrong.

    Attributes:
        success: Whether the operation succeeded
        value: The result value (present if success=True)
        error: Error message (present if success=False)
        warnings: List of warning messages

    Example:
        >>> def fetch_data() -> Result[dict]:
        ...     try:
        ...         data = api.get_data()
        ...         return Result.ok(data)
        ...     except APIError as e:
        ...         return Result.fail(str(e))
        ...
        >>> result = fetch_data()
        >>> if result.success:
        ...     process(result.value)
        ... else:
        ...     log_error(result.error)
    """
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def ok(cls, value: T, warnings: Optional[List[str]] = None) -> 'Result[T]':
        """
        Create a successful result.

        Args:
            value: The successful result value
            warnings: Optional list of warnings

        Returns:
            Result with success=True
        """
        return cls(success=True, value=value, warnings=warnings or [])

    @classmethod
    def fail(cls, error: str, warnings: Optional[List[str]] = None) -> 'Result[T]':
        """
        Create a failed result.

        Args:
            error: Error message describing what went wrong
            warnings: Optional list of warnings

        Returns:
            Result with success=False
        """
        return cls(success=False, error=error, warnings=warnings or [])

    @classmethod
    def partial(cls, value: T, error: str, warnings: Optional[List[str]] = None) -> 'Result[T]':
        """
        Create a partial result (success with warnings or incomplete data).

        Use this when an operation partially succeeded - for example,
        when downloading filings and some succeeded but others failed.

        Args:
            value: The partial result value
            error: Description of what was incomplete or failed
            warnings: Optional list of warnings

        Returns:
            Result with success=True but also an error message
        """
        return cls(success=True, value=value, error=error, warnings=warnings or [])

    def is_ok(self) -> bool:
        """Check if the result is successful."""
        return self.success

    def is_error(self) -> bool:
        """Check if the result is a failure."""
        return not self.success

    def is_partial(self) -> bool:
        """Check if the result is partial (success with error message)."""
        return self.success and self.error is not None

    def unwrap(self) -> T:
        """
        Get the value, raising if the result is a failure.

        Returns:
            The result value

        Raises:
            ValueError: If the result is a failure
        """
        if not self.success:
            raise ValueError(f"Cannot unwrap failed result: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Get the value, or a default if the result is a failure.

        Args:
            default: Default value to return on failure

        Returns:
            The result value or the default
        """
        return self.value if self.success else default

    def map(self, func) -> 'Result':
        """
        Apply a function to the value if successful.

        Args:
            func: Function to apply to the value

        Returns:
            New Result with transformed value, or the same failure
        """
        if self.success:
            try:
                return Result.ok(func(self.value), self.warnings)
            except Exception as e:
                return Result.fail(str(e), self.warnings)
        return self

    def __bool__(self) -> bool:
        """Allow using Result in boolean context."""
        return self.success


@dataclass
class BatchResult(Generic[T]):
    """
    Result type for batch operations with individual item tracking.

    Attributes:
        total: Total number of items attempted
        succeeded: Number of successful items
        failed: Number of failed items
        results: Dictionary mapping item key to Result
        errors: Dictionary mapping item key to error message

    Example:
        >>> batch = BatchResult[dict]()
        >>> for ticker in tickers:
        ...     try:
        ...         data = analyze(ticker)
        ...         batch.add_success(ticker, data)
        ...     except Exception as e:
        ...         batch.add_failure(ticker, str(e))
        >>> print(f"Completed: {batch.succeeded}/{batch.total}")
    """
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)

    def add_success(self, key: Any, value: T) -> None:
        """Add a successful result."""
        self.total += 1
        self.succeeded += 1
        self.results[key] = Result.ok(value)

    def add_failure(self, key: Any, error: str) -> None:
        """Add a failed result."""
        self.total += 1
        self.failed += 1
        self.results[key] = Result.fail(error)
        self.errors[key] = error

    def add_partial(self, key: Any, value: T, error: str) -> None:
        """Add a partial result."""
        self.total += 1
        self.succeeded += 1  # Counts as success since we have a value
        self.results[key] = Result.partial(value, error)

    @property
    def success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total == 0:
            return 0.0
        return (self.succeeded / self.total) * 100

    @property
    def all_succeeded(self) -> bool:
        """Check if all items succeeded."""
        return self.failed == 0 and self.total > 0

    @property
    def all_failed(self) -> bool:
        """Check if all items failed."""
        return self.succeeded == 0 and self.total > 0

    def get_successful_values(self) -> dict:
        """Get only the successful values."""
        return {
            key: result.value
            for key, result in self.results.items()
            if result.success
        }
