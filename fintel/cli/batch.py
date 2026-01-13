"""
Batch command for parallel processing of multiple companies.

This module provides the CLI command for batch processing companies in parallel
with progress tracking and resumption support.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

from fintel.core import get_config, get_logger
from fintel.processing import ParallelProcessor
from fintel.cli.utils import read_ticker_file

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("ticker-file", type=click.Path(exists=True))
@click.option("--workers", "-w", default=10, help="Number of parallel workers (default: 10, max: 25)")
@click.option("--num-filings", "-n", default=10, help="Number of 10-K filings per company (default: 10)")
@click.option("--session-id", "-s", help="Session ID for progress tracking (default: auto-generated)")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory (default: ./data/batch_results)")
@click.option("--resume", is_flag=True, help="Resume a previous batch session")
def batch(
    ticker_file: str,
    workers: int,
    num_filings: int,
    session_id: str,
    output_dir: str,
    resume: bool
):
    """
    Batch process multiple companies in parallel.

    Reads a list of ticker symbols from a CSV or text file and processes them
    in parallel using multiple API keys. Supports progress tracking and
    resumption of interrupted sessions.

    The ticker file should contain one ticker per line, or be a CSV with a
    'ticker' or 'symbol' column.

    Examples:

      # Process 10 companies with 5 workers
      fintel batch tickers.csv --workers 5

      # Process 30 years with all 25 workers
      fintel batch tickers.csv --workers 25 --num-filings 30

      # Resume interrupted session
      fintel batch tickers.csv --session-id batch_20241205 --resume

      # Custom output directory
      fintel batch tickers.csv --output-dir ./my_results
    """
    config = get_config()

    # Validate workers
    max_workers = min(workers, len(config.google_api_keys))
    if workers > max_workers:
        console.print(
            f"� Requested {workers} workers but only {max_workers} API keys available. "
            f"Using {max_workers} workers.",
            style="yellow"
        )
        workers = max_workers

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

    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = config.data_dir / "batch_results"

    output_path.mkdir(parents=True, exist_ok=True)

    # Generate session ID if not provided
    if not session_id:
        from datetime import datetime
        session_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Display batch info
    console.print(Panel.fit(
        f"[bold cyan]Batch Processing[/bold cyan]\n"
        f"Companies: {len(tickers)}\n"
        f"Workers: {workers}\n"
        f"Filings per company: {num_filings}\n"
        f"Session ID: {session_id}\n"
        f"Resume: {'Yes' if resume else 'No'}",
        title="Fintel Batch"
    ))

    try:
        # Create parallel processor
        processor = ParallelProcessor(
            api_keys=config.google_api_keys[:workers],
            session_id=session_id
        )

        # Process batch
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                f"Processing {len(tickers)} companies...",
                total=len(tickers)
            )

            results = processor.process_batch(
                tickers=tickers,
                num_filings=num_filings,
                output_dir=output_path
            )

            progress.update(task, completed=len(tickers))

        # Display results summary
        _display_results_summary(results, tickers)

        console.print(Panel.fit(
            f"[bold green]Batch Processing Complete![/bold green]\n"
            f"Session ID: {session_id}\n"
            f"Results saved to: {output_path}",
            title="Success"
        ))

    except KeyboardInterrupt:
        console.print(
            f"\n� Batch processing interrupted. "
            f"Run with --session-id {session_id} --resume to continue.",
            style="bold yellow"
        )
    except Exception as e:
        console.print(f"\n Batch processing failed: {e}", style="bold red")
        logger.exception("Batch processing failed")
        raise click.Abort()


def _display_results_summary(results: dict, tickers: list[str]) -> None:
    """
    Display a summary table of batch results.

    Args:
        results: Dictionary of results from parallel processor
        tickers: List of tickers that were processed
    """
    table = Table(title="Batch Results Summary")
    table.add_column("Ticker", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Filings", justify="right")
    table.add_column("Notes")

    for ticker in tickers:
        result = results.get(ticker, {})

        if result.get("success"):
            status = " Success"
            style = "green"
        else:
            status = " Failed"
            style = "red"

        filings = str(result.get("filings_processed", 0))
        notes = result.get("error", "")

        table.add_row(ticker, status, filings, notes)

    console.print(table)

    # Summary stats
    successful = sum(1 for r in results.values() if r.get("success"))
    failed = len(tickers) - successful

    console.print(f"\n[bold]Summary:[/bold] {successful} successful, {failed} failed")
