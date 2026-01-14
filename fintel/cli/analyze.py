"""
Analyze command for single company analysis.

This module provides the CLI command for analyzing individual companies
with various analysis types.
"""

import click
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from fintel.core import get_config, get_logger
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.fundamental import FundamentalAnalyzer, TenKAnalysis
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.ai import APIKeyManager, RateLimiter

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("ticker")
@click.option("--years", "-y", default=5, help="Number of years to analyze (default: 5)")
@click.option(
    "--analysis-type",
    "-t",
    type=click.Choice(["fundamental", "perspectives", "both"], case_sensitive=False),
    default="fundamental",
    help="Type of analysis to perform"
)
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory (default: ./data/processed)")
@click.option("--skip-download", is_flag=True, help="Skip download step if files already exist")
@click.option("--skip-convert", is_flag=True, help="Skip HTML to PDF conversion if PDFs exist")
def analyze(
    ticker: str,
    years: int,
    analysis_type: str,
    output_dir: str,
    skip_download: bool,
    skip_convert: bool
):
    """
    Analyze a single company's SEC 10-K filings.

    This command downloads, converts, and analyzes SEC 10-K filings for a given
    ticker symbol. Supports fundamental analysis and multi-perspective analysis.

    Examples:

      # Basic fundamental analysis
      fintel analyze AAPL

      # Analyze 10 years with perspectives
      fintel analyze AAPL --years 10 --analysis-type perspectives

      # Both analysis types
      fintel analyze AAPL --analysis-type both

      # Skip download if files exist
      fintel analyze AAPL --skip-download
    """
    config = get_config()
    ticker = ticker.upper()

    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = config.data_dir / "processed" / ticker

    output_path.mkdir(parents=True, exist_ok=True)

    console.print(Panel.fit(
        f"[bold cyan]Analyzing {ticker}[/bold cyan]\n"
        f"Years: {years} | Analysis: {analysis_type}",
        title="Fintel Analysis"
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Step 1: Download
            if not skip_download:
                task = progress.add_task(f"Downloading {years} 10-K filings for {ticker}...", total=None)

                downloader = SECDownloader(
                    company_name="Fintel CLI",
                    user_email=config.sec_user_email if hasattr(config, 'sec_user_email') else "user@example.com"
                )

                filing_path = downloader.download(ticker, num_filings=years)
                progress.update(task, completed=True)
                console.print(f" Downloaded to {filing_path}", style="green")
            else:
                filing_path = config.data_dir / "sec-edgar-filings" / ticker / "10-K"
                console.print(f"� Skipped download, using {filing_path}", style="yellow")

            # Step 2: Convert HTML to PDF
            if not skip_convert:
                task = progress.add_task(f"Converting HTML to PDF...", total=None)

                with SECConverter() as converter:
                    # convert() returns list of dicts with pdf_path, year, etc.
                    pdf_info = converter.convert(
                        ticker=ticker,
                        input_path=filing_path,
                        filing_type="10-K"
                    )
                    # Extract paths for analysis
                    pdf_paths = [Path(p['pdf_path']) for p in pdf_info if p.get('pdf_path')]

                progress.update(task, completed=True)
                console.print(f" Converted {len(pdf_paths)} filings to PDF", style="green")
            else:
                pdf_paths = list(filing_path.rglob("*.pdf"))
                console.print(f"� Skipped conversion, found {len(pdf_paths)} PDFs", style="yellow")

            if not pdf_paths:
                console.print(" No PDF files found. Cannot proceed with analysis.", style="bold red")
                return

            # Initialize AI components
            if not config.google_api_keys:
                console.print(" No Google API keys configured. Set GOOGLE_API_KEY_1 in .env", style="bold red")
                return

            key_mgr = APIKeyManager(config.google_api_keys)
            rate_limiter = RateLimiter(sleep_after_request=config.sleep_after_request)

            # Step 3: Perform Analysis
            if analysis_type in ["fundamental", "both"]:
                task = progress.add_task(f"Analyzing fundamentals (AI-powered)...", total=len(pdf_paths))

                analyzer = FundamentalAnalyzer(
                    api_key_manager=key_mgr,
                    rate_limiter=rate_limiter
                )

                current_year = datetime.now().year
                for i, pdf_path in enumerate(sorted(pdf_paths)[:years]):
                    # Extract year from filename if possible
                    try:
                        year = int(pdf_path.stem.split("-")[0])
                    except (ValueError, IndexError):
                        year = current_year - i

                    result = analyzer.analyze_filing(
                        pdf_path=pdf_path,
                        ticker=ticker,
                        year=year,
                        schema=TenKAnalysis,
                        output_dir=output_path / "fundamental"
                    )

                    if result:
                        console.print(f"   Analyzed {year}", style="green")
                    else:
                        console.print(f"   Failed to analyze {year}", style="red")

                    progress.update(task, advance=1)

                console.print(f" Fundamental analysis complete", style="bold green")

            if analysis_type in ["perspectives", "both"]:
                task = progress.add_task(f"Analyzing perspectives (Buffett, Taleb, Contrarian)...", total=len(pdf_paths))

                perspective_analyzer = PerspectiveAnalyzer(
                    api_key_manager=key_mgr,
                    rate_limiter=rate_limiter
                )

                current_year = datetime.now().year
                for i, pdf_path in enumerate(sorted(pdf_paths)[:years]):
                    try:
                        year = int(pdf_path.stem.split("-")[0])
                    except (ValueError, IndexError):
                        year = current_year - i

                    result = perspective_analyzer.analyze_multi_perspective(
                        pdf_path=pdf_path,
                        ticker=ticker,
                        year=year,
                        output_dir=output_path / "perspectives"
                    )

                    if result:
                        console.print(f"   Analyzed {year} (3 perspectives)", style="green")
                    else:
                        console.print(f"   Failed perspective analysis {year}", style="red")

                    progress.update(task, advance=1)

                console.print(f" Perspective analysis complete", style="bold green")

        # Summary
        console.print(Panel.fit(
            f"[bold green]Analysis Complete![/bold green]\n"
            f"Ticker: {ticker}\n"
            f"Results saved to: {output_path}",
            title="Success"
        ))

    except KeyboardInterrupt:
        console.print("\n Analysis interrupted by user", style="bold yellow")
    except Exception as e:
        console.print(f"\n Analysis failed: {e}", style="bold red")
        logger.exception("Analysis failed")
        raise click.Abort()
