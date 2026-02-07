"""
Storage backends for EON analysis results.

This module provides multiple storage backends for persisting analysis results:
- JSONStore: Human-readable JSON files for easy inspection
- ParquetStore: Columnar storage for efficient querying of large datasets
- ResultExporter: Export aggregated results to CSV/Excel
"""

from eon.data.storage.base import StorageBackend
from eon.data.storage.json_store import JSONStore
from eon.data.storage.parquet_store import ParquetStore
from eon.data.storage.exporter import ResultExporter

__all__ = [
    "StorageBackend",
    "JSONStore",
    "ParquetStore",
    "ResultExporter",
]
