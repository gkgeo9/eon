"""
Leadership Extractor - Extract and analyze leadership teams from 14A proxy statements.

This module provides custom scripting capabilities to:
1. Download 14A proxy statements for any ticker
2. Extract all directors and executive officers
3. Perform individual deep-dive research on each leader
4. Generate comprehensive leadership profiles with external data

Usage:
    from experimentation.leadership_extractor import LeadershipExtractor

    extractor = LeadershipExtractor()

    # Extract basic leadership team
    team = extractor.extract_leadership_team("AAPL")

    # Get detailed profiles for each leader
    profiles = extractor.extract_detailed_profiles("AAPL")
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from fintel.core import get_config
from fintel.core.exceptions import AnalysisError, DataSourceError
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ai.providers.gemini import GeminiProvider

from .schemas import LeadershipMember, LeadershipTeam, LeaderDetailedProfile


logger = logging.getLogger(__name__)


class LeadershipExtractor:
    """
    Extract and analyze leadership teams from 14A proxy statements.

    This class leverages existing Fintel infrastructure to:
    - Download DEF 14A filings from SEC EDGAR
    - Extract structured leadership data using AI
    - Perform individual research on each leader
    - Generate comprehensive leadership profiles
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        model: str = "gemini-2.5-flash",
        use_google_search: bool = True,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize the leadership extractor.

        Args:
            api_keys: List of Google API keys (defaults to config)
            model: Gemini model to use (default: gemini-3-pro-preview)
            thinking_level: Thinking level for Gemini 3 ("LOW", "MEDIUM", "HIGH")
            use_google_search: Enable Google Search tool for external research
            output_dir: Directory to save results (defaults to data/experimentation/leadership)
        """
        self.config = get_config()

        # API setup
        api_keys = api_keys or self.config.google_api_keys
        self.key_manager = APIKeyManager(
            api_keys=api_keys,
            max_requests_per_day=self.config.max_requests_per_day
        )
        self.rate_limiter = RateLimiter(
            sleep_after_request=self.config.sleep_after_request,
            max_requests_per_day=self.config.max_requests_per_day
        )

        # LLM provider configuration
        self.model = model
        # self.thinking_level = thinking_level
        self.use_google_search = use_google_search

        # SEC data sources
        self.downloader = SECDownloader(
            company_name=self.config.sec_company_name,
            user_email=self.config.sec_user_email
        )
        self.converter = SECConverter()
        self.extractor = PDFExtractor()

        # Output directory
        if output_dir is None:
            output_dir = self.config.get_data_path("experimentation", "leadership")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"LeadershipExtractor initialized with model: {model}, "
            # f"thinking_level: {thinking_level}, "
            f"google_search: {use_google_search}"
        )

    def _get_provider(self) -> GeminiProvider:
        """Get a fresh Gemini provider with least-used API key."""
        api_key = self.key_manager.get_least_used_key()
        return GeminiProvider(
            api_key=api_key,
            model=self.model,
            # thinking_level=self.thinking_level,
            use_google_search=self.use_google_search,
            rate_limiter=self.rate_limiter
        )

    def _download_14a_filing(self, ticker: str, num_filings: int = 1) -> Path:
        """
        Download the most recent DEF 14A proxy statement for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            num_filings: Number of recent filings to download

        Returns:
            Path to the downloaded filing directory

        Raises:
            DataSourceError: If download fails
        """
        logger.info(f"Downloading DEF 14A filing for {ticker}")

        try:
            filing_path = self.downloader.download(
                ticker=ticker,
                num_filings=num_filings,
                filing_type="DEF 14A"
            )
            logger.info(f"Downloaded to: {filing_path}")
            return Path(filing_path)
        except Exception as e:
            raise DataSourceError(f"Failed to download 14A for {ticker}: {str(e)}")

    def _convert_to_pdf(self, ticker: str, filing_path: Path) -> List[Dict[str, Any]]:
        """
        Convert downloaded HTML filing to PDF.

        Args:
            ticker: Stock ticker symbol
            filing_path: Path to downloaded filing directory

        Returns:
            List of dicts with 'pdf_path', 'year', 'filing_type'

        Raises:
            DataSourceError: If conversion fails
        """
        logger.info(f"Converting {ticker} DEF 14A to PDF")

        try:
            pdfs = self.converter.convert(
                ticker=ticker,
                input_path=filing_path,
                filing_type="DEF 14A"
            )
            if not pdfs:
                raise DataSourceError(f"No PDFs generated for {ticker}")

            logger.info(f"Converted {len(pdfs)} filing(s) to PDF")
            return pdfs
        except Exception as e:
            raise DataSourceError(f"Failed to convert 14A to PDF: {str(e)}")

    def _extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF filing.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content

        Raises:
            DataSourceError: If extraction fails
        """
        logger.info(f"Extracting text from: {pdf_path}")

        try:
            text = self.extractor.extract_text(pdf_path)
            if not text or len(text.strip()) < 100:
                raise DataSourceError(f"Extracted text too short or empty: {len(text)} chars")

            logger.info(f"Extracted {len(text):,} characters")
            return text
        except Exception as e:
            raise DataSourceError(f"Failed to extract text from PDF: {str(e)}")

    def extract_leadership_team(
        self,
        ticker: str,
        num_filings: int = 1,
        save_to_file: bool = True
    ) -> LeadershipTeam:
        """
        Extract complete leadership team from 14A proxy statement.

        This performs the full pipeline:
        1. Download DEF 14A filing
        2. Convert to PDF and extract text
        3. Use AI to extract structured leadership data

        Args:
            ticker: Stock ticker symbol
            num_filings: Number of recent filings to process (default: 1)
            save_to_file: Whether to save results to JSON

        Returns:
            LeadershipTeam object with all directors and executives

        Raises:
            AnalysisError: If extraction fails
        """
        logger.info(f"Extracting leadership team for {ticker}")

        try:
            # Step 1: Download filing
            filing_path = self._download_14a_filing(ticker, num_filings)

            # Step 2: Convert to PDF
            pdfs = self._convert_to_pdf(ticker, filing_path)

            # Step 3: Extract text from most recent filing
            pdf_info = pdfs[0]  # Most recent
            text = self._extract_text(Path(pdf_info['pdf_path']))

            # Step 4: AI extraction
            prompt = self._build_leadership_extraction_prompt(ticker, text)

            provider = self._get_provider()
            result = provider.generate(
                prompt=prompt,
                schema=LeadershipTeam,
                max_retries=3
            )

            # Parse result
            team = LeadershipTeam.model_validate(result)

            # Save to file
            if save_to_file:
                output_file = self.output_dir / f"{ticker}_leadership_team.json"
                with open(output_file, 'w') as f:
                    json.dump(team.model_dump(), f, indent=2)
                logger.info(f"Saved leadership team to: {output_file}")

            logger.info(
                f"Extracted {len(team.board_of_directors)} directors and "
                f"{len(team.executive_officers)} executives for {ticker}"
            )

            return team

        except Exception as e:
            raise AnalysisError(f"Failed to extract leadership for {ticker}: {str(e)}")

    def extract_detailed_profile(
        self,
        leader: LeadershipMember,
        ticker: str,
        filing_text: Optional[str] = None
    ) -> LeaderDetailedProfile:
        """
        Extract detailed profile for a single leader with external research.

        This makes individual AI calls to research each leader in depth.
        Google Search is automatically enabled if configured in the extractor.

        Args:
            leader: LeadershipMember to research
            ticker: Company ticker symbol
            filing_text: Full 14A text (optional, for context)

        Returns:
            LeaderDetailedProfile with comprehensive background

        Raises:
            AnalysisError: If profile extraction fails
        """
        logger.info(f"Extracting detailed profile for {leader.name}")

        try:
            prompt = self._build_detailed_profile_prompt(
                leader=leader,
                ticker=ticker,
                filing_text=filing_text
            )

            provider = self._get_provider()
            result = provider.generate(
                prompt=prompt,
                schema=LeaderDetailedProfile,
                max_retries=3
            )

            profile = LeaderDetailedProfile.model_validate(result)
            logger.info(f"Extracted detailed profile for {leader.name}")

            return profile

        except Exception as e:
            raise AnalysisError(f"Failed to extract profile for {leader.name}: {str(e)}")

    def extract_detailed_profiles(
        self,
        ticker: str,
        leaders: Optional[List[LeadershipMember]] = None,
        save_to_file: bool = True
    ) -> List[LeaderDetailedProfile]:
        """
        Extract detailed profiles for all leaders in a company.

        This makes individual AI calls for each leader to gather
        comprehensive background information.

        Args:
            ticker: Stock ticker symbol
            leaders: List of LeadershipMembers (if None, extracts from 14A first)
            save_to_file: Whether to save results to JSON

        Returns:
            List of LeaderDetailedProfile objects

        Raises:
            AnalysisError: If extraction fails
        """
        logger.info(f"Extracting detailed profiles for {ticker} leadership")

        # If no leaders provided, extract them first
        if leaders is None:
            team = self.extract_leadership_team(ticker)
            leaders = team.board_of_directors + team.executive_officers

        profiles = []

        for i, leader in enumerate(leaders, 1):
            logger.info(f"Processing {i}/{len(leaders)}: {leader.name}")

            try:
                profile = self.extract_detailed_profile(
                    leader=leader,
                    ticker=ticker
                )
                profiles.append(profile)

            except Exception as e:
                logger.error(f"Failed to extract profile for {leader.name}: {e}")
                continue

        # Save to file
        if save_to_file:
            output_file = self.output_dir / f"{ticker}_detailed_profiles.json"
            with open(output_file, 'w') as f:
                json.dump(
                    [p.model_dump() for p in profiles],
                    f,
                    indent=2
                )
            logger.info(f"Saved {len(profiles)} profiles to: {output_file}")

        logger.info(f"Extracted {len(profiles)}/{len(leaders)} detailed profiles")
        return profiles

    def _build_leadership_extraction_prompt(self, ticker: str, filing_text: str) -> str:
        """Build prompt for extracting leadership team from 14A."""
        return f"""Analyze this DEF 14A (proxy statement) and extract comprehensive information about the company's leadership team.

Company Ticker: {ticker}

Your task:
1. Identify ALL members of the Board of Directors
2. Identify ALL Named Executive Officers (typically the top 5 highest-paid executives)
3. For each person, extract:
   - Full name and current title
   - Role type (Director, Executive Officer, C-Suite, etc.)
   - Age (if mentioned)
   - Tenure with the company
   - Compensation details (total comp, salary, bonus, stock awards)
   - Professional background and experience
   - Education
   - Other public company boards they serve on
   - Board committee memberships
   - Independence status (for directors)

4. Calculate summary statistics:
   - Total number of directors and executives
   - Number of independent directors
   - Average director tenure
   - Board diversity summary

Focus on accuracy and completeness. Extract all available data from the filing.

DEF 14A Content:
{filing_text[:50000]}
"""  # Limit to 50K chars to avoid token limits

    def _build_detailed_profile_prompt(
        self,
        leader: LeadershipMember,
        ticker: str,
        filing_text: Optional[str] = None
    ) -> str:
        """Build prompt for extracting detailed individual profile."""

        websearch_instruction = """
IMPORTANT: Use your web search capabilities to find additional information about this person:
- Recent news articles or interviews
- LinkedIn profile information
- Other current board seats or advisory roles
- Notable achievements and recognitions
- Educational background details
- Career progression and previous positions

Cross-reference information from the proxy statement with external sources to build a comprehensive profile.
"""

        filing_context = ""
        if filing_text:
            filing_context = f"""
Proxy Statement Context (for reference):
{filing_text[:20000]}

"""

        return f"""Create a comprehensive detailed profile for this executive/director.

Person: {leader.name}
Current Title: {leader.title}
Company: {ticker}
Role Type: {leader.role_type}

{filing_context}{websearch_instruction}

Provide a detailed analysis including:

1. Career History:
   - Complete timeline of previous positions and companies
   - Years at each position
   - Notable career transitions

2. Achievements & Recognition:
   - Major accomplishments
   - Awards or recognitions
   - Industry influence

3. Education:
   - All degrees with institutions and years
   - Notable academic achievements
   - Executive education programs

4. Current Roles & Influence:
   - Other current board seats
   - Advisory positions
   - Industry associations or non-profits

5. Recent Activity:
   - Recent news mentions
   - Interviews or public statements
   - Major decisions or initiatives

6. Leadership Analysis:
   - Leadership style and approach
   - Key strengths based on background
   - Any potential concerns or red flags

7. Compensation Context (if available):
   - How their compensation ranks vs industry peers
   - Pay for performance analysis
   - Compensation trends over time

Be thorough, objective, and fact-based. Cite sources when possible.
"""

    def analyze_leadership_quality(
        self,
        ticker: str,
        team: Optional[LeadershipTeam] = None,
        profiles: Optional[List[LeaderDetailedProfile]] = None
    ) -> Dict[str, Any]:
        """
        Perform high-level analysis of leadership team quality and governance.

        Args:
            ticker: Stock ticker symbol
            team: LeadershipTeam (extracted if not provided)
            profiles: Detailed profiles (extracted if not provided)

        Returns:
            Dict with leadership quality analysis
        """
        logger.info(f"Analyzing leadership quality for {ticker}")

        # Extract data if not provided
        if team is None:
            team = self.extract_leadership_team(ticker)

        if profiles is None:
            profiles = self.extract_detailed_profiles(ticker)

        # Build analysis prompt
        prompt = f"""Analyze the overall quality and effectiveness of this leadership team.

Company: {ticker}

Board of Directors ({len(team.board_of_directors)} members):
{json.dumps([d.model_dump() for d in team.board_of_directors], indent=2)}

Executive Officers ({len(team.executive_officers)} members):
{json.dumps([e.model_dump() for e in team.executive_officers], indent=2)}

Detailed Profiles:
{json.dumps([p.model_dump() for p in profiles], indent=2)}

Provide a comprehensive analysis covering:

1. Board Composition & Governance:
   - Board independence and diversity
   - Relevant expertise and experience
   - Potential conflicts of interest
   - Committee structure effectiveness

2. Executive Team Strength:
   - Depth of experience and track record
   - Alignment of skills with company strategy
   - Succession planning readiness
   - Team cohesion and tenure

3. Compensation Structure:
   - Pay for performance alignment
   - Comparison to industry peers
   - Incentive structure appropriateness
   - Red flags or concerns

4. Leadership Quality Assessment:
   - Overall team strength (1-10 rating with justification)
   - Key strengths of the leadership team
   - Areas of concern or weakness
   - Comparison to best-in-class governance

5. Investor Perspective:
   - How this leadership team affects investment thesis
   - Governance risks to monitor
   - Positive signals for long-term value creation

Be analytical, objective, and investment-focused.
"""

        provider = self._get_provider()
        result = provider.generate(prompt=prompt, max_retries=3)

        # Save analysis
        output_file = self.output_dir / f"{ticker}_leadership_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        logger.info(f"Leadership quality analysis saved to: {output_file}")
        return result


# Convenience function for quick scripting
def extract_leadership(ticker: str, detailed: bool = False) -> Dict[str, Any]:
    """
    Quick function to extract leadership data for a ticker.

    Args:
        ticker: Stock ticker symbol
        detailed: If True, includes detailed profiles for each leader

    Returns:
        Dict with leadership data

    Example:
        >>> data = extract_leadership("AAPL", detailed=True)
        >>> print(f"CEO: {data['team'].executive_officers[0].name}")
    """
    extractor = LeadershipExtractor()

    team = extractor.extract_leadership_team(ticker)
    result = {"team": team}

    if detailed:
        profiles = extractor.extract_detailed_profiles(ticker)
        result["profiles"] = profiles

        analysis = extractor.analyze_leadership_quality(ticker, team, profiles)
        result["analysis"] = analysis

    return result
