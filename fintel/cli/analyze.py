"""
Analyze command for single company analysis.

This module provides the CLI command for analyzing individual companies.
It delegates to the shared AnalysisService, ensuring the CLI and UI
execute analyses through the same code path.
"""

import click
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

from fintel.core import get_config, get_logger
from fintel.core.analysis_types import CLI_ANALYSIS_CHOICES, get_analysis_type
from fintel.ui.database import DatabaseRepository
from fintel.ui.services import AnalysisService, create_analysis_service

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("ticker")
@click.option("--years", "-y", default=5, help="Number of years to analyze (default: 5)")
@click.option(
    "--analysis-type",
    "-t",
    type=click.Choice(CLI_ANALYSIS_CHOICES, case_sensitive=False),
    default="fundamental",
    help="Type of analysis to perform",
)
@click.option(
    "--filing-type",
    "-f",
    default="10-K",
    show_default=True,
    help="SEC filing type to analyze (10-K, 20-F, 10-Q, 8-K, 4, DEF 14A, etc.)",
)
@click.option(
    "--input-mode",
    type=click.Choice(["ticker", "cik"], case_sensitive=False),
    default="ticker",
    show_default=True,
    help="Whether TICKER argument is a stock symbol or SEC CIK number",
)
@click.option("--company-name", default=None, help="Company name for display (optional)")
def analyze(
    ticker: str,
    years: int,
    analysis_type: str,
    filing_type: str,
    input_mode: str,
    company_name: Optional[str],
):
    """
    Analyze a company's SEC filings.

    Delegates to the shared AnalysisService used by both CLI and Web UI,
    ensuring identical analysis behaviour regardless of interface.

    \b
    ═══════════════════════════════════════════════════════════════
    ANALYSIS TYPES
    ═══════════════════════════════════════════════════════════════

    \b
    fundamental - Basic 10-K financial analysis
    excellent   - Multi-year excellence / success factors (3+ years)
    objective   - Multi-year unbiased assessment (3+ years)
    buffett     - Warren Buffett value investing lens
    taleb       - Nassim Taleb antifragility analysis
    contrarian  - Contrarian / skeptical analysis
    multi       - All three perspectives combined
    scanner     - Quick contrarian screening (3+ years)

    \b
    ═══════════════════════════════════════════════════════════════
    EXAMPLES
    ═══════════════════════════════════════════════════════════════

    \b
    # Basic fundamental analysis (last 5 years)
    fintel analyze AAPL

    \b
    # Analyze 10 years with multi-perspective
    fintel analyze AAPL --years 10 --analysis-type multi

    \b
    # Analyze foreign issuer 20-F filings
    fintel analyze TSM --filing-type 20-F --years 5

    \b
    # Analyze by CIK number
    fintel analyze 0001018724 --input-mode cik --years 5

    \b
    # Buffett lens on quarterly filings
    fintel analyze AAPL --analysis-type buffett --filing-type 10-Q --years 2
    """
    config = get_config()
    ticker = ticker.upper() if input_mode == "ticker" else ticker.strip()

    # Validate API keys
    if not config.google_api_keys:
        console.print(
            "[bold red]No Google API keys configured. "
            "Set GOOGLE_API_KEY_1 in .env[/bold red]"
        )
        raise click.Abort()

    # Validate min-years for multi-year types
    type_info = get_analysis_type(analysis_type)
    if type_info and type_info.min_years > 1 and years < type_info.min_years:
        console.print(
            f"[bold red]{analysis_type} analysis requires at least "
            f"{type_info.min_years} years (got {years})[/bold red]"
        )
        raise click.Abort()

    # Display header
    display_id = ticker if input_mode == "ticker" else f"CIK:{ticker}"
    analysis_label = type_info.name if type_info else analysis_type
    console.print(
        Panel.fit(
            f"[bold cyan]Analyzing {display_id}[/bold cyan]\n"
            f"Years: {years} | Analysis: {analysis_label}\n"
            f"Filing: {filing_type} | Mode: {input_mode}",
            title="Fintel Analysis",
        )
    )

    # Initialize shared services (same code path as web UI)
    db = DatabaseRepository()
    service = create_analysis_service(db, config)

    # Build year list
    current_year = datetime.now().year
    year_list = list(range(current_year, current_year - years, -1))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Running {analysis_label} for {display_id}...", total=None
            )

            # Delegate to AnalysisService — the single source of truth
            # for download → cache → convert → analyze → store
            run_id = service.run_analysis(
                ticker=ticker,
                analysis_type=analysis_type,
                filing_type=filing_type,
                years=year_list,
                num_years=years,
                company_name=company_name,
                input_mode=input_mode,
            )

            progress.update(task, completed=True)

        # Show results summary
        status = service.get_analysis_status(run_id)
        results = status.get("results", [])
        years_done = len(results) if results else 0

        console.print(
            Panel.fit(
                f"[bold green]Analysis Complete![/bold green]\n"
                f"Ticker: {display_id}\n"
                f"Analysis: {analysis_label}\n"
                f"Years analysed: {years_done}\n"
                f"Run ID: {run_id}\n\n"
                f"[dim]View results via the web UI (streamlit run streamlit_app.py) "
                f"or 'fintel export'.[/dim]",
                title="Success",
            )
        )

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Analysis interrupted by user[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Analysis failed: {e}[/bold red]")
        logger.exception("Analysis failed")
        raise click.Abort()
