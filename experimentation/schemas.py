"""
Pydantic schemas for leadership extraction from 14A proxy statements.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class LeadershipMember(BaseModel):
    """Individual leadership team member extracted from 14A filing."""

    name: str = Field(description="Full name of the leadership member")
    title: str = Field(description="Current title/position in the company")
    role_type: str = Field(description="Role category: 'Director', 'Executive Officer', 'C-Suite', 'Board Chair', etc.")
    age: Optional[int] = Field(None, description="Age if mentioned in the filing")
    tenure_years: Optional[float] = Field(None, description="Years with the company if mentioned")

    # Compensation info (if in 14A)
    total_compensation: Optional[float] = Field(None, description="Total compensation in USD")
    salary: Optional[float] = Field(None, description="Base salary in USD")
    bonus: Optional[float] = Field(None, description="Bonus amount in USD")
    stock_awards: Optional[float] = Field(None, description="Stock awards value in USD")

    # Background
    background: Optional[str] = Field(None, description="Professional background and experience")
    education: Optional[str] = Field(None, description="Educational background")
    other_boards: Optional[List[str]] = Field(None, description="Other public company boards they serve on")

    # Governance
    committee_memberships: Optional[List[str]] = Field(None, description="Board committees they serve on")
    independence_status: Optional[str] = Field(None, description="Independent, Non-Independent, or N/A")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jane Smith",
                "title": "Chief Executive Officer",
                "role_type": "C-Suite",
                "age": 55,
                "tenure_years": 8.5,
                "total_compensation": 15000000,
                "background": "Former CEO of XYZ Corp, 20 years in tech industry",
                "committee_memberships": ["Executive Committee"],
                "independence_status": "Non-Independent"
            }
        }


class LeadershipTeam(BaseModel):
    """Complete leadership team extracted from 14A proxy statement."""

    company_name: str = Field(description="Company name")
    ticker: str = Field(description="Stock ticker symbol")
    fiscal_year: int = Field(description="Fiscal year of the proxy statement")
    filing_date: Optional[str] = Field(None, description="Date of the 14A filing")

    board_of_directors: List[LeadershipMember] = Field(
        description="All board of directors members",
        default_factory=list
    )

    executive_officers: List[LeadershipMember] = Field(
        description="Named executive officers (typically top 5)",
        default_factory=list
    )

    total_directors: int = Field(description="Total number of directors")
    total_executives: int = Field(description="Total number of named executive officers")

    # Governance metrics
    independent_directors_count: Optional[int] = Field(None, description="Number of independent directors")
    board_diversity_summary: Optional[str] = Field(None, description="Summary of board diversity")
    average_director_tenure: Optional[float] = Field(None, description="Average tenure of directors in years")

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "fiscal_year": 2024,
                "board_of_directors": [],
                "executive_officers": [],
                "total_directors": 8,
                "total_executives": 5
            }
        }


class LeaderDetailedProfile(BaseModel):
    """Detailed profile of an individual leader with external research."""

    # Basic info (from 14A)
    name: str = Field(description="Full name")
    current_title: str = Field(description="Current title at the company")
    current_company: str = Field(description="Current company ticker/name")

    # Extended background research
    career_history: Optional[List[str]] = Field(None, description="List of previous positions and companies")
    notable_achievements: Optional[List[str]] = Field(None, description="Key achievements and recognitions")
    education_details: Optional[List[str]] = Field(None, description="Degrees, institutions, and years")

    # External presence
    linkedin_summary: Optional[str] = Field(None, description="Summary from LinkedIn or similar")
    other_current_roles: Optional[List[str]] = Field(None, description="Current board seats, advisory roles, etc.")
    recent_news: Optional[List[str]] = Field(None, description="Recent news mentions or interviews")

    # Analysis
    leadership_style: Optional[str] = Field(None, description="Assessment of leadership style and approach")
    key_strengths: Optional[List[str]] = Field(None, description="Key strengths based on background")
    potential_concerns: Optional[List[str]] = Field(None, description="Any potential red flags or concerns")

    # Compensation context
    compensation_rank: Optional[str] = Field(None, description="How their comp ranks vs peers in industry")
    pay_for_performance: Optional[str] = Field(None, description="Analysis of pay vs company performance")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Tim Cook",
                "current_title": "Chief Executive Officer",
                "current_company": "AAPL",
                "career_history": ["COO Apple (2007-2011)", "CEO Apple (2011-present)"],
                "notable_achievements": ["Led Apple to $2T+ market cap", "Expanded services revenue"],
                "leadership_style": "Operational excellence focused, consensus builder"
            }
        }
