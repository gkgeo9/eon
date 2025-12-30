"""
CUSTOM ANALYSIS TEMPLATE

Simple template for custom SEC filing analysis.
Copy this file and modify the schema and prompt for your specific use case.

Usage:
    python experimentation/custom_analysis_template.py TICKER
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


# ============================================================================
# CUSTOMIZE THIS: Define your Pydantic schema for what you want to extract
# ============================================================================

class YourCustomAnalysis(BaseModel):
    """
    Define whatever fields you want to extract from the filing.
    The AI will extract data matching this schema.
    """
    company_name: str = Field(description="Company name")
    ticker: str = Field(description="Stock ticker")

    # Add your custom fields here
    summary: str = Field(description="Brief summary of the filing")
    key_points: List[str] = Field(description="Key points from the filing")

    # Example: Extract specific information
    # risk_factors: List[str] = Field(description="Main risk factors")
    # revenue: Optional[float] = Field(None, description="Revenue if mentioned")


# ============================================================================
# CUSTOMIZE THIS: Define your analysis prompt
# ============================================================================

def build_prompt(ticker: str, filing_text: str, filing_type: str = "DEF 14A") -> str:
    """
    Build your custom prompt.

    Args:
        ticker: Stock ticker
        filing_text: Full text of the filing
        filing_type: Type of filing (DEF 14A, 10-K, etc.)

    Returns:
        Prompt string
    """
    return f"""Analyze this {filing_type} filing for {ticker}.

YOUR CUSTOM INSTRUCTIONS HERE:
- What do you want the AI to extract?
- What should it focus on?
- What analysis should it perform?

Use Google Search to find additional information if needed.

Filing Content:
{filing_text[:100000]}
"""


# ============================================================================
# Main extraction function (usually don't need to modify this)
# ============================================================================

def analyze_filing(
    ticker: str,
    filing_type: str = "DEF 14A",
    num_filings: int = 1,
    model: str = "gemini-3-pro-preview",
    thinking_level: str = "HIGH",
    use_google_search: bool = True,
    save_json: bool = True
) -> YourCustomAnalysis:
    """
    Download and analyze SEC filing.

    Args:
        ticker: Stock ticker (e.g., "AAPL")
        filing_type: SEC filing type (e.g., "DEF 14A", "10-K", "10-Q")
        num_filings: Number of recent filings to download
        model: Gemini model to use
        thinking_level: "LOW", "MEDIUM", or "HIGH"
        use_google_search: Enable Google Search tool
        save_json: Save results to JSON file

    Returns:
        Your custom analysis result
    """
    config = get_config()

    print(f"\n{'='*80}")
    print(f"Analyzing {filing_type} for {ticker}")
    print(f"{'='*80}\n")

    # Download filing
    print(f"Downloading {filing_type} filing...")
    downloader = SECDownloader(
        company_name=config.sec_company_name,
        user_email=config.sec_user_email
    )
    filing_path = downloader.download(ticker, num_filings=num_filings, filing_type=filing_type)
    print(f"✓ Downloaded\n")

    # Convert to PDF
    print("Converting to PDF...")
    converter = SECConverter()
    pdfs = converter.convert(ticker, filing_path, filing_type=filing_type)
    pdf_path = Path(pdfs[0]['pdf_path'])
    print(f"✓ Converted: {pdf_path.name}\n")

    # Extract text
    print("Extracting text...")
    extractor = PDFExtractor()
    text = extractor.extract_text(pdf_path)
    print(f"✓ Extracted {len(text):,} characters\n")

    # Build prompt
    prompt = build_prompt(ticker, text, filing_type)

    # Analyze with AI
    print(f"Analyzing with {model} (thinking_level={thinking_level})...")

    client = genai.Client(api_key=config.google_api_keys[0])

    # Build config
    config_params = {
        'thinkingConfig': {
            'thinkingLevel': thinking_level,
        },
        'response_mime_type': "application/json",
        'response_schema': YourCustomAnalysis,
    }

    if use_google_search:
        config_params['tools'] = [types.Tool(googleSearch=types.GoogleSearch())]

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_params),
    )

    # Parse response
    result = YourCustomAnalysis.model_validate_json(response.text)
    print(f"✓ Analysis complete\n")

    # Save to JSON
    if save_json:
        output_dir = Path("data/experimentation/custom_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{ticker}_{filing_type.replace(' ', '_')}_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result.model_dump(), f, indent=2)

        print(f"✓ Saved to: {output_file}\n")

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python experimentation/custom_analysis_template.py TICKER [FILING_TYPE]")
        print("Example: python experimentation/custom_analysis_template.py AAPL")
        print("Example: python experimentation/custom_analysis_template.py AAPL '10-K'")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    filing_type = sys.argv[2] if len(sys.argv) > 2 else "DEF 14A"

    # Run analysis
    result = analyze_filing(ticker, filing_type=filing_type)

    # Display results
    print(f"{'='*80}")
    print(f"RESULTS: {result.company_name} ({ticker})")
    print(f"{'='*80}\n")

    print(json.dumps(result.model_dump(), indent=2))

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
