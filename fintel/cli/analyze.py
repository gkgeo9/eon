"""
Analyze command for single company analysis.

This module provides the CLI command for analyzing individual companies
with various analysis types.
"""

import click
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from fintel.core import get_config, get_logger
from fintel.data.sources.sec import SECDownloader, SECConverter
from fintel.analysis.fundamental import FundamentalAnalyzer, TenKAnalysis
from fintel.analysis.perspectives import PerspectiveAnalyzer
from fintel.ai import APIKeyManager, RateLimiter
from fintel.ui.database import DatabaseRepository

console = Console()
logger = get_logger(__name__)


def _get_cached_pdfs(
    db: DatabaseRepository,
    ticker: str,
    filing_type: str,
    years: List[int]
) -> Dict[int, Path]:
    """
    Check cache for existing PDFs.

    Args:
        db: Database repository
        ticker: Company ticker symbol
        filing_type: Filing type (10-K, etc.)
        years: List of years to check

    Returns:
        Dictionary mapping year to cached PDF path
    """
    cached_pdfs = {}

    for year in years:
        cached_path = db.get_cached_file(ticker, year, filing_type)
        if cached_path:
            path = Path(cached_path)
            if path.exists():
                logger.info(f"[CACHE HIT] Using cached PDF for {ticker} {year}: {cached_path}")
                cached_pdfs[year] = path
            else:
                # Stale cache entry - file missing
                logger.warning(f"[CACHE STALE] Cached file missing for {ticker} {year}, clearing entry")
                db.clear_file_cache_entry(ticker, year, filing_type)

    return cached_pdfs


