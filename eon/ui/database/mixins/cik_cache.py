#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CIK cache database operations mixin.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class CIKCacheMixin:
    """Mixin for CIK to company mapping cache operations."""

    def cache_cik_company(
        self,
        cik: str,
        company_name: str,
        former_names: Optional[List[Dict]] = None,
        sic_code: Optional[str] = None,
        sic_description: Optional[str] = None,
        state_of_incorporation: Optional[str] = None,
        fiscal_year_end: Optional[str] = None
    ) -> None:
        """
        Cache CIK to company name mapping.

        Args:
            cik: CIK number (will be zero-padded)
            company_name: Company name from SEC
            former_names: List of former name dicts from SEC
            sic_code: Standard Industrial Classification code
            sic_description: SIC description
            state_of_incorporation: State where incorporated
            fiscal_year_end: Fiscal year end in MMDD format
        """
        query = """
            INSERT OR REPLACE INTO cik_company_cache
            (cik, company_name, former_names, sic_code, sic_description,
             state_of_incorporation, fiscal_year_end, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            cik.zfill(10),
            company_name,
            json.dumps(former_names) if former_names else None,
            sic_code,
            sic_description,
            state_of_incorporation,
            fiscal_year_end,
            datetime.utcnow().isoformat()
        ))

    def get_cached_cik_company(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get cached company info for CIK.

        Args:
            cik: CIK number

        Returns:
            Company info dict or None if not cached
        """
        query = "SELECT * FROM cik_company_cache WHERE cik = ?"
        row = self._execute_with_retry(query, (cik.zfill(10),), fetch_one=True)

        if row:
            result = dict(row)
            if result.get('former_names'):
                result['former_names'] = json.loads(result['former_names'])
            return result
        return None

    def create_analysis_run_with_cik(
        self,
        run_id: str,
        ticker: str,
        analysis_type: str,
        filing_type: str,
        years: List[int],
        config: Dict[str, Any],
        company_name: Optional[str] = None,
        cik: Optional[str] = None,
        input_mode: str = 'ticker'
    ) -> None:
        """
        Create new analysis run record with CIK support.

        Args:
            run_id: Unique UUID for this run
            ticker: Company ticker symbol or CIK (based on input_mode)
            analysis_type: Type of analysis
            filing_type: Filing type (10-K, 10-Q, etc.)
            years: List of years to analyze
            config: Analysis configuration as dict
            company_name: Optional company name
            cik: Optional CIK number
            input_mode: 'ticker' or 'cik'
        """
        query = """
            INSERT INTO analysis_runs
            (run_id, ticker, company_name, analysis_type, filing_type,
             years_analyzed, config_json, started_at, cik, input_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_with_retry(query, (
            run_id,
            ticker.upper() if input_mode == 'ticker' else ticker,
            company_name,
            analysis_type,
            filing_type,
            json.dumps(years),
            json.dumps(config),
            datetime.utcnow().isoformat(),
            cik.zfill(10) if cik else None,
            input_mode
        ))
