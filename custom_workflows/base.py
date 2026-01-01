#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base class for custom analysis workflows.

To create a custom workflow:
1. Create a new .py file in the custom_workflows/ folder
2. Subclass CustomWorkflow
3. Define your prompt and schema
4. The workflow will be automatically discovered and appear in the UI

See docs/CUSTOM_WORKFLOWS.md for detailed documentation.
"""

from abc import ABC, abstractmethod
from typing import Type, List, Optional
from pydantic import BaseModel
import re


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails."""

    def __init__(self, message: str, workflow_name: str, suggestions: Optional[List[str]] = None):
        self.workflow_name = workflow_name
        self.suggestions = suggestions or []
        super().__init__(message)

    def __str__(self):
        msg = f"[{self.workflow_name}] {super().__str__()}"
        if self.suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(f"  - {s}" for s in self.suggestions)
        return msg


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

    See docs/CUSTOM_WORKFLOWS.md for detailed documentation and examples.
    """

    # Required class attributes - override in subclasses
    name: str = "Custom Workflow"
    description: str = "A custom analysis workflow"
    icon: str = "🔧"
    min_years: int = 1
    category: str = "custom"
    max_years: int = 10  # Optional maximum years

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
            True if valid, raises WorkflowValidationError otherwise
        """
        if years < self.min_years:
            raise WorkflowValidationError(
                f"Requires at least {self.min_years} year(s), but only {years} selected.",
                workflow_name=self.name,
                suggestions=[
                    f"Select {self.min_years} or more years in the analysis settings",
                    "Choose a different workflow that works with fewer years"
                ]
            )

        if years > self.max_years:
            raise WorkflowValidationError(
                f"Supports at most {self.max_years} years, but {years} selected.",
                workflow_name=self.name,
                suggestions=[
                    f"Select {self.max_years} or fewer years",
                    "Consider splitting into multiple analyses"
                ]
            )

        return True

    def validate_workflow(self) -> List[str]:
        """
        Validate the workflow definition itself.

        Returns:
            List of warning messages (empty if all good)

        Raises:
            WorkflowValidationError: If critical issues found
        """
        warnings = []
        errors = []

        # Validate name
        if not self.name or self.name == "Custom Workflow":
            errors.append("Workflow 'name' is not set or uses default value")

        if len(self.name) > 50:
            warnings.append(f"Workflow name is too long ({len(self.name)} chars). Keep under 50.")

        # Validate description
        if not self.description or self.description == "A custom analysis workflow":
            warnings.append("Consider adding a meaningful 'description' for the UI")

        # Validate icon
        if not self.icon:
            warnings.append("No icon set. Add an emoji for better UI display.")

        # Validate prompt template
        try:
            prompt = self.prompt_template
            if not prompt:
                errors.append("prompt_template is empty")
            else:
                # Check for required placeholders
                if "{ticker}" not in prompt:
                    errors.append("prompt_template must contain {ticker} placeholder")
                if "{year}" not in prompt:
                    errors.append("prompt_template must contain {year} placeholder")

                # Check for unescaped braces (common mistake)
                # Find all {...} that aren't {ticker} or {year}
                pattern = r'\{(?!ticker\}|year\})[^}]*\}'
                bad_braces = re.findall(pattern, prompt)
                if bad_braces:
                    warnings.append(
                        f"Possible unescaped braces in prompt: {bad_braces[:3]}... "
                        "Use {{ and }} to escape braces in examples."
                    )

                # Check prompt length
                if len(prompt) > 10000:
                    warnings.append(
                        f"Prompt is very long ({len(prompt)} chars). "
                        "Consider shortening for better results."
                    )
                elif len(prompt) < 100:
                    warnings.append(
                        "Prompt is very short. Consider adding more detailed instructions."
                    )

        except Exception as e:
            errors.append(f"Error accessing prompt_template: {e}")

        # Validate schema
        try:
            schema = self.schema
            if schema is None:
                errors.append("schema property returns None")
            elif not issubclass(schema, BaseModel):
                errors.append(f"schema must be a Pydantic BaseModel subclass, got {type(schema)}")
            else:
                # Check schema fields have descriptions
                fields_without_desc = []
                for field_name, field_info in schema.model_fields.items():
                    if not field_info.description:
                        fields_without_desc.append(field_name)

                if fields_without_desc:
                    warnings.append(
                        f"Schema fields without descriptions: {fields_without_desc}. "
                        "Add Field(description='...') for better AI output."
                    )

        except Exception as e:
            errors.append(f"Error accessing schema: {e}")

        # Raise if critical errors
        if errors:
            raise WorkflowValidationError(
                f"Workflow has {len(errors)} critical error(s):\n" +
                "\n".join(f"  - {e}" for e in errors),
                workflow_name=self.name,
                suggestions=[
                    "Review the workflow definition in your Python file",
                    "See docs/CUSTOM_WORKFLOWS.md for examples"
                ]
            )

        return warnings

    def get_estimated_tokens(self) -> int:
        """
        Estimate token count for the prompt template.

        Useful for API cost estimation.

        Returns:
            Estimated token count (rough: chars/4)
        """
        return len(self.prompt_template) // 4

    def format_prompt(self, ticker: str, year: int) -> str:
        """
        Format the prompt template with actual values.

        Args:
            ticker: Company ticker symbol
            year: Fiscal year

        Returns:
            Formatted prompt string
        """
        return self.prompt_template.format(ticker=ticker, year=year)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', min_years={self.min_years})"
