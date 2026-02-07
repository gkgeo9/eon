"""
Contrarian scanner for identifying hidden gem investment opportunities.

This module scans companies using multi-year success factor analysis
to identify undervalued contrarian opportunities with "compounder DNA".
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from eon.core import get_logger, AnalysisError
from eon.ai import APIKeyManager, RateLimiter
from eon.ai.providers.gemini import GeminiProvider

logger = get_logger(__name__)


class ContrarianScores(BaseModel):
    """Individual contrarian scoring dimensions."""

    strategic_anomaly: int = Field(..., ge=0, le=100, description="Bold, counterintuitive strategic moves")
    asymmetric_resources: int = Field(..., ge=0, le=100, description="Concentrated resource allocation")
    contrarian_positioning: int = Field(..., ge=0, le=100, description="Inverse to industry orthodoxy")
    cross_industry_dna: int = Field(..., ge=0, le=100, description="Leadership importing foreign practices")
    early_infrastructure: int = Field(..., ge=0, le=100, description="Building for future markets")
    intellectual_capital: int = Field(..., ge=0, le=100, description="Undervalued IP/capabilities")


class ContrarianAnalysis(BaseModel):
    """
    Contrarian investment analysis result.

    Scores companies on six dimensions of contrarian/hidden gem potential.
    Overall "alpha score" represents composite opportunity assessment.
    """

    ticker: str
    company_name: str
    overall_alpha_score: int = Field(..., ge=0, le=100, description="Composite contrarian opportunity score")
    scores: ContrarianScores
    key_insights: List[str] = Field(default_factory=list, description="Factual observations about strategy")
    investment_thesis: str = Field(description="Objective assessment based on evidence")
    risk_factors: List[str] = Field(default_factory=list, description="Primary execution/market risks")
    catalyst_timeline: str = Field(description="Timeframe for thesis validation")
    confidence_level: str = Field(description="HIGH/MEDIUM/LOW based on evidence strength")


class ContrarianScanner:
    """
    Scan companies for contrarian investment opportunities.

    Uses multi-year success factor analysis to identify hidden gems
    with strong "compounder DNA" that may be undervalued by the market.
    """

    # Contrarian analysis prompt
    CONTRARIAN_PROMPT = """
You are an objective investment analyst. Analyze this company's data without bias toward company size, market cap, or industry popularity. Be brutally honest - most companies will score poorly on these metrics, and that's expected.

**COMPANY DATA:**
{company_data}

**SCORING FRAMEWORK (0-100 scale):**

1. **STRATEGIC ANOMALY SCORE (0-100)**
   - 0-20: Standard industry playbook, no unusual decisions
   - 21-40: Minor deviations from industry norm, low-risk moves
   - 41-60: Some unconventional decisions with unclear rationale
   - 61-80: Clear contrarian strategy with logical reasoning
   - 81-100: Bold, counterintuitive moves that could redefine their space

2. **ASYMMETRIC RESOURCE ALLOCATION (0-100)**
   - 0-20: Resources spread evenly across standard business areas
   - 21-40: Slight concentration in 1-2 areas, typical allocation
   - 41-60: Moderate bet on specific initiative (10-25% of resources)
   - 61-80: Major bet on single opportunity (25-50% of resources)
   - 81-100: All-in bet risking company on transformative opportunity

3. **CONTRARIAN POSITIONING (0-100)**
   - 0-20: Following exact industry trends and consensus
   - 21-40: Minor differentiation, mostly following pack
   - 41-60: Some opposite moves but hedging bets
   - 61-80: Clear opposite positioning on key industry assumptions
   - 81-100: Completely inverse strategy to industry orthodoxy

4. **CROSS-INDUSTRY DNA (0-100)**
   - 0-20: Management with only same-industry experience
   - 21-40: Some outside hires but maintaining industry norms
   - 41-60: Applying select concepts from other industries
   - 61-80: Leadership actively importing foreign industry practices
   - 81-100: Fundamentally operating like a different industry

5. **EARLY INFRASTRUCTURE BUILDER (0-100)**
   - 0-20: Building for current market needs only
   - 21-40: Minor investments in next-generation capabilities
   - 41-60: Significant R&D for 2-3 year market evolution
   - 61-80: Building for markets 3-5 years out
   - 81-100: Creating infrastructure for markets that don't exist yet

6. **UNDERVALUED INTELLECTUAL CAPITAL (0-100)**
   - 0-20: Standard IP portfolio, no hidden technical advantages
   - 21-40: Decent IP but well-recognized by market
   - 41-60: Some overlooked technical capabilities or patents
   - 61-80: Significant hidden technical moats or IP value
   - 81-100: Game-changing IP/capabilities completely unrecognized

**CRITICAL INSTRUCTIONS:**
- Primary focus: Score based on EVIDENCE from financial data, management actions, and concrete business decisions
- Secondary consideration: Include forward-looking execution capability only when supported by track record
- Only award high scores (60+) with specific justification citing data points
- Company size, age, market cap, or industry power is irrelevant - judge actions relative to their available resources
- Score distribution expectation: Most companies 20-50, good companies 51-70, exceptional companies 71-85, truly revolutionary companies 86-100
- Be objective: don't inflate scores for potential alone, but don't ignore demonstrated execution ability

