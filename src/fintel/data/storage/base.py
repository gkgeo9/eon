"""
Abstract base class for storage backends.

This module defines the interface that all storage backends must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Type
from pydantic import BaseModel


class StorageBackend(ABC):
    """
    Abstract base class for all storage backends.

    Storage backends handle persistence and retrieval of Pydantic models
    representing analysis results.
    """

    def __init__(self, base_dir: Path):
        """
        Initialize the storage backend.

        Args:
            base_dir: Base directory for storing data
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def save(self, data: BaseModel, key: str) -> None:
        """
        Save a Pydantic model to storage.

        Args:
            data: Pydantic model instance to save
            key: Storage key (e.g., "AAPL/2024_fundamental")

        Raises:
            StorageError: If save operation fails
        """
        pass

    @abstractmethod
    def load(self, key: str, schema: Type[BaseModel]) -> Optional[BaseModel]:
        """
        Load a Pydantic model from storage.

        Args:
            key: Storage key (e.g., "AAPL/2024_fundamental")
            schema: Pydantic model class to deserialize into

        Returns:
            Deserialized Pydantic model instance, or None if not found

        Raises:
            StorageError: If load operation fails
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in storage.

        Args:
            key: Storage key to check

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys in storage with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys (e.g., "AAPL/")

        Returns:
            List of storage keys
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete an entry by key.

        Args:
            key: Storage key to delete

        Returns:
            True if deletion successful, False if key didn't exist

        Raises:
            StorageError: If deletion fails
        """
        pass
