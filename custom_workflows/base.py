#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base class for custom analysis workflows.

To create a custom workflow:
1. Create a new .py file in the custom_workflows/ folder
2. Subclass CustomWorkflow
3. Define your prompt and schema
4. The workflow will be automatically discovered and appear in the UI
"""

from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel


class CustomWorkflow(ABC):
    """
    Base class for custom analysis workflows.

    Each custom workflow defines:
    - name: Display name in the UI
    - description: Help text for the user
    - icon: Emoji for UI display
    - min_years: Minimum years required (1 for single-year, 3+ for multi-year)
    - prompt_template: The analysis prompt with {ticker} and {year} placeholders
    - schema: Pydantic model for structured output
    """

    # Required class attributes - override in subclasses
    name: str = "Custom Workflow"
    description: str = "A custom analysis workflow"
    icon: str = "🔧"
    min_years: int = 1
    category: str = "custom"

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """
        Return the prompt template for this workflow.

        Use {ticker} and {year} as placeholders.
        The filing content will be appended automatically.

        Example:
            return '''
            You are analyzing {ticker} for fiscal year {year}.
            Focus on identifying key growth drivers and risks.
            '''
        """
        pass

    @property
    @abstractmethod
    def schema(self) -> Type[BaseModel]:
        """
        Return the Pydantic schema for structured output.

        The schema should define all fields you want extracted from the analysis.
        Use Field() with descriptions for best results.

        Example:
            class MyAnalysisResult(BaseModel):
                summary: str = Field(description="Brief summary of findings")
                key_points: List[str] = Field(description="Top 3-5 key points")
                score: int = Field(ge=0, le=100, description="Overall score 0-100")

            @property
            def schema(self):
                return MyAnalysisResult
        """
        pass

    def validate_config(self, years: int) -> bool:
        """
        Validate that the workflow can run with given config.

        Args:
            years: Number of years selected

        Returns:
            True if valid, raises ValueError otherwise
        """
        if years < self.min_years:
            raise ValueError(
                f"{self.name} requires at least {self.min_years} years, "
                f"but only {years} selected"
            )
        return True
