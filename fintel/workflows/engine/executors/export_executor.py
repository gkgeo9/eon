#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ExportExecutor - Export results to files.
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import json
import csv
from datetime import datetime

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger


class ExportExecutor(StepExecutor):
    """
    Export results to files.

    Input: DataContainer
    Output: Same DataContainer (pass-through) + exported files

    Config:
        - formats: List["json" | "csv" | "excel" | "pdf"]
        - include_metadata: bool
        - include_raw_data: bool

    The executor exports data to workflows/exports/ directory
    and returns the original data unchanged (pass-through).
    """

    def __init__(self, db, analysis_service=None):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

        # Setup export directory
        from fintel.core import get_config
        config = get_config()
        self.export_dir = config.get_data_path("workflows", "exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data."""
        if input_data is None:
            raise ValueError("ExportExecutor requires input data")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Export results to files.

        Args:
            config: Configuration with formats and options
            input_data: DataContainer to export

        Returns:
            Original input_data (pass-through)
        """
        self.validate_input(input_data)

        formats = config.get('formats', ['json'])
        include_metadata = config.get('include_metadata', True)
        include_raw_data = config.get('include_raw_data', True)

        self.logger.info(f"Exporting to formats: {formats}")

        # Generate base filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"{input_data.step_id}_{timestamp}"

        exported_files = []

        # Export to each format
        for fmt in formats:
            try:
                if fmt.lower() == 'json':
                    file_path = self._export_json(
                        input_data, base_name, include_metadata, include_raw_data
                    )
                    exported_files.append(str(file_path))

                elif fmt.lower() == 'csv':
                    file_path = self._export_csv(input_data, base_name)
                    exported_files.append(str(file_path))

                elif fmt.lower() in ['excel', 'xlsx']:
                    file_path = self._export_excel(input_data, base_name)
                    exported_files.append(str(file_path))

                elif fmt.lower() == 'pdf':
                    self.logger.warning("PDF export not yet implemented")

                else:
                    self.logger.warning(f"Unknown export format: {fmt}")

            except Exception as e:
                self.logger.error(f"Failed to export to {fmt}: {e}")
                input_data.add_error(f"Export to {fmt} failed", {'error': str(e)})

        # Add export metadata to input data
        input_data.metadata['exported_files'] = exported_files
        input_data.metadata['export_timestamp'] = datetime.now().isoformat()

        self.logger.info(f"Exported to {len(exported_files)} files: {exported_files}")

        # Return original data (pass-through)
        return input_data

    def _export_json(
        self,
        input_data: DataContainer,
        base_name: str,
        include_metadata: bool,
        include_raw_data: bool
    ) -> Path:
        """Export to JSON file."""
        file_path = self.export_dir / f"{base_name}.json"

        # Build export data
        export_data = {
            'step_id': input_data.step_id,
            'step_type': input_data.step_type,
            'shape': input_data.shape,
            'total_items': input_data.total_items,
            'exported_at': datetime.now().isoformat()
        }

        if include_metadata:
            export_data['metadata'] = input_data.metadata
            export_data['source_run_ids'] = input_data.source_run_ids
            export_data['errors'] = input_data.errors
            export_data['warnings'] = input_data.warnings

        if include_raw_data:
            export_data['data'] = input_data._serialize_data()

        # Write to file
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        self.logger.info(f"Exported JSON: {file_path}")
        return file_path

    def _export_csv(self, input_data: DataContainer, base_name: str) -> Path:
        """Export to CSV file (flattened)."""
        file_path = self.export_dir / f"{base_name}.csv"

        # Flatten data to rows
        rows = []
        headers = ['ticker', 'year', 'step_id', 'step_type']

        for ticker in input_data.tickers:
            for year in input_data.get_years_for_ticker(ticker):
                data = input_data.data[ticker][year]

                if data is None:
                    continue

                row = {
                    'ticker': ticker,
                    'year': year,
                    'step_id': input_data.step_id,
                    'step_type': input_data.step_type
                }

                # Add data fields (simplified - just top-level fields)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (str, int, float, bool)):
                            row[key] = value
                            if key not in headers:
                                headers.append(key)

                rows.append(row)

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        self.logger.info(f"Exported CSV: {file_path} ({len(rows)} rows)")
        return file_path

    def _export_excel(self, input_data: DataContainer, base_name: str) -> Path:
        """Export to Excel file."""
        file_path = self.export_dir / f"{base_name}.xlsx"

        try:
            import pandas as pd

            # Create DataFrame (similar to CSV)
            rows = []

            for ticker in input_data.tickers:
                for year in input_data.get_years_for_ticker(ticker):
                    data = input_data.data[ticker][year]

                    if data is None:
                        continue

                    row = {
                        'ticker': ticker,
                        'year': year,
                        'step_id': input_data.step_id,
                        'step_type': input_data.step_type
                    }

                    # Add data fields
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (str, int, float, bool)):
                                row[key] = value

                    rows.append(row)

            df = pd.DataFrame(rows)

            # Write Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)

                # Add metadata sheet
                metadata_df = pd.DataFrame([{
                    'step_id': input_data.step_id,
                    'step_type': input_data.step_type,
                    'shape': str(input_data.shape),
                    'total_items': input_data.total_items,
                    'exported_at': datetime.now().isoformat()
                }])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)

            self.logger.info(f"Exported Excel: {file_path} ({len(rows)} rows)")

        except ImportError:
            self.logger.error("pandas or openpyxl not installed - cannot export to Excel")
            raise

        return file_path

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output shape is same as input (pass-through)."""
        return input_shape if input_shape else (0, 0)
