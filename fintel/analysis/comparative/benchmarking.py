#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Benchmark comparator for comparing companies against top performers.

RESTORED FROM: 10K_automator/compare_excellent_to_top_50.py
and compare_random_to_top_50.py

This module compares company success factors against a baseline of top 50
proven winners to identify alignment with success patterns using the
COMPOUNDER DNA SCORING SYSTEM.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, Union

from fintel.core import get_logger, get_config, AnalysisError
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers import GeminiProvider
from fintel.analysis.fundamental.models.success_factors import CompanySuccessFactors
from fintel.analysis.fundamental.models.excellent_company_factors import ExcellentCompanyFactors
from .models.benchmark_comparison import BenchmarkComparison
from .prompts.benchmark_comparison import BENCHMARK_COMPARISON_PROMPT


class BenchmarkComparator:
    """
    Compare companies against top 50 baseline using COMPOUNDER DNA SCORING.

    Uses pre-computed meta-analysis of top 50 proven winners to identify
    whether a company exhibits similar success patterns.

    CRITICAL SCORING FRAMEWORK:
    - 90-100: Future Compounder - Exceptional alignment
    - 75-89: Strong Potential - Significant alignment
    - 60-74: Developing Contender - Meaningful elements
    - 40-59: Partial Alignment - Some positive elements
    - 20-39: Limited Alignment - Minimal resemblance
    - 0-19: Misaligned - Counter to top performers

    Example:
        comparator = BenchmarkComparator(
            baseline_path=Path("top_50_meta_analysis.json"),
            api_key_manager=key_mgr,
            rate_limiter=rate_limiter
        )

        # Load company success factors
        company_factors = load_success_factors("AAPL_success_factors.json")

        # Compare against top 50
        comparison = comparator.compare_against_baseline(
            success_factors=company_factors
        )

        # Check compounder potential
        print(f"Score: {comparison.compounder_potential.score}")
        print(f"Category: {comparison.compounder_potential.category}")
    """

    def __init__(
        self,
        baseline_path: Path,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        model: str = None,
        thinking_budget: int = None
    ):
        """
        Initialize the benchmark comparator.

        Args:
            baseline_path: Path to top 50 meta-analysis JSON file
            api_key_manager: Manager for API key rotation
            rate_limiter: Rate limiter for API calls
            model: LLM model name (default from config)
            thinking_budget: Thinking budget (default from config)
        """
        self.baseline_path = baseline_path
        self.api_key_manager = api_key_manager
        self.rate_limiter = rate_limiter

        # Load configuration
        config = get_config()
        self.model = model or config.default_model
        # CRITICAL: Use 4096 thinking budget for deep comparative analysis
        self.thinking_budget = thinking_budget or 4096

        self.logger = get_logger(f"{__name__}.BenchmarkComparator")

        # Load baseline
        if baseline_path and baseline_path.exists():
            self.baseline = self._load_baseline(baseline_path)
            self.logger.info(f"Loaded top 50 baseline from {baseline_path}")
        else:
            raise AnalysisError(f"Baseline file not found: {baseline_path}")

    def _load_baseline(self, baseline_path: Path) -> Dict[str, Any]:
        """
        Load the top 50 meta-analysis baseline.

        Args:
            baseline_path: Path to baseline JSON file

        Returns:
            Baseline data dictionary
        """
        try:
            with open(baseline_path, "r") as f:
                baseline = json.load(f)
            self.logger.debug(f"Loaded baseline from {baseline_path}")
            return baseline
        except Exception as e:
            raise AnalysisError(f"Failed to load baseline: {e}") from e

    def compare_against_baseline(
        self,
        success_factors: Union[CompanySuccessFactors, ExcellentCompanyFactors],
        output_file: Optional[Path] = None
    ) -> BenchmarkComparison:
        """
        Compare company success factors against top 50 baseline.

        Uses AI with the COMPOUNDER DNA SCORING SYSTEM to identify
        alignment with proven multi-decade compounders.

        Args:
            success_factors: Company success factors (from either analyzer)
            output_file: Optional path to save JSON results

        Returns:
            BenchmarkComparison with comprehensive scoring and assessment

        Raises:
            AnalysisError: If comparison fails
        """
        company_name = success_factors.company_name

        self.logger.info(
            f"Comparing {company_name} against top 50 baseline"
        )

        try:
            # Construct prompt
            prompt = self._construct_prompt(success_factors)

            # Run AI analysis
            result = self._analyze_with_ai(prompt)

            # Save results if requested
            if output_file and result:
                self._save_result(result, output_file)

            return result

        except Exception as e:
            error_msg = f"Benchmark comparison failed for {company_name}: {e}"
            self.logger.error(error_msg)
            raise AnalysisError(error_msg) from e

    def _construct_prompt(
        self,
        success_factors: Union[CompanySuccessFactors, ExcellentCompanyFactors]
    ) -> str:
        """
        Construct prompt for benchmark comparison.

        Args:
            success_factors: Company success factors

        Returns:
            Complete prompt string
        """
        # Convert success factors to JSON
        company_data = success_factors.model_dump()
        company_json = json.dumps(company_data, indent=2)

        # Convert baseline to JSON
        top_50_json = json.dumps(self.baseline, indent=2)

        # Combine prompt with data
        full_prompt = (
            f"{BENCHMARK_COMPARISON_PROMPT}\n\n"
            f"## COMPANY DATA:\n{company_json}\n\n"
            f"## TOP 50 SUCCESS PRINCIPLES:\n{top_50_json}"
        )

        return full_prompt

    def _analyze_with_ai(self, prompt: str) -> Optional[BenchmarkComparison]:
        """
        Run AI analysis for benchmark comparison.

        Args:
            prompt: Complete prompt with data

        Returns:
            BenchmarkComparison model
        """
        try:
            # Get least-used API key
            api_key = self.api_key_manager.get_least_used_key()

            self.logger.debug(f"Using API key: {api_key[:10]}...")

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
                schema=BenchmarkComparison,
                max_retries=3,
                retry_delay=10
            )

            # Record usage
            self.api_key_manager.record_usage(api_key)

            return result

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            raise AnalysisError(f"AI analysis failed: {e}") from e

    def _save_result(self, result: BenchmarkComparison, output_file: Path):
        """
        Save benchmark comparison to JSON.

        Args:
            result: Benchmark comparison model
            output_file: Path to save to
        """
        try:
            # Create output directory
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict and save
            result_dict = result.model_dump()

            with open(output_file, 'w') as f:
                json.dump(result_dict, f, indent=2)

            self.logger.info(f"Saved benchmark comparison to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save result: {e}")

    def get_baseline_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the baseline.

        Returns:
            Dictionary with baseline statistics
        """
        return {
            "total_companies": self.baseline.get("total_companies", "Unknown"),
            "baseline_source": str(self.baseline_path),
            "analysis_period": self.baseline.get("analysis_period", "Unknown"),
            "available": True
        }

    def print_summary(self, comparison: BenchmarkComparison) -> None:
        """
        Print a formatted summary of the comparison to console.

        Args:
            comparison: Benchmark comparison result
        """
        print("\n" + "=" * 80)
        print(f"BENCHMARK COMPARISON: {comparison.company_name}")
        print(f"Analysis Date: {comparison.analysis_date}")
        print("=" * 80)

        # Compounder potential
        potential = comparison.compounder_potential
        print(f"\nCOMPOUNDER POTENTIAL SCORE: {potential.score}/100")
        print(f"CATEGORY: {potential.category}")
        print(f"\n{potential.summary}")

        # Distinctive strengths
        print("\nDISTINCTIVE STRENGTHS:")
        for strength in potential.distinctive_strengths:
            print(f"  + {strength}")

        # Critical gaps
        print("\nCRITICAL GAPS:")
        for gap in potential.critical_gaps:
            print(f"  - {gap}")

        # Final assessment
        final = comparison.final_assessment
        print(f"\nVERDICT: {final.verdict}")
        print(f"PROBABILITY OF OUTPERFORMANCE: {final.probability_of_outperformance}")

        # Key areas to monitor
        print("\nKEY AREAS TO MONITOR:")
        for area in final.key_areas_to_monitor:
            print(f"  • {area}")

        print("\n" + "=" * 80)


__all__ = [
    'BenchmarkComparator',
]
