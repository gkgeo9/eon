"""
JSON-based storage backend.

This module provides a JSON storage backend for human-readable persistence
of analysis results. Ideal for debugging and small to medium datasets.
"""

import json
from pathlib import Path
from typing import Optional, List, Type
from pydantic import BaseModel

from fintel.data.storage.base import StorageBackend
from fintel.core import get_logger, StorageError

logger = get_logger(__name__)


class JSONStore(StorageBackend):
    """
    JSON-based storage backend.

    Features:
    - Human-readable format for easy inspection
    - Hierarchical directory structure: {ticker}/{year}_{analysis_type}.json
    - Pretty-printed JSON for readability
    - Automatic directory creation
    """

    def __init__(self, base_dir: Path):
        """
        Initialize JSON storage backend.

        Args:
            base_dir: Base directory for storing JSON files
        """
        super().__init__(base_dir)
        logger.info(f"Initialized JSON storage at {self.base_dir}")

    def _get_file_path(self, key: str) -> Path:
        """
        Get the full file path for a storage key.

        Args:
            key: Storage key (e.g., "AAPL/2024_fundamental")

        Returns:
            Full path to JSON file
        """
        return self.base_dir / f"{key}.json"

    def save(self, data: BaseModel, key: str) -> None:
        """
        Save a Pydantic model to JSON storage.

        Args:
            data: Pydantic model instance to save
            key: Storage key (e.g., "AAPL/2024_fundamental")

        Raises:
            StorageError: If save operation fails
        """
        try:
            file_path = self._get_file_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert Pydantic model to dict and save as pretty JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    data.model_dump(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,  # Handle datetime, Path, etc.
                )

            logger.debug(f"Saved data to {file_path}")

        except Exception as e:
            raise StorageError(f"Failed to save to JSON: {e}") from e

    def load(self, key: str, schema: Type[BaseModel]) -> Optional[BaseModel]:
        """
        Load a Pydantic model from JSON storage.

        Args:
            key: Storage key (e.g., "AAPL/2024_fundamental")
            schema: Pydantic model class to deserialize into

        Returns:
            Deserialized Pydantic model instance, or None if not found

        Raises:
            StorageError: If load operation fails
        """
        try:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                logger.debug(f"Key not found: {key}")
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            result = schema(**data)
            logger.debug(f"Loaded data from {file_path}")
            return result

        except Exception as e:
            raise StorageError(f"Failed to load from JSON: {e}") from e

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in storage.

        Args:
            key: Storage key to check

        Returns:
            True if key exists, False otherwise
        """
        return self._get_file_path(key).exists()

    def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys in storage with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys (e.g., "AAPL/")

        Returns:
            List of storage keys (without .json extension)
        """
        try:
            search_dir = self.base_dir / prefix if prefix else self.base_dir

            if not search_dir.exists():
                return []

            # Find all JSON files recursively
            json_files = search_dir.rglob("*.json")

            # Convert to relative keys (remove base_dir and .json extension)
            keys = []
            for file_path in json_files:
                relative_path = file_path.relative_to(self.base_dir)
                key = str(relative_path.with_suffix(""))  # Remove .json
                keys.append(key)

            return sorted(keys)

        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []

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
        try:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                logger.debug(f"Key not found for deletion: {key}")
                return False

            file_path.unlink()
            logger.info(f"Deleted {file_path}")

            # Clean up empty parent directories
            try:
                file_path.parent.rmdir()
            except OSError:
                pass  # Directory not empty, that's fine

            return True

        except Exception as e:
            raise StorageError(f"Failed to delete from JSON: {e}") from e
