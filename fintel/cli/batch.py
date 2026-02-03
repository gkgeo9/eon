"""
Batch command for multi-day parallel processing of multiple companies.

This module provides the CLI command for large-scale batch processing that:
- Runs persistently (use tmux/screen for multi-day operation)
- Uses BatchQueueService for proper rate limiting and reset handling
- Supports graceful shutdown via SIGINT/SIGTERM
- Can resume interrupted batches
- Handles context length errors gracefully (skips, doesn't fail)

Usage:
    # Process 1000 companies with 7 years each
    fintel batch companies.csv --years 7

    # Resume an interrupted batch
    fintel batch --resume

    # List incomplete batches
    fintel batch --list-incomplete
"""

import click
import signal
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn

from fintel.core import get_config, get_logger
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.batch_queue import BatchQueueService, BatchJobConfig
from fintel.cli.utils import read_ticker_file

console = Console()
logger = get_logger(__name__)

# Global reference for signal handler
_batch_service: Optional[BatchQueueService] = None
_current_batch_id: Optional[str] = None
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    signal_name = signal.Signals(signum).name

    if _shutdown_requested:
        console.print(f"\n[bold red]Forced shutdown (second {signal_name})[/bold red]")
        sys.exit(1)

    _shutdown_requested = True
    console.print(f"\n[yellow]Received {signal_name}, stopping gracefully...[/yellow]")
    console.print("[yellow]Press Ctrl+C again to force quit[/yellow]")

    if _batch_service and _current_batch_id:
        _batch_service.stop_batch(_current_batch_id)


