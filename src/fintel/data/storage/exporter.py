"""
Result exporter for aggregating and exporting analysis results.

This module provides functionality to export analysis results to various formats:
- CSV: Simple tabular export
- Excel: Multi-sheet workbooks
- Parquet: Efficient columnar format
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from fintel.data.storage.json_store import JSONStore
from fintel.data.storage.parquet_store import ParquetStore
from fintel.core import get_logger, StorageError

logger = get_logger(__name__)


class ResultExporter:
    """
    Export aggregated analysis results to various formats.

    Supports exporting to CSV, Excel, and Parquet with configurable
    column selection and filtering.
    """

    def __init__(self, json_store: Optional[JSONStore] = None, parquet_store: Optional[ParquetStore] = None):
        """
        Initialize the result exporter.

        Args:
            json_store: Optional JSON storage backend to export from
            parquet_store: Optional Parquet storage backend to export from
        """
        self.json_store = json_store
        self.parquet_store = parquet_store
        logger.info("Initialized ResultExporter")

    def _flatten_pydantic_to_dict(self, model: BaseModel) -> Dict[str, Any]:
        """
        Flatten a Pydantic model to a single-level dictionary.

        Args:
            model: Pydantic model to flatten

        Returns:
            Flattened dictionary
        """
        def flatten(d: dict, parent_key: str = "", sep: str = "_") -> dict:
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key, sep=sep).items())
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    # Convert list of dicts to JSON string
                    items.append((new_key, str(v)))
                elif isinstance(v, list):
                    # Convert simple list to comma-separated string
                    items.append((new_key, ", ".join(map(str, v))))
                else:
                    items.append((new_key, v))
            return dict(items)

        return flatten(model.model_dump())

    def _load_all_from_json(self, analysis_type: Optional[str] = None) -> pd.DataFrame:
        """
        Load all records from JSON storage as a DataFrame.

        Args:
            analysis_type: Optional filter for analysis type

        Returns:
            DataFrame with all records

        Raises:
            ValueError: If json_store is not configured
        """
        if not self.json_store:
            raise ValueError("JSON store not configured")

        # Get all keys
        keys = self.json_store.list_keys()

        if analysis_type:
            keys = [k for k in keys if k.endswith(f"_{analysis_type}")]

        if not keys:
            logger.warning("No records found in JSON storage")
            return pd.DataFrame()

        # Load all records (this is a simple implementation - for large datasets, use Parquet)
        records = []
        for key in keys:
            try:
                # Parse key to extract metadata
                parts = key.split("/")
                if len(parts) == 2:
                    ticker = parts[0]
                    year_type = parts[1].split("_", 1)
                    if len(year_type) == 2:
                        year, atype = year_type
                        record = {
                            "ticker": ticker,
                            "year": year,
                            "analysis_type": atype,
                            "key": key
                        }
                        records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse key {key}: {e}")

        return pd.DataFrame(records)

    def export_to_csv(
        self,
        output_path: Path,
        analysis_type: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> None:
        """
        Export analysis results to CSV.

        Args:
            output_path: Path to output CSV file
            analysis_type: Optional filter for analysis type
            columns: Optional list of columns to include

        Raises:
            StorageError: If export fails
        """
        try:
            # Try Parquet first (more efficient)
            if self.parquet_store:
                if analysis_type:
                    df = self.parquet_store.load_dataframe(analysis_type)
                else:
                    # Load all analysis types
                    dfs = []
                    for type_dir in self.parquet_store.base_dir.iterdir():
                        if type_dir.is_dir():
                            try:
                                type_df = self.parquet_store.load_dataframe(type_dir.name)
                                if not type_df.empty:
                                    type_df["analysis_type"] = type_dir.name
                                    dfs.append(type_df)
                            except Exception as e:
                                logger.warning(f"Failed to load {type_dir.name}: {e}")
                    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            elif self.json_store:
                df = self._load_all_from_json(analysis_type)
            else:
                raise ValueError("No storage backend configured")

            if df.empty:
                logger.warning("No data to export")
                return

            # Select columns if specified
            if columns:
                available_cols = [col for col in columns if col in df.columns]
                if not available_cols:
                    logger.warning(f"None of the specified columns found in data")
                else:
                    df = df[available_cols]

            # Export to CSV
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            logger.info(f"Exported {len(df)} records to {output_path}")

        except Exception as e:
            raise StorageError(f"Failed to export to CSV: {e}") from e

    def export_to_excel(
        self,
        output_path: Path,
        sheets: Optional[Dict[str, List[str]]] = None
    ) -> None:
        """
        Export analysis results to Excel with multiple sheets.

        Args:
            output_path: Path to output Excel file
            sheets: Optional dict mapping sheet names to analysis types
                   e.g., {"Fundamental": ["fundamental"], "Perspectives": ["perspectives"]}

        Raises:
            StorageError: If export fails
        """
        try:
            if not self.parquet_store and not self.json_store:
                raise ValueError("No storage backend configured")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                if sheets:
                    # Export specified sheets
                    for sheet_name, analysis_types in sheets.items():
                        dfs = []
                        for analysis_type in analysis_types:
                            if self.parquet_store:
                                df = self.parquet_store.load_dataframe(analysis_type)
                            else:
                                df = self._load_all_from_json(analysis_type)

                            if not df.empty:
                                df["analysis_type"] = analysis_type
                                dfs.append(df)

                        if dfs:
                            combined_df = pd.concat(dfs, ignore_index=True)
                            combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            logger.info(f"Exported {len(combined_df)} records to sheet '{sheet_name}'")
                else:
                    # Export all analysis types as separate sheets
                    if self.parquet_store:
                        for type_dir in self.parquet_store.base_dir.iterdir():
                            if type_dir.is_dir():
                                analysis_type = type_dir.name
                                try:
                                    df = self.parquet_store.load_dataframe(analysis_type)
                                    if not df.empty:
                                        # Excel sheet names have 31 char limit
                                        sheet_name = analysis_type[:31]
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                                        logger.info(f"Exported {len(df)} records to sheet '{sheet_name}'")
                                except Exception as e:
                                    logger.warning(f"Failed to export {analysis_type}: {e}")
                    elif self.json_store:
                        df = self._load_all_from_json()
                        if not df.empty:
                            # Group by analysis type
                            for analysis_type, group_df in df.groupby("analysis_type"):
                                sheet_name = str(analysis_type)[:31]
                                group_df.to_excel(writer, sheet_name=sheet_name, index=False)
                                logger.info(f"Exported {len(group_df)} records to sheet '{sheet_name}'")

            logger.info(f"Exported to Excel: {output_path}")

        except Exception as e:
            raise StorageError(f"Failed to export to Excel: {e}") from e

    def export_to_parquet(
        self,
        output_path: Path,
        analysis_type: Optional[str] = None,
        partition_by: Optional[str] = None
    ) -> None:
        """
        Export analysis results to Parquet format.

        Args:
            output_path: Path to output Parquet file or directory
            analysis_type: Optional filter for analysis type
            partition_by: Optional column to partition by (e.g., "year", "ticker")

        Raises:
            StorageError: If export fails
        """
        try:
            # Load data
            if self.parquet_store:
                if analysis_type:
                    df = self.parquet_store.load_dataframe(analysis_type)
                else:
                    # Load all analysis types
                    dfs = []
                    for type_dir in self.parquet_store.base_dir.iterdir():
                        if type_dir.is_dir():
                            try:
                                type_df = self.parquet_store.load_dataframe(type_dir.name)
                                if not type_df.empty:
                                    type_df["analysis_type"] = type_dir.name
                                    dfs.append(type_df)
                            except Exception as e:
                                logger.warning(f"Failed to load {type_dir.name}: {e}")
                    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            elif self.json_store:
                df = self._load_all_from_json(analysis_type)
            else:
                raise ValueError("No storage backend configured")

            if df.empty:
                logger.warning("No data to export")
                return

            # Export to Parquet
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if partition_by and partition_by in df.columns:
                # Partitioned export
                df.to_parquet(
                    output_path,
                    engine="pyarrow",
                    partition_cols=[partition_by],
                    index=False
                )
                logger.info(f"Exported {len(df)} records to partitioned Parquet: {output_path}")
            else:
                # Single file export
                df.to_parquet(output_path, engine="pyarrow", index=False)
                logger.info(f"Exported {len(df)} records to Parquet: {output_path}")

        except Exception as e:
            raise StorageError(f"Failed to export to Parquet: {e}") from e

    def get_summary_stats(self, analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics for stored analyses.

        Args:
            analysis_type: Optional filter for analysis type

        Returns:
            Dictionary with summary statistics
        """
        try:
            if self.parquet_store:
                if analysis_type:
                    df = self.parquet_store.load_dataframe(analysis_type)
                else:
                    dfs = []
                    for type_dir in self.parquet_store.base_dir.iterdir():
                        if type_dir.is_dir():
                            try:
                                type_df = self.parquet_store.load_dataframe(type_dir.name)
                                if not type_df.empty:
                                    type_df["analysis_type"] = type_dir.name
                                    dfs.append(type_df)
                            except Exception:
                                pass
                    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            elif self.json_store:
                df = self._load_all_from_json(analysis_type)
            else:
                return {"error": "No storage backend configured"}

            if df.empty:
                return {"total_records": 0}

            stats = {
                "total_records": len(df),
                "unique_tickers": df["ticker"].nunique() if "ticker" in df.columns else 0,
            }

            if "year" in df.columns:
                stats["year_range"] = f"{df['year'].min()}-{df['year'].max()}"

            if "analysis_type" in df.columns:
                stats["by_type"] = df["analysis_type"].value_counts().to_dict()

            return stats

        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {"error": str(e)}
