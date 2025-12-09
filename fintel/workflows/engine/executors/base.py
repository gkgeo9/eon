#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
StepExecutor - Base class for all workflow step executors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from ..data_container import DataContainer


class StepExecutor(ABC):
    """
    Base class for workflow step executors.

    Each step executor implements the logic for one type of workflow step
    (e.g., fundamental analysis, filtering, aggregation).

    All executors must:
    1. Validate input data shape and type
    2. Execute the step logic
    3. Return output in a DataContainer
    4. Predict output shape from input shape
    """

    def __init__(self, db, analysis_service=None):
        """
        Initialize executor.

        Args:
            db: DatabaseRepository instance
            analysis_service: Optional AnalysisService for analysis executors
        """
        self.db = db
        self.analysis_service = analysis_service

    @abstractmethod
    def execute(self, config: Dict[str, Any], input_data: Optional[DataContainer]) -> DataContainer:
        """
        Execute the step logic.

        Args:
            config: Step configuration dictionary
            input_data: Input DataContainer (None for first step)

        Returns:
            Output DataContainer with results

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If execution fails
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """
        Validate that input data is compatible with this step.

        Args:
            input_data: Input DataContainer (None for first step)

        Returns:
            True if input is valid

        Raises:
            ValueError: If input is invalid (with descriptive message)
        """
        pass

    @abstractmethod
    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """
        Calculate expected output shape from input shape.

        Args:
            input_shape: (num_companies, num_years) or None for first step

        Returns:
            Expected (num_companies, num_years) after this step
        """
        pass

    def get_step_type(self) -> str:
        """Return the step type identifier."""
        return self.__class__.__name__.replace('Executor', '').lower()
