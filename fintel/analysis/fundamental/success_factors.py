#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-year success factor analysis for companies.

Analyzes multiple 10-K filings across years to identify patterns,
success factors, and strategic evolution.

CRITICAL: Provides TWO analysis paths:
1. ExcellentCompanyAnalyzer - For known successful companies (success-focused)
2. ObjectiveCompanyAnalyzer - For random/unknown companies (balanced/neutral)

This distinction is CRUCIAL for comparative analysis:
- Excellent companies analyzed with success-bias → stored in excellent_company_factors/
- Random companies analyzed objectively → stored in random_company_factors/

Extracted from 10K_automator/
- analyze_30_outputs_for_excellent_companies.py (success-focused)
- analyze_30_outputs_for_random_companies.py (objective)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Type
from pydantic import BaseModel

from fintel.core import get_logger, get_config, AnalysisError, mask_api_key
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers import GeminiProvider
from .models.success_factors import CompanySuccessFactors
from .models.excellent_company_factors import ExcellentCompanyFactors
from .prompts.success_factors import SUCCESS_FACTORS_PROMPT
from .prompts.excellent_company_factors import EXCELLENT_COMPANY_PROMPT


class _BaseSuccessAnalyzer:
    """
    Base class for multi-year success factor analysis.

    Provides shared functionality for both excellent and objective analysis.
    Subclasses specify the prompt template and output model.
    """

    # Subclasses must override these
    PROMPT_TEMPLATE: str = None
    OUTPUT_MODEL: Type[BaseModel] = None
    DEFAULT_OUTPUT_DIR: str = None

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        model: str = None,
        thinking_budget: int = None
    ):
        """
        Initialize the success factor analyzer.

        Args:
            api_key_manager: Manager for API key rotation
            rate_limiter: Rate limiter for API calls
            model: LLM model name (default from config)
            thinking_budget: Thinking budget (default from config)
        """
        self.api_key_manager = api_key_manager
        self.rate_limiter = rate_limiter

        # Load configuration
        config = get_config()
        self.model = model or config.default_model
        # CRITICAL: Use 4096 thinking budget for deep multi-year analysis (from 10K_automator)
        self.thinking_budget = thinking_budget or 4096

        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def analyze_success_factors(
        self,
        ticker: str,
        analyses: Dict[int, BaseModel],
        output_file: Optional[Path] = None
    ) -> Optional[Union[CompanySuccessFactors, ExcellentCompanyFactors]]:
        """
        Analyze multi-year data to identify success factors.

        Args:
            ticker: Company ticker symbol
            analyses: Dictionary mapping year to TenKAnalysis
                     {2024: TenKAnalysis(...), 2023: TenKAnalysis(...), ...}
            output_file: Optional path to save JSON results

        Returns:
            Success factors model (type depends on subclass)

        Raises:
            AnalysisError: If analysis fails
        """
        if not analyses:
            raise AnalysisError("No analyses provided")

        self.logger.info(
            f"Analyzing success factors for {ticker} across {len(analyses)} years"
        )

        try:
            # Prepare data for AI analysis
            company_data = self._prepare_company_data(ticker, analyses)

            # Construct prompt
            prompt = self._construct_prompt(ticker, company_data)

            # Run AI analysis
            result = self._analyze_with_ai(prompt)

            # Save results if requested
            if output_file and result:
                self._save_result(result, output_file)

            return result

        except Exception as e:
            error_msg = f"Success factor analysis failed for {ticker}: {e}"
            self.logger.error(error_msg)
            raise AnalysisError(error_msg) from e

    def analyze_from_directory(
        self,
        ticker: str,
        analyses_dir: Path,
        output_dir: Optional[Path] = None
    ) -> Optional[Union[CompanySuccessFactors, ExcellentCompanyFactors]]:
        """
        Load analyses from directory and run success factor analysis.

        Args:
            ticker: Company ticker
            analyses_dir: Directory containing {ticker}_{year}_analysis.json files
            output_dir: Output directory (uses default if not specified)

        Returns:
            Success factors model
        """
        # Load analyses from directory
        analyses = self.load_analyses_from_directory(analyses_dir, ticker)

        if not analyses:
            raise AnalysisError(f"No analyses found for {ticker} in {analyses_dir}")

        # Determine output file
        if output_dir:
            output_file = output_dir / f"{ticker}_success_factors.json"
        elif self.DEFAULT_OUTPUT_DIR:
            output_file = Path(self.DEFAULT_OUTPUT_DIR) / f"{ticker}_success_factors.json"
        else:
            output_file = Path(f"{ticker}_success_factors.json")

        # Run analysis
        return self.analyze_success_factors(ticker, analyses, output_file)

    def load_analyses_from_directory(
        self,
        directory: Path,
        ticker: str
    ) -> Dict[int, Dict]:
        """
        Load all analysis JSON files from a directory.

        Args:
            directory: Directory containing {ticker}_{year}_analysis.json files
            ticker: Company ticker to filter files

        Returns:
            Dictionary mapping year to analysis dict
        """
        self.logger.info(f"Loading analyses from {directory}")

        analyses = {}
        pattern = f"{ticker}_*_analysis.json"

        for file_path in directory.glob(pattern):
            try:
                with open(file_path, 'r') as f:
                    analysis = json.load(f)

                # Extract year from filename
                # Format: TICKER_YEAR_analysis.json
                year_str = file_path.stem.split('_')[1]
                year = int(year_str)

                analyses[year] = analysis
                self.logger.debug(f"Loaded analysis for year {year}")

            except Exception as e:
                self.logger.warning(f"Failed to load {file_path.name}: {e}")

        if analyses:
            self.logger.info(f"Loaded {len(analyses)} analyses for {ticker}")
        else:
            self.logger.warning(f"No analyses found for {ticker} in {directory}")

        return analyses

    def _prepare_company_data(
        self,
        ticker: str,
        analyses: Dict[int, BaseModel]
    ) -> Dict:
        """
        Prepare company data structure for AI analysis.

        Args:
            ticker: Company ticker
            analyses: Dictionary of year to analysis models

        Returns:
            Structured data for prompt
        """
        # Sort years in descending order (newest first)
        sorted_years = sorted(analyses.keys(), reverse=True)

        analyses_list = []
        for year in sorted_years:
            analysis = analyses[year]

            # Convert Pydantic model to dict if needed
            if isinstance(analysis, BaseModel):
                analysis_dict = analysis.model_dump()
            else:
                analysis_dict = analysis

            analyses_list.append({
                "year": str(year),
                "analysis": analysis_dict
            })

        return {
            "company_name": ticker,
            "analyses": analyses_list
        }

    def _construct_prompt(self, ticker: str, company_data: Dict) -> str:
        """
        Construct prompt for success factor analysis.

        Args:
            ticker: Company ticker
            company_data: Prepared company data

        Returns:
            Complete prompt string
        """
        if not self.PROMPT_TEMPLATE:
            raise ValueError("PROMPT_TEMPLATE not set in subclass")

        years = [a["year"] for a in company_data["analyses"]]
        years_str = ", ".join(years)

        # Format template using the prompt from subclass
        formatted_prompt = self.PROMPT_TEMPLATE.format(
            company_name=ticker,
            years_str=years_str
        )

        # Append company data as JSON
        company_data_json = json.dumps(company_data, indent=2)

        full_prompt = (
            f"{formatted_prompt}\n\n"
            f"Here's the combined 10-K analyses to analyze:\n\n"
            f"{company_data_json}"
        )

        return full_prompt

    def _analyze_with_ai(
        self,
        prompt: str
    ) -> Optional[Union[CompanySuccessFactors, ExcellentCompanyFactors]]:
        """
        Run AI analysis to identify success factors.

        Args:
            prompt: Complete prompt with data

        Returns:
            Success factors model (type from OUTPUT_MODEL)
        """
        if not self.OUTPUT_MODEL:
            raise ValueError("OUTPUT_MODEL not set in subclass")

        # Reserve a key atomically to prevent race conditions in batch processing
        api_key = self.api_key_manager.reserve_key()

        if api_key is None:
            raise AnalysisError(
                "No API keys available! All keys are either in use by other threads "
                "or have reached their daily limits."
            )

        try:
            masked_key = mask_api_key(api_key)
            self.logger.debug(f"Using reserved API key: {masked_key}")

            # Create provider with rate limiter
            provider = GeminiProvider(
                api_key=api_key,
                model=self.model,
                thinking_budget=self.thinking_budget,
                rate_limiter=self.rate_limiter
            )

            # Generate with structured output
            result = provider.generate_with_retry(
                prompt=prompt,
                schema=self.OUTPUT_MODEL,
                max_retries=3,
                retry_delay=10
            )

            # Record usage
            self.api_key_manager.record_usage(api_key)

            return result

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            raise AnalysisError(f"AI analysis failed: {e}") from e

        finally:
            # Always release the key, even on error
            self.api_key_manager.release_key(api_key)

    def _save_result(
        self,
        result: Union[CompanySuccessFactors, ExcellentCompanyFactors],
        output_file: Path
    ):
        """
        Save success factors analysis to JSON.

        Args:
            result: Success factors model
            output_file: Path to save to
        """
        try:
            # Create output directory
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict and save
            result_dict = result.model_dump()

            with open(output_file, 'w') as f:
                json.dump(result_dict, f, indent=2)

            self.logger.info(f"Saved success factors to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save result: {e}")


