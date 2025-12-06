"""
Storage backends for Fintel analysis results.

This module provides multiple storage backends for persisting analysis results:
- JSONStore: Human-readable JSON files for easy inspection
- ParquetStore: Columnar storage for efficient querying of large datasets
- ResultExporter: Export aggregated results to CSV/Excel
"""

from fintel.data.storage.base import StorageBackend
from fintel.data.storage.json_store import JSONStore
from fintel.data.storage.parquet_store import ParquetStore
from fintel.data.storage.exporter import ResultExporter

__all__ = [
    "StorageBackend",
    "JSONStore",
    "ParquetStore",
    "ResultExporter",
]
