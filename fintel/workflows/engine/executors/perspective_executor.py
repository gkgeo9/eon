#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PerspectiveAnalysisExecutor - Apply investment perspective lenses.
"""

from typing import Dict, Any, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import StepExecutor
from ..data_container import DataContainer
from fintel.core import get_logger
from fintel.analysis.perspectives import PerspectiveAnalyzer


class PerspectiveAnalysisExecutor(StepExecutor):
    """
    Apply investment perspective lenses (Buffett/Taleb/Contrarian).

    Input: DataContainer with fundamental analyses (or filings)
    Output: DataContainer (same shape, with perspective analyses)

    Config:
        - perspectives: List["buffett" | "taleb" | "contrarian"]
        - run_parallel: bool (default: True)

    Note: This requires PDF files, so it works on the original filing data.
    """

    def __init__(self, db, analysis_service):
        super().__init__(db, analysis_service)
        self.logger = get_logger(__name__)

        if not analysis_service:
            raise ValueError("PerspectiveAnalysisExecutor requires AnalysisService")

        self.analyzer = PerspectiveAnalyzer(
            api_key_manager=analysis_service.api_key_manager,
            rate_limiter=analysis_service.rate_limiter
        )

    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data."""
        if input_data is None:
            raise ValueError("PerspectiveAnalysisExecutor requires input data")
        return True

    def execute(self, config: Dict[str, Any], input_data: DataContainer) -> DataContainer:
        """
        Run perspective analyses.

        Args:
            config: Configuration with perspectives list and run_parallel
            input_data: DataContainer with ticker/year structure

        Returns:
            DataContainer with perspective analysis results
        """
        self.validate_input(input_data)

        perspectives = config.get('perspectives', ['buffett'])
        run_parallel = config.get('run_parallel', True)
        filing_type = input_data.metadata.get('filing_type', '10-K')

        self.logger.info(
            f"Running perspective analyses: {perspectives}, "
            f"parallel={run_parallel}"
        )

        results = {}
        run_ids = []

        # Build list of (ticker, year) tasks
        tasks = []
        for ticker in input_data.tickers:
            for year in input_data.get_years_for_ticker(ticker):
                tasks.append((ticker, year))

        if run_parallel and len(tasks) > 1:
            # Run in parallel
            results = self._run_parallel(tasks, perspectives, filing_type)
        else:
            # Run sequentially
            results = self._run_sequential(tasks, perspectives, filing_type)

        # Create output container
        output = DataContainer(
            data=results,
            num_companies=input_data.num_companies,
            num_years_per_company=input_data.num_years_per_company,
            step_id=config.get('step_id', 'perspective_1'),
            step_type='perspective_analysis',
            source_run_ids=run_ids,
            metadata={
                'perspectives': perspectives,
                'run_parallel': run_parallel,
                'filing_type': filing_type,
                'input_step': input_data.step_id
            }
        )

        self.logger.info(
            f"Perspective analysis complete: {output.total_items} results"
        )

        return output

    def _run_sequential(
        self,
        tasks: List[Tuple[str, int]],
        perspectives: List[str],
        filing_type: str
    ) -> Dict:
        """Run analyses sequentially."""
        results = {}

        for ticker, year in tasks:
            if ticker not in results:
                results[ticker] = {}

            self.logger.info(f"Analyzing {ticker} {year} ({perspectives})")

            try:
                # Get PDF path from cache
                pdf_path = self.db.get_cached_file(ticker, year, filing_type)

                if not pdf_path:
                    self.logger.warning(f"No PDF found for {ticker} {year}")
                    results[ticker][year] = None
                    continue

                # Run each perspective
                perspective_results = {}

                for perspective in perspectives:
                    if perspective == 'buffett':
                        result = self.analyzer.analyze_buffett(
                            pdf_path=pdf_path,
                            ticker=ticker,
                            year=year
                        )
                    elif perspective == 'taleb':
                        result = self.analyzer.analyze_taleb(
                            pdf_path=pdf_path,
                            ticker=ticker,
                            year=year
                        )
                    elif perspective == 'contrarian':
                        result = self.analyzer.analyze_contrarian(
                            pdf_path=pdf_path,
                            ticker=ticker,
                            year=year
                        )
                    else:
                        self.logger.warning(f"Unknown perspective: {perspective}")
                        continue

                    if result:
                        perspective_results[perspective] = result

                results[ticker][year] = perspective_results

            except Exception as e:
                self.logger.error(f"Failed to analyze {ticker} {year}: {e}")
                results[ticker][year] = None

        return results

    def _run_parallel(
        self,
        tasks: List[Tuple[str, int]],
        perspectives: List[str],
        filing_type: str
    ) -> Dict:
        """Run analyses in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    self._analyze_one,
                    ticker,
                    year,
                    perspectives,
                    filing_type
                ): (ticker, year)
                for ticker, year in tasks
            }

            for future in as_completed(futures):
                ticker, year = futures[future]

                try:
                    result = future.result()

                    if ticker not in results:
                        results[ticker] = {}
                    results[ticker][year] = result

                except Exception as e:
                    self.logger.error(f"Failed to analyze {ticker} {year}: {e}")
                    if ticker not in results:
                        results[ticker] = {}
                    results[ticker][year] = None

        return results

    def _analyze_one(
        self,
        ticker: str,
        year: int,
        perspectives: List[str],
        filing_type: str
    ) -> Optional[Dict]:
        """Analyze one ticker/year combination."""
        self.logger.info(f"Analyzing {ticker} {year} ({perspectives})")

        # Get PDF path
        pdf_path = self.db.get_cached_file(ticker, year, filing_type)

        if not pdf_path:
            self.logger.warning(f"No PDF found for {ticker} {year}")
            return None

        # Run each perspective
        perspective_results = {}

        for perspective in perspectives:
            try:
                if perspective == 'buffett':
                    result = self.analyzer.analyze_buffett(
                        pdf_path=pdf_path,
                        ticker=ticker,
                        year=year
                    )
                elif perspective == 'taleb':
                    result = self.analyzer.analyze_taleb(
                        pdf_path=pdf_path,
                        ticker=ticker,
                        year=year
                    )
                elif perspective == 'contrarian':
                    result = self.analyzer.analyze_contrarian(
                        pdf_path=pdf_path,
                        ticker=ticker,
                        year=year
                    )
                else:
                    continue

                if result:
                    perspective_results[perspective] = result

            except Exception as e:
                self.logger.error(f"Failed {perspective} for {ticker} {year}: {e}")

        return perspective_results if perspective_results else None

    def expected_output_shape(self, input_shape: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        """Output shape is same as input shape."""
        return input_shape if input_shape else (0, 0)
