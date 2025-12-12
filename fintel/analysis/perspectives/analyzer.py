#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-perspective investment analysis using different investment philosophies.

Analyzes companies through:
- Warren Buffett (value, moat, management)
- Nassim Taleb (fragility, tail risks, antifragility)
- Contrarian View (variant perception)
"""

from pathlib import Path
from typing import Optional, Union, Dict
from pydantic import BaseModel

from fintel.core import get_logger, get_config, AnalysisError
from fintel.data.sources.sec import PDFExtractor
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers import GeminiProvider
from fintel.ai.prompts.perspectives import (
    MULTI_PERSPECTIVE_PROMPT,
    BUFFETT_PROMPT,
    TALEB_PROMPT,
    CONTRARIAN_PROMPT,
    format_perspective_prompt
)
from .schemas import (
    BuffettAnalysis,
    TalebAnalysis,
    ContrarianAnalysis,
    SimplifiedAnalysis
)


class PerspectiveAnalyzer:
    """
    Analyzes companies through multiple investment philosophy lenses.

    Can analyze through:
    - Individual perspectives (Buffett, Taleb, Contrarian)
    - All perspectives combined (SimplifiedAnalysis)

    Example:
        analyzer = PerspectiveAnalyzer(key_mgr, rate_limiter)

        # Analyze with all perspectives
        result = analyzer.analyze_multi_perspective(
            pdf_path=Path("AAPL_10-K_2024.pdf"),  # or "AAPL_DEF_14A_2024.pdf", etc.
            ticker="AAPL",
            year=2024
        )

        # Or analyze single perspective
        buffett_view = analyzer.analyze_buffett(
            pdf_path=Path("AAPL_10-K_2024.pdf"),  # or any filing type
            ticker="AAPL",
            year=2024
        )
    """

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        model: str = None,
        thinking_budget: int = None
    ):
        """
        Initialize the perspective analyzer.

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
        self.thinking_budget = thinking_budget or config.thinking_budget

        # Initialize PDF extractor
        self.pdf_extractor = PDFExtractor()

        self.logger = get_logger(f"{__name__}.PerspectiveAnalyzer")

    def analyze_multi_perspective(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        output_dir: Optional[Path] = None
    ) -> Optional[SimplifiedAnalysis]:
        """
        Analyze through all three perspectives (Buffett, Taleb, Contrarian).

        Args:
            pdf_path: Path to PDF file
            ticker: Company ticker
            year: Fiscal year
            output_dir: Optional directory to save JSON results

        Returns:
            SimplifiedAnalysis with all three perspectives

        Raises:
            AnalysisError: If analysis fails
        """
        self.logger.info(
            f"Analyzing {ticker} {year} through multi-perspective lens"
        )

        return self._analyze_with_perspective(
            pdf_path=pdf_path,
            ticker=ticker,
            year=year,
            prompt_template=MULTI_PERSPECTIVE_PROMPT,
            schema=SimplifiedAnalysis,
            output_dir=output_dir,
            perspective_name="multi"
        )

    def analyze_buffett(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        output_dir: Optional[Path] = None
    ) -> Optional[BuffettAnalysis]:
        """
        Analyze through Warren Buffett's value investing lens.

        Args:
            pdf_path: Path to PDF file
            ticker: Company ticker
            year: Fiscal year
            output_dir: Optional directory to save JSON results

        Returns:
            BuffettAnalysis model

        Raises:
            AnalysisError: If analysis fails
        """
        self.logger.info(f"Analyzing {ticker} {year} through Buffett lens")

        return self._analyze_with_perspective(
            pdf_path=pdf_path,
            ticker=ticker,
            year=year,
            prompt_template=BUFFETT_PROMPT,
            schema=BuffettAnalysis,
            output_dir=output_dir,
            perspective_name="buffett"
        )

    def analyze_taleb(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        output_dir: Optional[Path] = None
    ) -> Optional[TalebAnalysis]:
        """
        Analyze through Nassim Taleb's antifragility lens.

        Args:
            pdf_path: Path to PDF file
            ticker: Company ticker
            year: Fiscal year
            output_dir: Optional directory to save JSON results

        Returns:
            TalebAnalysis model

        Raises:
            AnalysisError: If analysis fails
        """
        self.logger.info(f"Analyzing {ticker} {year} through Taleb lens")

        return self._analyze_with_perspective(
            pdf_path=pdf_path,
            ticker=ticker,
            year=year,
            prompt_template=TALEB_PROMPT,
            schema=TalebAnalysis,
            output_dir=output_dir,
            perspective_name="taleb"
        )

    def analyze_contrarian(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        output_dir: Optional[Path] = None
    ) -> Optional[ContrarianAnalysis]:
        """
        Analyze through a contrarian/variant perception lens.

        Args:
            pdf_path: Path to PDF file
            ticker: Company ticker
            year: Fiscal year
            output_dir: Optional directory to save JSON results

        Returns:
            ContrarianAnalysis model

        Raises:
            AnalysisError: If analysis fails
        """
        self.logger.info(f"Analyzing {ticker} {year} through Contrarian lens")

        return self._analyze_with_perspective(
            pdf_path=pdf_path,
            ticker=ticker,
            year=year,
            prompt_template=CONTRARIAN_PROMPT,
            schema=ContrarianAnalysis,
            output_dir=output_dir,
            perspective_name="contrarian"
        )

    def _analyze_with_perspective(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        prompt_template: str,
        schema: type[BaseModel],
        output_dir: Optional[Path],
        perspective_name: str
    ) -> Optional[BaseModel]:
        """
        Core analysis method for any perspective.

        Args:
            pdf_path: Path to PDF
            ticker: Company ticker
            year: Fiscal year
            prompt_template: Prompt template to use
            schema: Pydantic schema for output
            output_dir: Optional output directory
            perspective_name: Name of perspective (for logging/output)

        Returns:
            Analysis result as Pydantic model

        Raises:
            AnalysisError: If analysis fails
        """
        try:
            # Extract text from PDF
            self.logger.debug("Extracting text from PDF")
            text = self.pdf_extractor.extract_text(pdf_path)

            if not text or len(text.strip()) < 100:
                raise AnalysisError(
                    f"PDF extraction failed or insufficient text "
                    f"({len(text) if text else 0} chars)"
                )

            # Construct prompt
            self.logger.debug("Constructing prompt")
            formatted_prompt = format_perspective_prompt(
                prompt_template, ticker, year
            )
            full_prompt = (
                f"{formatted_prompt}\n\n"
                f"Here's the 10-K content to analyze:\n\n"
                f"{text}"
            )

            # Run AI analysis
            self.logger.debug(f"Running {perspective_name} analysis with AI")
            result = self._analyze_with_ai(full_prompt, schema)

            # Save results if requested
            if output_dir and result:
                self._save_result(
                    result, ticker, year, output_dir, perspective_name
                )

            self.logger.info(
                f"Successfully analyzed {ticker} {year} "
                f"({perspective_name} perspective)"
            )
            return result

        except Exception as e:
            error_msg = (
                f"{perspective_name.capitalize()} analysis failed "
                f"for {ticker} {year}: {e}"
            )
            self.logger.error(error_msg)
            raise AnalysisError(error_msg) from e

    def _analyze_with_ai(
        self,
        prompt: str,
        schema: type[BaseModel]
    ) -> Optional[BaseModel]:
        """
        Run AI analysis with structured output.

        Args:
            prompt: Complete prompt
            schema: Pydantic schema for output

        Returns:
            Validated Pydantic model instance
        """
        try:
            # Get least-used API key
            api_key = self.api_key_manager.get_least_used_key()

            if not self.rate_limiter.can_make_request(api_key):
                self.logger.warning(
                    f"API key {api_key[:10]}... hit daily limit. "
                    f"Trying next available..."
                )
                available_keys = self.api_key_manager.get_available_keys()
                if not available_keys:
                    raise AnalysisError("All API keys hit daily limits")
                api_key = available_keys[0]

            # Create provider with rate limiter
            provider = GeminiProvider(
                api_key=api_key,
                model=self.model,
                thinking_budget=self.thinking_budget,
                rate_limiter=self.rate_limiter
            )

            # Generate with retry
            result = provider.generate_with_retry(
                prompt=prompt,
                schema=schema,
                max_retries=3,
                retry_delay=10
            )

            # Record usage
            self.api_key_manager.record_usage(api_key)

            return result

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            raise AnalysisError(f"AI analysis failed: {e}") from e

    def _save_result(
        self,
        result: BaseModel,
        ticker: str,
        year: int,
        output_dir: Path,
        perspective_name: str
    ):
        """
        Save analysis result to JSON file.

        Args:
            result: Pydantic model instance
            ticker: Company ticker
            year: Fiscal year
            output_dir: Directory to save to
            perspective_name: Perspective name (for filename)
        """
        try:
            import json

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            output_file = output_dir / f"{ticker}_{year}_{perspective_name}.json"

            # Convert to dict and save
            result_dict = result.model_dump()

            with open(output_file, 'w') as f:
                json.dump(result_dict, f, indent=2)

            self.logger.info(f"Saved {perspective_name} analysis to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save result: {e}")
