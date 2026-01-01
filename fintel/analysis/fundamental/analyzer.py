#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fundamental analysis of 10-K filings using AI.

Integrates PDF extraction, prompt engineering, and AI generation
to produce structured analysis of company filings.
"""

import json
from pathlib import Path
from typing import Optional, Type, Dict, List
from pydantic import BaseModel

from fintel.core import get_logger, get_config, AnalysisError, ExtractionError
from fintel.data.sources.sec import PDFExtractor
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers import GeminiProvider
from fintel.ai.prompts.fundamental import DEFAULT_10K_PROMPT, format_prompt
from .schemas import TenKAnalysis


class FundamentalAnalyzer:
    """
    Analyzes 10-K PDF filings using AI to extract fundamental insights.

    Three-stage pipeline:
    1. PDF text extraction
    2. Prompt construction with company/year context
    3. AI analysis with structured output validation

    Example:
        config = get_config()
        key_mgr = APIKeyManager(config.google_api_keys)
        rate_limiter = RateLimiter()

        analyzer = FundamentalAnalyzer(
            api_key_manager=key_mgr,
            rate_limiter=rate_limiter
        )

        result = analyzer.analyze_filing(
            pdf_path=Path("./AAPL_10-K_2024.pdf"),  # or any filing type
            ticker="AAPL",
            year=2024,
            schema=TenKAnalysis
        )
    """

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        model: str = None,
        thinking_budget: int = None,
        use_structured_output: bool = True
    ):
        """
        Initialize the fundamental analyzer.

        Args:
            api_key_manager: Manager for API key rotation and usage tracking
            rate_limiter: Rate limiter for API calls
            model: LLM model name (default from config)
            thinking_budget: Thinking budget (default from config)
            use_structured_output: Use Pydantic structured output
        """
        self.api_key_manager = api_key_manager
        self.rate_limiter = rate_limiter
        self.use_structured_output = use_structured_output

        # Load configuration
        config = get_config()
        self.model = model or config.default_model
        self.thinking_budget = thinking_budget or config.thinking_budget

        # Initialize PDF extractor
        self.pdf_extractor = PDFExtractor()

        # Logger
        self.logger = get_logger(f"{__name__}.FundamentalAnalyzer")
        self.logger.info(
            f"Initialized FundamentalAnalyzer "
            f"(model={self.model}, structured_output={use_structured_output})"
        )

    def analyze_filing(
        self,
        pdf_path: Path,
        ticker: str,
        year: int,
        schema: Optional[Type[BaseModel]] = None,
        custom_prompt: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Optional[BaseModel]:
        """
        Analyze a single 10-K filing.

        Args:
            pdf_path: Path to the PDF file
            ticker: Company ticker symbol
            year: Fiscal year of filing
            schema: Pydantic schema for structured output (default: TenKAnalysis)
            custom_prompt: Custom prompt template (default: DEFAULT_10K_PROMPT)
            output_dir: Optional directory to save JSON results

        Returns:
            Pydantic model instance with analysis, or None on failure

        Raises:
            AnalysisError: If analysis fails critically
        """
        self.logger.info(f"Analyzing {ticker} {year} 10-K from {pdf_path.name}")

        try:
            # Stage 1: Extract text from PDF
            self.logger.debug(f"Stage 1: Extracting text from PDF")
            text = self._extract_text(pdf_path)

            if not text or len(text.strip()) < 100:
                raise ExtractionError(
                    f"PDF extraction failed or produced insufficient text "
                    f"({len(text) if text else 0} characters)"
                )

            # Stage 2: Construct prompt
            self.logger.debug(f"Stage 2: Constructing prompt")
            prompt = self._construct_prompt(ticker, year, text, custom_prompt)

            # Stage 3: AI analysis with schema
            self.logger.debug(f"Stage 3: Running AI analysis")
            schema = schema or TenKAnalysis
            result = self._analyze_with_ai(prompt, schema)

            # Stage 4: Save results (optional)
            if output_dir and result:
                self._save_result(result, ticker, year, output_dir)

            self.logger.info(f"Successfully analyzed {ticker} {year}")
            return result

        except ExtractionError as e:
            self.logger.error(f"Text extraction failed for {ticker} {year}: {e}")
            return None

        except Exception as e:
            error_msg = f"Analysis failed for {ticker} {year}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception("Full traceback:")
            return None

    def analyze_multiple_filings(
        self,
        pdf_paths: List[Path],
        ticker: str,
        schema: Optional[Type[BaseModel]] = None,
        custom_prompt: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[int, BaseModel]:
        """
        Analyze multiple filings for a single company.

        Args:
            pdf_paths: List of PDF file paths
            ticker: Company ticker symbol
            schema: Pydantic schema for structured output
            custom_prompt: Custom prompt template
            output_dir: Optional directory to save JSON results

        Returns:
            Dictionary mapping year to analysis result: {2024: TenKAnalysis, ...}
        """
        self.logger.info(f"Analyzing {len(pdf_paths)} filings for {ticker}")
        results = {}

        for pdf_path in pdf_paths:
            # Extract year from filename (assumes format: TICKER_FILING-TYPE_YEAR.pdf)
            try:
                year = int(pdf_path.stem.split('_')[-1])
            except (ValueError, IndexError):
                self.logger.warning(
                    f"Could not extract year from filename: {pdf_path.name}. Skipping."
                )
                continue

            result = self.analyze_filing(
                pdf_path=pdf_path,
                ticker=ticker,
                year=year,
                schema=schema,
                custom_prompt=custom_prompt,
                output_dir=output_dir
            )

            if result:
                results[year] = result

        self.logger.info(
            f"Completed analysis for {ticker}: "
            f"{len(results)}/{len(pdf_paths)} successful"
        )
        return results

    def _extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF

        Returns:
            Extracted text

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            text = self.pdf_extractor.extract_text(pdf_path)
            self.logger.debug(f"Extracted {len(text):,} characters from PDF")
            return text

        except Exception as e:
            raise ExtractionError(f"PDF extraction failed: {e}") from e

    def _construct_prompt(
        self,
        ticker: str,
        year: int,
        content: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Construct full prompt with company context and content.

        Args:
            ticker: Company ticker
            year: Fiscal year
            content: Extracted PDF text
            custom_prompt: Optional custom prompt template

        Returns:
            Complete prompt string
        """
        # Use custom or default prompt template
        prompt_template = custom_prompt or DEFAULT_10K_PROMPT

        # Format with company name and year
        formatted_prompt = format_prompt(prompt_template, ticker, year)

        # Append the filing content
        full_prompt = (
            f"{formatted_prompt}\n\n"
            f"Here's the 10-K content to analyze:\n\n"
            f"{content}"
        )

        token_estimate = len(full_prompt) // 4
        self.logger.debug(
            f"Constructed prompt: {len(full_prompt):,} chars "
            f"(~{token_estimate:,} tokens)"
        )

        return full_prompt

    def _analyze_with_ai(
        self,
        prompt: str,
        schema: Type[BaseModel]
    ) -> Optional[BaseModel]:
        """
        Run AI analysis with structured output.

        Args:
            prompt: Complete prompt
            schema: Pydantic schema for output

        Returns:
            Validated Pydantic model instance, or None on failure
        """
        # Reserve a key atomically to prevent race conditions in batch processing
        api_key = self.api_key_manager.reserve_key()

        if api_key is None:
            raise AnalysisError(
                "No API keys available! All keys are either in use by other threads "
                "or have reached their daily limits."
            )

        try:
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
            self.logger.debug(f"Using reserved API key: ...{key_suffix}")

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
                schema=schema if self.use_structured_output else None,
                max_retries=3,
                retry_delay=10
            )

            # Record usage in key manager
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
        result: BaseModel,
        ticker: str,
        year: int,
        output_dir: Path
    ):
        """
        Save analysis result to JSON file.

        Args:
            result: Pydantic model instance
            ticker: Company ticker
            year: Fiscal year
            output_dir: Directory to save to
        """
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            output_file = output_dir / f"{ticker}_{year}_analysis.json"

            # Convert to dict and save
            if isinstance(result, BaseModel):
                result_dict = result.model_dump()
            else:
                result_dict = result

            with open(output_file, 'w') as f:
                json.dump(result_dict, f, indent=2)

            self.logger.info(f"Saved analysis to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save result: {e}")

    def get_stats(self) -> Dict[str, any]:
        """
        Get analyzer statistics.

        Returns:
            Dictionary with API key and rate limiter stats
        """
        return {
            'model': self.model,
            'thinking_budget': self.thinking_budget,
            'structured_output': self.use_structured_output,
            'api_keys': self.api_key_manager.get_usage_stats(),
            'rate_limiter': self.rate_limiter.get_stats()
        }