def _cache_new_pdfs(
    db: DatabaseRepository,
    ticker: str,
    filing_type: str,
    pdf_info_list: List[Dict]
) -> None:
    """
    Cache newly downloaded PDFs.

    Args:
        db: Database repository
        ticker: Company ticker symbol
        filing_type: Filing type
        pdf_info_list: List of dicts with pdf_path, year, filing_date
    """
    for pdf_info in pdf_info_list:
        year = pdf_info.get('year')
        pdf_path = pdf_info.get('pdf_path')
        filing_date = pdf_info.get('filing_date')

        if year and pdf_path:
            db.cache_file(
                ticker=ticker,
                fiscal_year=year,
                filing_type=filing_type,
                file_path=str(pdf_path),
                filing_date=filing_date
            )
            logger.info(f"[CACHE STORED] {ticker} {year} ({filing_type}): {pdf_path}")


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
    filing_type = "10-K"

    # Initialize database for cache
    db = DatabaseRepository()

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

            # Calculate years to analyze
            current_year = datetime.now().year
            requested_years = list(range(current_year, current_year - years, -1))

            # Step 1: Check cache first
            task = progress.add_task(f"Checking cache for {ticker}...", total=None)
            cached_pdfs = _get_cached_pdfs(db, ticker, filing_type, requested_years)
            progress.update(task, completed=True)

            if cached_pdfs:
                console.print(f"[green] Found {len(cached_pdfs)} cached PDFs: {sorted(cached_pdfs.keys(), reverse=True)}[/green]")

            # Determine which years still need downloading
            years_to_download = [y for y in requested_years if y not in cached_pdfs]

            # Step 2: Download only uncached years
            pdf_info_new = []
            filing_path = None

            if years_to_download and not skip_download:
                task = progress.add_task(f"Downloading {len(years_to_download)} {filing_type} filings for {ticker}...", total=None)

                downloader = SECDownloader(
                    company_name="Fintel CLI",
                    user_email=config.sec_user_email if hasattr(config, 'sec_user_email') else "user@example.com"
                )

                filing_path = downloader.download(ticker, num_filings=len(years_to_download))
                progress.update(task, completed=True)
                console.print(f" Downloaded to {filing_path}", style="green")

                # Step 3: Convert HTML to PDF (only for new downloads)
                if not skip_convert:
                    task = progress.add_task(f"Converting HTML to PDF...", total=None)

                    with SECConverter() as converter:
                        # convert() returns list of dicts with pdf_path, year, etc.
                        pdf_info_new = converter.convert(
                            ticker=ticker,
                            input_path=filing_path,
                            filing_type=filing_type
                        )

                    progress.update(task, completed=True)
                    console.print(f" Converted {len(pdf_info_new)} filings to PDF", style="green")

                    # Cache the newly downloaded PDFs
                    _cache_new_pdfs(db, ticker, filing_type, pdf_info_new)

            elif skip_download:
                filing_path = config.data_dir / "sec-edgar-filings" / ticker / filing_type
                console.print(f"[yellow]Skipped download, using {filing_path}[/yellow]")

                if not skip_convert and filing_path.exists():
                    task = progress.add_task(f"Converting HTML to PDF...", total=None)

                    with SECConverter() as converter:
                        pdf_info_new = converter.convert(
                            ticker=ticker,
                            input_path=filing_path,
                            filing_type=filing_type
                        )

                    progress.update(task, completed=True)
                    console.print(f" Converted {len(pdf_info_new)} filings to PDF", style="green")

                    # Cache the newly converted PDFs
                    _cache_new_pdfs(db, ticker, filing_type, pdf_info_new)

            elif not years_to_download:
                console.print(f"[green] All {len(cached_pdfs)} requested filings found in cache - no download needed[/green]")

            # Combine cached and newly converted PDFs
            pdf_paths = list(cached_pdfs.values())
            for p in pdf_info_new:
                if p.get('pdf_path'):
                    pdf_paths.append(Path(p['pdf_path']))

            # Handle skip_convert case for finding existing PDFs
            if skip_convert and not pdf_paths:
                if filing_path and filing_path.exists():
                    pdf_paths = list(filing_path.rglob("*.pdf"))
                else:
                    # Try default location
                    default_path = config.data_dir / "sec-edgar-filings" / ticker / filing_type
                    if default_path.exists():
                        pdf_paths = list(default_path.rglob("*.pdf"))
                if pdf_paths:
                    console.print(f"[yellow]Skipped conversion, found {len(pdf_paths)} PDFs[/yellow]")

            if not pdf_paths:
                console.print(" No PDF files found. Cannot proceed with analysis.", style="bold red")
                return

            # Initialize AI components
            if not config.google_api_keys:
                console.print(" No Google API keys configured. Set GOOGLE_API_KEY_1 in .env", style="bold red")
                return

            key_mgr = APIKeyManager(config.google_api_keys)
            rate_limiter = RateLimiter(sleep_after_request=config.sleep_after_request)

            # Step 4: Perform Analysis
            if analysis_type in ["fundamental", "both"]:
                task = progress.add_task(f"Analyzing fundamentals (AI-powered)...", total=len(pdf_paths))

                analyzer = FundamentalAnalyzer(
                    api_key_manager=key_mgr,
                    rate_limiter=rate_limiter
                )

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
                        console.print(f"   Analyzed {year}", style="green")
                    else:
                        console.print(f"   Failed to analyze {year}", style="red")

                    progress.update(task, advance=1)

                console.print(f" Fundamental analysis complete", style="bold green")

            if analysis_type in ["perspectives", "both"]:
                task = progress.add_task(f"Analyzing perspectives (Buffett, Taleb, Contrarian)...", total=len(pdf_paths))

                perspective_analyzer = PerspectiveAnalyzer(
                    api_key_manager=key_mgr,
                    rate_limiter=rate_limiter
                )

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
                        console.print(f"   Analyzed {year} (3 perspectives)", style="green")
                    else:
                        console.print(f"   Failed perspective analysis {year}", style="red")

                    progress.update(task, advance=1)

                console.print(f" Perspective analysis complete", style="bold green")

        # Summary
        console.print(Panel.fit(
            f"[bold green]Analysis Complete![/bold green]\n"
            f"Ticker: {ticker}\n"
            f"Results saved to: {output_path}",
            title="Success"
        ))

    except KeyboardInterrupt:
        console.print("\n Analysis interrupted by user", style="bold yellow")
    except Exception as e:
        console.print(f"\n Analysis failed: {e}", style="bold red")
        logger.exception("Analysis failed")
        raise click.Abort()
