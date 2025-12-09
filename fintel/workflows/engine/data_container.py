#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DataContainer - Wrapper for workflow data with shape tracking and metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json


@dataclass
class DataContainer:
    """
    Wrapper for data flowing between workflow steps.

    Tracks data shape (companies × years), provides metadata,
    and maintains lineage through analysis run IDs.

    Data Structure:
        data: Dict[ticker, Dict[year, analysis_result]]

    Example:
        {
            "AAPL": {
                2024: TenKAnalysis(...),
                2023: TenKAnalysis(...),
                2022: TenKAnalysis(...)
            },
            "MSFT": {
                2024: TenKAnalysis(...),
                2023: TenKAnalysis(...)
            }
        }

    Shape Tracking:
        - (num_companies, max_years) represents the data dimensions
        - num_years_per_company may vary per company
        - total_items counts actual data points (excludes None values)
    """

    # Core data
    data: Dict[str, Dict[Any, Any]]  # ticker -> year/key -> result

    # Shape tracking
    num_companies: int
    num_years_per_company: Dict[str, int]  # ticker -> year count

    # Metadata
    step_id: str
    step_type: str
    created_at: datetime = field(default_factory=datetime.now)

    # Lineage tracking
    source_run_ids: List[str] = field(default_factory=list)

    # Error and warning tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def shape(self) -> Tuple[int, int]:
        """
        Returns (num_companies, max_years).

        This represents the maximum dimensions of the data,
        though some cells may be None.
        """
        max_years = max(self.num_years_per_company.values()) if self.num_years_per_company else 0
        return (self.num_companies, max_years)

    @property
    def total_items(self) -> int:
        """
        Total number of actual data items (excludes None values).

        This is the count of cells that have actual results,
        not just the theoretical maximum from shape.
        """
        count = 0
        for ticker, years_dict in self.data.items():
            for year, value in years_dict.items():
                if value is not None:
                    count += 1
        return count

    @property
    def tickers(self) -> List[str]:
        """Get list of all tickers in this container."""
        return list(self.data.keys())

    def get_years_for_ticker(self, ticker: str) -> List[Any]:
        """Get all years/keys for a specific ticker."""
        if ticker in self.data:
            return list(self.data[ticker].keys())
        return []

    def get_all_years(self) -> List[Any]:
        """Get all unique years across all tickers."""
        all_years = set()
        for ticker, years_dict in self.data.items():
            all_years.update(years_dict.keys())
        return sorted(list(all_years))

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Note: The actual data values may need special handling
        if they're Pydantic models or other complex types.
        """
        return {
            'data': self._serialize_data(),
            'num_companies': self.num_companies,
            'num_years_per_company': self.num_years_per_company,
            'step_id': self.step_id,
            'step_type': self.step_type,
            'created_at': self.created_at.isoformat(),
            'source_run_ids': self.source_run_ids,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata,
            'shape': self.shape,
            'total_items': self.total_items
        }

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize the data dictionary, handling Pydantic models.

        Converts Pydantic models to dicts via model_dump().
        """
        serialized = {}
        for ticker, years_dict in self.data.items():
            serialized[ticker] = {}
            for year, value in years_dict.items():
                if value is None:
                    serialized[ticker][str(year)] = None
                elif hasattr(value, 'model_dump'):
                    # Pydantic model
                    serialized[ticker][str(year)] = {
                        '__type__': type(value).__name__,
                        '__data__': value.model_dump()
                    }
                elif isinstance(value, dict):
                    serialized[ticker][str(year)] = value
                else:
                    # Try to convert to dict
                    serialized[ticker][str(year)] = str(value)
        return serialized

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataContainer':
        """
        Deserialize from dictionary.

        Note: This creates a basic DataContainer with dict data.
        To reconstruct Pydantic models, you'd need to pass
        the model classes or use a registry.
        """
        return cls(
            data=data.get('data', {}),
            num_companies=data.get('num_companies', 0),
            num_years_per_company=data.get('num_years_per_company', {}),
            step_id=data.get('step_id', ''),
            step_type=data.get('step_type', ''),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            source_run_ids=data.get('source_run_ids', []),
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            metadata=data.get('metadata', {})
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'DataContainer':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Add a warning to the container."""
        self.warnings.append({
            'message': message,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        })

    def add_error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Add an error to the container."""
        self.errors.append({
            'message': message,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        })

    def __repr__(self) -> str:
        return (
            f"DataContainer(step={self.step_id}, "
            f"shape={self.shape}, "
            f"items={self.total_items}, "
            f"tickers={len(self.tickers)})"
        )