**OUTPUT FORMAT:**
Return ONLY a valid JSON object with NO additional text before or after.
"""

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        rate_limiter: RateLimiter,
        api_key: Optional[str] = None
    ):
        """
        Initialize the contrarian scanner.

        Args:
            api_key_manager: API key manager for rotation
            rate_limiter: Rate limiter for API calls
            api_key: Optional pre-reserved API key (for batch queue optimization)
        """
        self.api_key_manager = api_key_manager
        self.rate_limiter = rate_limiter
        self._pre_reserved_key = api_key
        logger.info("Initialized ContrarianScanner")

    def scan_company(
        self,
        ticker: str,
        success_factors_path: Optional[Path] = None,
        years: int = 30
    ) -> Optional[ContrarianAnalysis]:
        """
        Scan a single company for contrarian opportunities.

        Args:
            ticker: Company ticker symbol
            success_factors_path: Optional path to pre-computed success factors
            years: Number of years to analyze (default: 30)

        Returns:
            ContrarianAnalysis result or None if analysis fails
        """
        try:
            logger.info(f"Scanning {ticker} for contrarian opportunities")

            # Get success factors (must be pre-computed or loaded from file)
            if success_factors_path and success_factors_path.exists():
                logger.debug(f"Loading success factors from {success_factors_path}")
                with open(success_factors_path, "r") as f:
                    success_data = json.load(f)
            else:
                logger.error(
                    f"No pre-computed success factors found for {ticker}. "
                    f"Run success factor analysis first using CompanySuccessAnalyzer."
                )
                return None

            # Create analysis prompt
            company_data_str = json.dumps(success_data, indent=2)
            prompt = self.CONTRARIAN_PROMPT.format(company_data=company_data_str)

            # Use pre-reserved key if available (batch optimization), otherwise reserve
            if self._pre_reserved_key:
                api_key = self._pre_reserved_key
                key_was_pre_reserved = True
            else:
                api_key = self.api_key_manager.reserve_key()
                key_was_pre_reserved = False

            if not api_key:
                logger.error(f"No API keys available for {ticker}")
                return None

            try:
                provider = GeminiProvider(
                    api_key=api_key,
                    rate_limiter=self.rate_limiter
                )

                # Perform contrarian analysis with retry
                result = provider.generate_with_retry(
                    prompt=prompt,
                    schema=ContrarianAnalysis
                )

                if result:
                    logger.info(
                        f"Contrarian analysis complete for {ticker} "
                        f"(alpha score: {result.overall_alpha_score})"
                    )
                    return result
                else:
                    logger.warning(f"Failed contrarian analysis for {ticker}")
                    return None

            finally:
                if not key_was_pre_reserved:
                    self.api_key_manager.release_key(api_key)

        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")
            return None

    def scan_companies(
        self,
        tickers: List[str],
        success_factors_dir: Optional[Path] = None,
        min_score: int = 0
    ) -> pd.DataFrame:
        """
        Scan multiple companies and return ranked opportunities.

        Args:
            tickers: List of ticker symbols to scan
            success_factors_dir: Optional directory with pre-computed success factors
            min_score: Minimum alpha score threshold (default: 0, no filter)

        Returns:
            DataFrame with ranked contrarian opportunities
        """
        results = []

        for ticker in tickers:
            # Determine success factors path if directory provided
            success_path = None
            if success_factors_dir:
                success_path = success_factors_dir / f"{ticker}_success_factors.json"

            # Scan company
            analysis = self.scan_company(
                ticker=ticker,
                success_factors_path=success_path
            )

            if analysis:
                # Convert to dict for DataFrame
                result_dict = {
                    "ticker": analysis.ticker,
                    "company_name": analysis.company_name,
                    "alpha_score": analysis.overall_alpha_score,
                    "strategic_anomaly": analysis.scores.strategic_anomaly,
                    "asymmetric_resources": analysis.scores.asymmetric_resources,
                    "contrarian_positioning": analysis.scores.contrarian_positioning,
                    "cross_industry_dna": analysis.scores.cross_industry_dna,
                    "early_infrastructure": analysis.scores.early_infrastructure,
                    "intellectual_capital": analysis.scores.intellectual_capital,
                    "investment_thesis": analysis.investment_thesis,
                    "catalyst_timeline": analysis.catalyst_timeline,
                    "confidence_level": analysis.confidence_level,
                }
                results.append(result_dict)

        # Create DataFrame
        df = pd.DataFrame(results)

        if df.empty:
            logger.warning("No successful scans, returning empty DataFrame")
            return df

        # Sort by alpha score (descending)
        df = df.sort_values("alpha_score", ascending=False).reset_index(drop=True)

        # Filter by minimum score if specified
        if min_score > 0:
            df = df[df["alpha_score"] >= min_score]
            logger.info(f"Filtered to {len(df)} companies with alpha score >= {min_score}")

        return df

    def export_rankings(
        self,
        df: pd.DataFrame,
        output_path: Path,
        format: str = "csv"
    ) -> None:
        """
        Export ranked opportunities to file.

        Args:
            df: DataFrame with ranked opportunities
            output_path: Path to output file
            format: Output format ("csv" or "excel")
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            df.to_csv(output_path, index=False)
            logger.info(f"Exported {len(df)} opportunities to {output_path}")
        elif format == "excel":
            df.to_excel(output_path, index=False, sheet_name="Contrarian Opportunities")
            logger.info(f"Exported {len(df)} opportunities to {output_path}")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_top_opportunities(
        self,
        df: pd.DataFrame,
        top_n: int = 10,
        min_confidence: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get top N contrarian opportunities with optional confidence filter.

        Args:
            df: DataFrame with ranked opportunities
            top_n: Number of top opportunities to return
            min_confidence: Optional minimum confidence level ("HIGH", "MEDIUM", "LOW")

        Returns:
            Filtered DataFrame with top opportunities
        """
        result_df = df.copy()

        # Filter by confidence if specified
        if min_confidence:
            confidence_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            min_level = confidence_levels.get(min_confidence.upper(), 0)

            result_df = result_df[
                result_df["confidence_level"].map(confidence_levels) >= min_level
            ]

        # Return top N
        return result_df.head(top_n)
