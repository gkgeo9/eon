#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CustomPromptExecutor - Run custom prompt on aggregated data.
"""

from typing import Dict, Any, Optional, Tuple
import json

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger
from fintel.ai.providers.gemini import GeminiProvider


class CustomPromptExecutor(StepExecutor):
    """
    Run custom prompt on aggregated data.

    Input: DataContainer (any shape)
    Output: DataContainer (potentially different shape)

    Config:
        - prompt: str (can reference {company_data})
        - output_format: "structured_json" | "free_text" | "comparison_table"

    This executor allows arbitrary LLM prompts to process workflow data.
    """

    def __init__(self, db, analysis_service):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

        if not analysis_service:
            raise ValueError("CustomPromptExecutor requires AnalysisService")

        # Create AI provider
        api_key = analysis_service.api_key_manager.get_next_key()
        self.provider = GeminiProvider(
            api_key=api_key,
            rate_limiter=analysis_service.rate_limiter
        )

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data."""
        if input_data is None:
            raise ValueError("CustomPromptExecutor requires input data")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Run custom prompt on input data.

        Args:
            config: Configuration with prompt and output_format
            input_data: DataContainer with previous step results

        Returns:
            DataContainer with custom prompt results
        """
        self.validate_input(input_data)

        prompt_template = config.get('prompt', '')
        output_format = config.get('output_format', 'free_text')

        if not prompt_template:
            raise ValueError("No prompt provided in configuration")

        self.logger.info(f"Running custom prompt: format={output_format}")

        # Format input data for the prompt
        company_data = self._format_data(input_data)

        # Replace placeholder
        prompt = prompt_template.replace('{company_data}', company_data)

        # Add format instructions
        if output_format == 'structured_json':
            prompt += "\n\nProvide your response as a valid JSON object."
        elif output_format == 'comparison_table':
            prompt += "\n\nProvide your response as a markdown table."

        self.logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            # Build full prompt with system context
            full_prompt = f"""You are an expert financial analyst.

{prompt}"""

            # Call LLM
            response = self.provider.generate(
                prompt=full_prompt,
                temperature=0.3
            )

            # Parse response based on format
            # Note: provider.generate() already returns a dict when no schema is provided
            if output_format == 'structured_json':
                if isinstance(response, dict):
                    parsed_response = response
                else:
                    # Fallback if response is still a string
                    try:
                        parsed_response = json.loads(response)
                    except json.JSONDecodeError:
                        # Try to extract JSON from markdown code blocks
                        if '```json' in response:
                            json_str = response.split('```json')[1].split('```')[0].strip()
                            parsed_response = json.loads(json_str)
                        elif '```' in response:
                            json_str = response.split('```')[1].split('```')[0].strip()
                            parsed_response = json.loads(json_str)
                        else:
                            parsed_response = {'raw_text': response}
            else:
                if isinstance(response, dict):
                    parsed_response = response
                else:
                    parsed_response = {'text': response}

            # Store result under special key
            results = {
                'CUSTOM_ANALYSIS': {
                    0: parsed_response
                }
            }

            # Create output container
            output = DataContainer(
                data=results,
                num_companies=1,
                num_years_per_company={'CUSTOM_ANALYSIS': 1},
                step_id=config.get('step_id', 'custom_1'),
                step_type='custom_analysis',
                source_run_ids=input_data.source_run_ids,
                metadata={
                    'prompt_length': len(prompt),
                    'output_format': output_format,
                    'input_step': input_data.step_id,
                    'input_shape': input_data.shape
                }
            )

            self.logger.info("Custom prompt analysis complete")

            return output

        except Exception as e:
            self.logger.error(f"Failed to run custom prompt: {e}")
            raise RuntimeError(f"Custom prompt execution failed: {e}")

    def _format_data(self, input_data: DataContainer) -> str:
        """
        Format input data as a readable string for the prompt.

        Args:
            input_data: DataContainer to format

        Returns:
            Formatted string representation
        """
        lines = []
        lines.append(f"Data from step: {input_data.step_id}")
        lines.append(f"Shape: {input_data.shape[0]} companies × {input_data.shape[1]} years")
        lines.append(f"Total items: {input_data.total_items}")
        lines.append("")

        # Format each company's data
        for ticker in input_data.tickers:
            lines.append(f"## {ticker}")

            for year in sorted(input_data.get_years_for_ticker(ticker), reverse=True):
                data = input_data.data[ticker][year]

                if data is None:
                    lines.append(f"  {year}: No data")
                    continue

                lines.append(f"  ### Year {year}")

                # Format based on data type
                if isinstance(data, dict):
                    # Pretty print dict
                    data_str = json.dumps(data, indent=4)
                    lines.append(f"  {data_str}")
                else:
                    # Convert to string
                    lines.append(f"  {str(data)}")

            lines.append("")

        return "\n".join(lines)

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output is typically (1, 1) - single aggregated result."""
        return (1, 1)