def _setup_signal_handlers():
    """Install signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def _get_incomplete_batches(db: DatabaseRepository) -> list:
    """Get list of incomplete batches that can be resumed."""
    query = """
        SELECT batch_id, name, total_tickers, completed_tickers, failed_tickers,
               skipped_tickers, status, analysis_type, created_at, last_activity_at
        FROM batch_jobs
        WHERE status IN ('stopped', 'paused', 'waiting_reset', 'running')
        ORDER BY last_activity_at DESC
    """
    rows = db._execute_with_retry(query, fetch_all=True)
    return [dict(row) for row in rows] if rows else []


def _display_batch_progress(batch_service: BatchQueueService, batch_id: str):
    """Display live progress of batch processing."""
    global _shutdown_requested

    with Live(console=console, refresh_per_second=0.5) as live:
        while not _shutdown_requested:
            status = batch_service.get_batch_status(batch_id)
            if not status:
                break

            # Build progress display
            total = status['total_tickers']
            completed = status['completed_tickers']
            failed = status['failed_tickers']
            skipped = status.get('skipped_tickers', 0)
            remaining = total - completed - failed - skipped

            pct = (completed / total * 100) if total > 0 else 0

            # Create status table
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Label", style="bold")
            table.add_column("Value")

            table.add_row("Status", f"[cyan]{status['status']}[/cyan]")
            table.add_row("Progress", f"[green]{completed}[/green] / {total} ({pct:.1f}%)")
            table.add_row("Failed", f"[red]{failed}[/red]")
            table.add_row("Skipped", f"[yellow]{skipped}[/yellow]")
            table.add_row("Remaining", f"{remaining}")

            if status.get('estimated_completion'):
                try:
                    est = datetime.fromisoformat(status['estimated_completion'])
                    table.add_row("Est. Completion", est.strftime("%Y-%m-%d %H:%M"))
                except:
                    pass

            table.add_row("Last Activity", status.get('last_activity_at', 'N/A')[:19])

            panel = Panel(
                table,
                title=f"[bold]Batch: {status['name']}[/bold]",
                subtitle=f"batch_id: {batch_id[:8]}..."
            )
            live.update(panel)

            # Check if batch is complete
            if status['status'] in ('completed', 'failed', 'stopped'):
                break

            time.sleep(5)


@click.command()
@click.argument("ticker-file", type=click.Path(exists=True), required=False)
@click.option("--years", "-y", default=5, help="Number of years to analyze per company (default: 5)")
@click.option("--name", "-n", help="Batch job name (default: auto-generated)")
@click.option("--analysis-type", "-t", default="multi",
              help="Analysis type: fundamental, multi, buffett, taleb, contrarian, excellent, objective, scanner (default: multi)")
@click.option("--resume", "-r", is_flag=True, help="Resume the most recent incomplete batch")
@click.option("--resume-id", help="Resume a specific batch by ID")
@click.option("--list-incomplete", "-l", is_flag=True, help="List all incomplete batches")
@click.option("--cleanup-chrome", is_flag=True, help="Cleanup orphaned Chrome processes periodically")
def batch(
    ticker_file: Optional[str],
    years: int,
    name: Optional[str],
    analysis_type: str,
    resume: bool,
    resume_id: Optional[str],
    list_incomplete: bool,
    cleanup_chrome: bool
):
    """
    Multi-day batch processing of SEC filings analysis.

    Processes companies from a CSV file through the analysis pipeline,
    handling rate limits automatically by waiting for midnight PST reset.

    This command is designed for long-running operations (days/weeks).
    Use tmux or screen for persistence:

        tmux new -s fintel-batch
        fintel batch companies.csv --years 7

    Examples:

      # Process 1000 companies, 7 years each
      fintel batch tickers.csv --years 7

      # Resume most recent interrupted batch
      fintel batch --resume

      # Resume specific batch
      fintel batch --resume-id abc123

      # List incomplete batches
      fintel batch --list-incomplete

      # With Chrome cleanup (recommended for long runs)
      fintel batch tickers.csv --years 7 --cleanup-chrome
    """
    global _batch_service, _current_batch_id

    config = get_config()
    db = DatabaseRepository()
    _batch_service = BatchQueueService(db)

    # Setup signal handlers
    _setup_signal_handlers()

    # Handle list-incomplete
    if list_incomplete:
        incomplete = _get_incomplete_batches(db)
        if not incomplete:
            console.print("[green]No incomplete batches found.[/green]")
            return

        table = Table(title="Incomplete Batches")
        table.add_column("Batch ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Progress")
        table.add_column("Last Activity")

        for b in incomplete:
            total = b['total_tickers']
            completed = b['completed_tickers']
            failed = b['failed_tickers']
            skipped = b.get('skipped_tickers', 0)
            progress = f"{completed}/{total} ({failed} failed, {skipped} skipped)"
            last_activity = b['last_activity_at'][:16] if b['last_activity_at'] else 'N/A'

            table.add_row(
                b['batch_id'][:8] + "...",
                b['name'][:30],
                b['status'],
                progress,
                last_activity
            )

        console.print(table)
        console.print("\n[dim]Use --resume-id <batch_id> to resume a specific batch[/dim]")
        return

    # Handle resume
    if resume or resume_id:
        if resume_id:
            batch_id = resume_id
        else:
            # Find most recent incomplete batch
            incomplete = _get_incomplete_batches(db)
            if not incomplete:
                console.print("[red]No incomplete batches to resume.[/red]")
                return
            batch_id = incomplete[0]['batch_id']

        # Check batch exists and get its status
        status = _batch_service.get_batch_status(batch_id)
        if not status:
            console.print(f"[red]Batch {batch_id} not found.[/red]")
            return

        _current_batch_id = batch_id

        console.print(Panel.fit(
            f"[bold cyan]Resuming Batch[/bold cyan]\n"
            f"Name: {status['name']}\n"
            f"Batch ID: {batch_id[:16]}...\n"
            f"Progress: {status['completed_tickers']}/{status['total_tickers']}\n"
            f"Previous Status: {status['status']}",
            title="Fintel Batch Resume"
        ))

        # Resume the batch
        if _batch_service.resume_batch(batch_id):
            console.print("[green]Batch resumed successfully[/green]\n")
            _display_batch_progress(_batch_service, batch_id)
        else:
            console.print("[red]Failed to resume batch[/red]")
        return

    # New batch - require ticker file
    if not ticker_file:
        console.print("[red]Error: ticker-file is required for new batches[/red]")
        console.print("[dim]Use --resume to resume an existing batch[/dim]")
        return

    # Read tickers
    ticker_path = Path(ticker_file)
    try:
        tickers = read_ticker_file(ticker_path)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if not tickers:
        console.print(f"[red]Error: No tickers found in {ticker_file}[/red]")
        return

    # Validate analysis type
    valid_types = ['fundamental', 'multi', 'buffett', 'taleb', 'contrarian', 'excellent', 'objective', 'scanner']
    if analysis_type not in valid_types and not analysis_type.startswith('custom:'):
        console.print(f"[red]Invalid analysis type: {analysis_type}[/red]")
        console.print(f"[yellow]Valid types: {', '.join(valid_types)}[/yellow]")
        console.print("[yellow]For custom workflows, use: custom:<workflow_id>[/yellow]")
        return

    # Generate batch name
    if not name:
        name = f"CLI Batch {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Calculate estimates
    keys_count = len(config.google_api_keys)
    requests_per_day = keys_count * 20
    total_requests = len(tickers)  # 1 request per ticker (analysis combines years)
    days_estimate = total_requests / max(requests_per_day, 1)

    # Display batch info
    console.print(Panel.fit(
        f"[bold cyan]New Batch Job[/bold cyan]\n"
        f"Name: {name}\n"
        f"Companies: {len(tickers)}\n"
        f"Years per company: {years}\n"
        f"Analysis type: {analysis_type}\n"
        f"API keys available: {keys_count}\n"
        f"Requests/day: ~{requests_per_day}\n"
        f"Estimated duration: ~{days_estimate:.1f} days\n"
        f"Chrome cleanup: {'Yes' if cleanup_chrome else 'No'}",
        title="Fintel Batch"
    ))

    # Confirm start
    if not click.confirm("Start batch processing?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Create batch job
    batch_config = BatchJobConfig(
        name=name,
        tickers=tickers,
        analysis_type=analysis_type,
        filing_type="10-K",
        num_years=years,
        max_retries=2
    )

    batch_id = _batch_service.create_batch_job(batch_config)
    _current_batch_id = batch_id

    console.print(f"\n[green]Created batch: {batch_id}[/green]")
    console.print("[dim]Press Ctrl+C to stop gracefully[/dim]\n")

    # Start batch processing
    if _batch_service.start_batch_job(batch_id):
        _display_batch_progress(_batch_service, batch_id)

        # Final status
        final_status = _batch_service.get_batch_status(batch_id)
        if final_status:
            if final_status['status'] == 'completed':
                console.print(Panel.fit(
                    f"[bold green]Batch Complete![/bold green]\n"
                    f"Completed: {final_status['completed_tickers']}\n"
                    f"Failed: {final_status['failed_tickers']}\n"
                    f"Skipped: {final_status.get('skipped_tickers', 0)}",
                    title="Success"
                ))
            elif final_status['status'] == 'stopped':
                console.print(Panel.fit(
                    f"[bold yellow]Batch Stopped[/bold yellow]\n"
                    f"Completed: {final_status['completed_tickers']}\n"
                    f"Failed: {final_status['failed_tickers']}\n"
                    f"Skipped: {final_status.get('skipped_tickers', 0)}\n\n"
                    f"Run 'fintel batch --resume' to continue",
                    title="Paused"
                ))
            else:
                console.print(f"\n[yellow]Batch ended with status: {final_status['status']}[/yellow]")
    else:
        console.print("[red]Failed to start batch[/red]")
