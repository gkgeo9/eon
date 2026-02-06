"""
Scan command for contrarian opportunity scanning.

This module provides the CLI command for scanning companies for contrarian
investment opportunities using the alpha score methodology.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

from fintel.core import get_config, get_logger
from fintel.cli.utils import read_ticker_file
from fintel.analysis.comparative import ContrarianScanner
from fintel.ui.database import DatabaseRepository
from fintel.ui.services import create_analysis_service

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("ticker-file", type=click.Path(exists=True))
@click.option("--min-score", "-m", default=70, help="Minimum alpha score threshold (default: 70)")
@click.option("--output", "-o", type=click.Path(), help="Output CSV file path")
@click.option("--success-factors-dir", "-d", type=click.Path(), help="Directory with pre-computed success factors")
@click.option("--top-n", "-n", default=20, help="Show top N opportunities (default: 20)")
@click.option("--min-confidence", type=click.Choice(["HIGH", "MEDIUM", "LOW"], case_sensitive=False), help="Minimum confidence level")
def scan_contrarian(
    ticker_file: str,
    min_score: int,
    output: str,
    success_factors_dir: str,
    top_n: int,
    min_confidence: str
):
    """
    Scan companies for contrarian investment opportunities.

    Analyzes companies using multi-year success factor analysis to identify
    hidden gems with strong "alpha" potential. Scores companies on six
    dimensions: strategic anomaly, asymmetric resources, contrarian positioning,
    cross-industry DNA, early infrastructure, and intellectual capital.

    The ticker file should contain one ticker per line, or be a CSV with a
    'ticker' or 'symbol' column.

    Examples:

      # Scan companies with minimum alpha score of 75
      fintel scan-contrarian tickers.csv --min-score 75

      # Show top 10 high-confidence opportunities
      fintel scan-contrarian tickers.csv --top-n 10 --min-confidence HIGH

      # Use pre-computed success factors
      fintel scan-contrarian tickers.csv --success-factors-dir ./factors

      # Export results to CSV
      fintel scan-contrarian tickers.csv --output gems.csv --min-score 80
    """
    config = get_config()

    # Read ticker list using shared utility
    ticker_path = Path(ticker_file)
    try:
        tickers = read_ticker_file(ticker_path)
    except ValueError as e:
        console.print(f"Error: {e}", style="bold red")
        return

    if not tickers:
        console.print(f"Error: No tickers found in {ticker_file}", style="bold red")
        return

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = config.data_dir / "contrarian_opportunities.csv"

    # Success factors directory
    factors_dir = Path(success_factors_dir) if success_factors_dir else None

    # Display scan info
    console.print(Panel.fit(
        f"[bold cyan]Contrarian Opportunity Scanner[/bold cyan]\n"
        f"Companies: {len(tickers)}\n"
        f"Minimum Alpha Score: {min_score}\n"
        f"Top N to Display: {top_n}\n"
        f"Min Confidence: {min_confidence or 'Any'}",
        title="Fintel Scanner"
    ))

    try:
        # Initialize shared service — reuses the same API key manager and rate
        # limiter that the rest of the CLI and UI use, ensuring consistent key
        # rotation and rate limiting across all commands.
        if not config.google_api_keys:
            console.print("No Google API keys configured. Set GOOGLE_API_KEY_1 in .env", style="bold red")
            return

        db = DatabaseRepository()
        service = create_analysis_service(db, config)

        # Create scanner using the service's shared components
        scanner = ContrarianScanner(
            api_key_manager=service.api_key_manager,
            rate_limiter=service.rate_limiter
        )

        # Scan companies
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                f"Scanning {len(tickers)} companies for alpha...",
                total=len(tickers)
            )

            df = scanner.scan_companies(
                tickers=tickers,
                success_factors_dir=factors_dir,
                min_score=min_score
            )

            # Update progress manually since we don't have callbacks
            progress.update(task, completed=len(tickers))

        if df.empty:
            console.print(
                f"\n⚠ No companies met the criteria (min score: {min_score})",
                style="yellow"
            )
            return

        # Export full results
        scanner.export_rankings(df, output_path, format="csv")

        # Get top opportunities
        top_df = scanner.get_top_opportunities(
            df=df,
            top_n=top_n,
            min_confidence=min_confidence
        )

        # Display top opportunities table
        _display_opportunities_table(top_df)

        console.print(Panel.fit(
            f"[bold green]Scan Complete![/bold green]\n"
            f"Found: {len(df)} opportunities (alpha score >= {min_score})\n"
            f"Results saved to: {output_path}",
            title="Success"
        ))

    except KeyboardInterrupt:
        console.print("\n✗ Scan interrupted by user", style="bold yellow")
    except Exception as e:
        console.print(f"\n✗ Scan failed: {e}", style="bold red")
        logger.exception("Contrarian scan failed")
        raise click.Abort()




def _display_opportunities_table(df) -> None:
    """
    Display top opportunities in a rich table.

    Args:
        df: DataFrame with top opportunities
    """
    table = Table(title="Top Contrarian Opportunities", show_lines=True)

    table.add_column("Rank", style="cyan", justify="right")
    table.add_column("Ticker", style="bold green")
    table.add_column("Company", style="white")
    table.add_column("Alpha\nScore", justify="right", style="bold yellow")
    table.add_column("Strategic\nAnomaly", justify="right")
    table.add_column("Asymmetric\nResources", justify="right")
    table.add_column("Contrarian\nPositioning", justify="right")
    table.add_column("Confidence", style="cyan")

    for idx, row in df.iterrows():
        # Color code alpha score
        alpha_score = row["alpha_score"]
        if alpha_score >= 80:
            score_style = "bold green"
        elif alpha_score >= 70:
            score_style = "green"
        elif alpha_score >= 60:
            score_style = "yellow"
        else:
            score_style = "white"

        table.add_row(
            str(idx + 1),
            row["ticker"],
            row.get("company_name", "")[:30],  # Truncate long names
            f"[{score_style}]{alpha_score}[/{score_style}]",
            str(row["strategic_anomaly"]),
            str(row["asymmetric_resources"]),
            str(row["contrarian_positioning"]),
            row["confidence_level"]
        )

    console.print(table)

    # Display investment theses for top 3
    if len(df) > 0:
        console.print("\n[bold]Top Investment Theses:[/bold]")
        for idx, row in df.head(3).iterrows():
            console.print(f"\n[bold cyan]{idx + 1}. {row['ticker']}[/bold cyan]")
            console.print(f"  {row['investment_thesis']}")
            console.print(f"  [dim]Catalyst: {row['catalyst_timeline']}[/dim]")
