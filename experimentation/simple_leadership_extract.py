"""
Simple script to extract leadership from 14A filings.

Usage:
    python experimentation/simple_leadership_extract.py AAPL
"""

import sys
import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from fintel.core import get_config
from fintel.data.sources.sec import SECDownloader, SECConverter, PDFExtractor


# Pydantic schemas
class Leader(BaseModel):
    """Individual leader from 14A filing."""
    name: str = Field(description="Full name")
    title: str = Field(description="Current title/position")
    role_type: str = Field(description="Director, Executive, C-Suite, etc.")
    age: Optional[int] = Field(None, description="Age if mentioned")
    tenure_years: Optional[float] = Field(None, description="Years with company")
    total_compensation: Optional[float] = Field(None, description="Total compensation in USD")
    background: Optional[str] = Field(None, description="Professional background")
    other_boards: Optional[List[str]] = Field(None, description="Other boards they serve on")
    independence_status: Optional[str] = Field(None, description="Independent or Non-Independent")


class LeadershipAnalysis(BaseModel):
    """Complete leadership analysis from 14A."""
    company_name: str = Field(description="Company name")
    ticker: str = Field(description="Stock ticker")
    fiscal_year: int = Field(description="Fiscal year")

    directors: List[Leader] = Field(description="Board of directors", default_factory=list)
    executives: List[Leader] = Field(description="Executive officers", default_factory=list)

    total_directors: int = Field(description="Total number of directors")
    total_executives: int = Field(description="Total named executive officers")
    independent_directors: Optional[int] = Field(None, description="Number of independent directors")


def extract_leadership(ticker: str, save_json: bool = True) -> LeadershipAnalysis:
    """
    Extract leadership from 14A filing.

    Args:
        ticker: Stock ticker (e.g., "AAPL")
        save_json: Save results to JSON file

    Returns:
        LeadershipAnalysis with all directors and executives
    """
    config = get_config()

    print(f"\n{'='*80}")
    print(f"Extracting Leadership for {ticker}")
    print(f"{'='*80}\n")

    # Step 1: Download 14A
    print("Step 1: Downloading DEF 14A filing...")
    downloader = SECDownloader(
        company_name=config.sec_company_name,
        user_email=config.sec_user_email
    )
    filing_path = downloader.download(ticker, num_filings=1, filing_type="DEF 14A")
    print(f"✓ Downloaded to: {filing_path}\n")

    # Step 2: Convert to PDF
    print("Step 2: Converting to PDF...")
    converter = SECConverter()
    pdfs = converter.convert(ticker, filing_path, filing_type="DEF 14A")
    pdf_path = Path(pdfs[0]['pdf_path'])
    year = pdfs[0]['year']
    print(f"✓ Converted: {pdf_path.name}\n")

    # Step 3: Extract text
    print("Step 3: Extracting text from PDF...")
    extractor = PDFExtractor()
    text = extractor.extract_text(pdf_path)
    print(f"✓ Extracted {len(text):,} characters\n")

    # Step 4: Analyze with AI
    print("Step 4: Analyzing with Gemini 3 + Google Search...")

    prompt = f"""Analyze this DEF 14A (proxy statement) and extract all leadership information.

Company Ticker: {ticker}

Extract:
1. ALL Board of Directors members
2. ALL Named Executive Officers (top executives)
3. For each person:
   - Name, title, role type
   - Age, tenure with company
   - Total compensation (if shown)
   - Professional background
   - Other public company boards
   - Independence status (for directors)

Use Google Search to verify names and get additional context about each leader.

DEF 14A Filing:
{text}
"""

    # Initialize Gemini 3 with Google Search
    client = genai.Client(api_key=config.google_api_keys[0])

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            # thinkingConfig={
            #     'thinkingLevel': 'HIGH',
            # },
            tools=[types.Tool(googleSearch=types.GoogleSearch())],
            # response_mime_type="application/json",
            response_schema=LeadershipAnalysis,
        ),
    )

    # Parse response
    print(response.text)
    result = LeadershipAnalysis.model_validate_json(response.text)
    print(f"✓ Extracted {len(result.directors)} directors and {len(result.executives)} executives\n")

    # Step 5: Save to JSON
    if save_json:
        output_dir = Path("data/experimentation/leadership")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{ticker}_leadership.json"
        with open(output_file, 'w') as f:
            json.dump(result.model_dump(), f, indent=2)

        print(f"✓ Saved to: {output_file}\n")

    return result


def main():
    """CLI entry point."""
    # if len(sys.argv) < 2:
    #     print("Usage: python experimentation/simple_leadership_extract.py TICKER")
    #     print("Example: python experimentation/simple_leadership_extract.py AAPL")
    #     sys.exit(1)

    ticker = "SDGR"

    # Extract leadership
    result = extract_leadership(ticker)

    # Display results
    print(f"{'='*80}")
    print(f"RESULTS: {result.company_name} ({ticker})")
    print(f"{'='*80}\n")

    print(f"Fiscal Year: {result.fiscal_year}")
    print(f"Total Directors: {result.total_directors}")
    print(f"Total Executives: {result.total_executives}")
    if result.independent_directors:
        print(f"Independent Directors: {result.independent_directors}")

    print(f"\n--- Board of Directors ({len(result.directors)}) ---")
    for i, director in enumerate(result.directors, 1):
        print(f"\n{i}. {director.name}")
        print(f"   Title: {director.title}")
        if director.age:
            print(f"   Age: {director.age}")
        if director.tenure_years:
            print(f"   Tenure: {director.tenure_years} years")
        if director.independence_status:
            print(f"   Status: {director.independence_status}")
        if director.other_boards:
            print(f"   Other Boards: {', '.join(director.other_boards[:3])}")

    print(f"\n--- Executive Officers ({len(result.executives)}) ---")
    for i, exec in enumerate(result.executives, 1):
        print(f"\n{i}. {exec.name}")
        print(f"   Title: {exec.title}")
        if exec.total_compensation:
            print(f"   Total Comp: ${exec.total_compensation:,.0f}")
        if exec.tenure_years:
            print(f"   Tenure: {exec.tenure_years} years")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