class ExcellentCompanyAnalyzer(_BaseSuccessAnalyzer):
    """
    Analyzer for KNOWN SUCCESSFUL companies.

    Uses SUCCESS-FOCUSED prompt that assumes the company was successful
    and identifies what made it succeed.

    Use for:
    - Top 50 compounders
    - Known high performers
    - Companies you want to learn success patterns from

    Output directory: excellent_company_factors/

    Example:
        analyzer = ExcellentCompanyAnalyzer(key_mgr, rate_limiter)

        # Analyze a known successful company
        result = analyzer.analyze_from_directory(
            ticker="AAPL",
            analyses_dir=Path("analyzed_10k/AAPL"),
            output_dir=Path("excellent_company_factors")
        )

        # Access unique success attributes
        print(result.unique_attributes)
    """

    PROMPT_TEMPLATE = EXCELLENT_COMPANY_PROMPT
    OUTPUT_MODEL = ExcellentCompanyFactors
    DEFAULT_OUTPUT_DIR = "excellent_company_factors"


class ObjectiveCompanyAnalyzer(_BaseSuccessAnalyzer):
    """
    Analyzer for RANDOM/UNKNOWN companies.

    Uses OBJECTIVE/BALANCED prompt that doesn't assume success or failure.
    Identifies both strengths and weaknesses with equal attention.

    Use for:
    - Random companies you're researching
    - Companies with unknown track record
    - Unbiased pattern identification

    Output directory: random_company_factors/

    Example:
        analyzer = ObjectiveCompanyAnalyzer(key_mgr, rate_limiter)

        # Analyze an unknown company objectively
        result = analyzer.analyze_from_directory(
            ticker="XYZ",
            analyses_dir=Path("analyzed_10k/XYZ"),
            output_dir=Path("random_company_factors")
        )

        # Access balanced assessment
        print(result.distinguishing_characteristics)
    """

    PROMPT_TEMPLATE = SUCCESS_FACTORS_PROMPT
    OUTPUT_MODEL = CompanySuccessFactors
    DEFAULT_OUTPUT_DIR = "random_company_factors"


# Backwards compatibility alias
CompanySuccessAnalyzer = ObjectiveCompanyAnalyzer


__all__ = [
    'ExcellentCompanyAnalyzer',
    'ObjectiveCompanyAnalyzer',
    'CompanySuccessAnalyzer',  # Backwards compatibility
]
