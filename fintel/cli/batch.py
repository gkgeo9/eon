"""
Batch command for multi-day parallel processing of multiple companies.

This module provides the CLI command for large-scale batch processing that:
- Runs persistently (use tmux/screen for multi-day operation)
- Uses BatchQueueService for proper rate limiting and reset handling
- Supports graceful shutdown via SIGINT/SIGTERM
- Can resume interrupted batches
- Handles context length errors gracefully (skips, doesn't fail)

RESUME BEHAVIOR:
    - Progress is tracked per-COMPANY, not per-year
    - If a company fails mid-analysis (e.g., at year 13 of 20), the entire
      company will be retried from the beginning on resume
    - Completed companies are never re-processed
    - Failed companies are retried up to max_retries times

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
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text

from fintel.core import get_config, get_logger
from fintel.core.logging import setup_cli_logging
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.batch_queue import BatchQueueService, BatchJobConfig
from fintel.cli.utils import read_ticker_file

console = Console()
logger = get_logger(__name__)

# Will be reconfigured based on --log-level flag
_log_level_configured = False

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


def _get_running_items(db: DatabaseRepository, batch_id: str) -> List[Dict]:
    """Get currently running items (active workers) with year progress."""
    query = """
        SELECT ticker, company_name, started_at, attempts,
               total_years, completed_years, current_year
        FROM batch_items
        WHERE batch_id = ? AND status = 'running'
        ORDER BY started_at DESC
        LIMIT 25
    """
    rows = db._execute_with_retry(query, (batch_id,), fetch_all=True)
    return [dict(row) for row in rows] if rows else []


def _get_recent_completed(db: DatabaseRepository, batch_id: str, limit: int = 5) -> List[Dict]:
    """Get recently completed items with year progress."""
    query = """
        SELECT ticker, company_name, completed_at,
               total_years, completed_years
        FROM batch_items
        WHERE batch_id = ? AND status = 'completed'
        ORDER BY completed_at DESC
        LIMIT ?
    """
    rows = db._execute_with_retry(query, (batch_id, limit), fetch_all=True)
    return [dict(row) for row in rows] if rows else []


def _get_recent_failed(db: DatabaseRepository, batch_id: str, limit: int = 5) -> List[Dict]:
    """Get recently failed items."""
    query = """
        SELECT ticker, company_name, error_message, attempts
        FROM batch_items
        WHERE batch_id = ? AND status = 'failed'
        ORDER BY completed_at DESC
        LIMIT ?
    """
    rows = db._execute_with_retry(query, (batch_id, limit), fetch_all=True)
    return [dict(row) for row in rows] if rows else []


def _format_duration(start_time_str: Optional[str]) -> str:
    """Format duration since start time."""
    if not start_time_str:
        return "N/A"
    try:
        start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        if start.tzinfo:
            start = start.replace(tzinfo=None)
        duration = datetime.utcnow() - start
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    except:
        return "N/A"


def _build_progress_display(
    batch_service: BatchQueueService,
    db: DatabaseRepository,
    batch_id: str,
    num_years: int
) -> Panel:
    """Build a rich progress display panel."""
    status = batch_service.get_batch_status(batch_id)
    if not status:
        return Panel("[red]Batch not found[/red]")

    # Get detailed item info
    running_items = _get_running_items(db, batch_id)
    recent_completed = _get_recent_completed(db, batch_id, limit=3)
    recent_failed = _get_recent_failed(db, batch_id, limit=3)

    # Calculate stats
    total = status['total_tickers']
    completed = status['completed_tickers']
    failed = status['failed_tickers']
    skipped = status.get('skipped_tickers', 0)
    pending = total - completed - failed - skipped - len(running_items)
    pct = (completed / total * 100) if total > 0 else 0

    # Build the display
    elements = []

    # === OVERALL PROGRESS BAR ===
    progress_bar = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[green]{task.completed}[/green]/[blue]{task.total}[/blue]"),
        expand=False
    )
    task = progress_bar.add_task("Overall", total=total, completed=completed)
    elements.append(progress_bar)
    elements.append(Text(""))

    # === STATUS SUMMARY ===
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Label", style="bold", width=15)
    summary_table.add_column("Value", width=20)
    summary_table.add_column("Label2", style="bold", width=15)
    summary_table.add_column("Value2", width=20)

    status_color = {
        'running': 'green',
        'waiting_reset': 'yellow',
        'stopped': 'red',
        'completed': 'cyan',
        'failed': 'red'
    }.get(status['status'], 'white')

    summary_table.add_row(
        "Status", f"[{status_color}]{status['status']}[/{status_color}]",
        "Active Workers", f"[cyan]{len(running_items)}[/cyan]"
    )
    summary_table.add_row(
        "Completed", f"[green]{completed}[/green] ({pct:.1f}%)",
        "Pending", f"[blue]{pending}[/blue]"
    )
    summary_table.add_row(
        "Failed", f"[red]{failed}[/red]",
        "Skipped", f"[yellow]{skipped}[/yellow]"
    )

    # Time estimates
    if status.get('estimated_completion'):
        try:
            est = datetime.fromisoformat(status['estimated_completion'])
            est_str = est.strftime("%Y-%m-%d %H:%M")
        except:
            est_str = "N/A"
    else:
        est_str = "Calculating..."

    summary_table.add_row(
        "Est. Completion", est_str,
        "Years/Company", f"{num_years}"
    )

    elements.append(summary_table)
    elements.append(Text(""))

    # === ACTIVE WORKERS ===
    if running_items:
        workers_table = Table(
            title="[bold cyan]Active Workers[/bold cyan]",
            show_header=True,
            header_style="bold",
            box=None,
            padding=(0, 1)
        )
        workers_table.add_column("Ticker", style="cyan", width=10)
        workers_table.add_column("Company", width=20)
        workers_table.add_column("Years", width=10)
        workers_table.add_column("Duration", width=10)
        workers_table.add_column("Attempt", width=8)

        for item in running_items[:10]:  # Show max 10 workers
            company = (item.get('company_name') or '')[:19]
            duration = _format_duration(item.get('started_at'))
            attempt = item.get('attempts', 1)

            # Year progress display
            total_yrs = item.get('total_years', num_years)
            completed_yrs = item.get('completed_years', 0)
            current_yr = item.get('current_year', '')

            if current_yr:
                years_display = f"[yellow]{completed_yrs}/{total_yrs}[/yellow] ({current_yr})"
            else:
                years_display = f"[yellow]{completed_yrs}/{total_yrs}[/yellow]"

            workers_table.add_row(
                item['ticker'],
                company,
                years_display,
                duration,
                f"{attempt}/3"
            )

        if len(running_items) > 10:
            workers_table.add_row(
                f"... +{len(running_items) - 10} more",
                "", "", "", ""
            )

        elements.append(workers_table)
        elements.append(Text(""))

    # === RECENT ACTIVITY ===
    if recent_completed or recent_failed:
        activity_table = Table(
            title="[bold]Recent Activity[/bold]",
            show_header=True,
            header_style="bold",
            box=None,
            padding=(0, 1)
        )
        activity_table.add_column("Status", width=10)
        activity_table.add_column("Ticker", width=10)
        activity_table.add_column("Years", width=8)
        activity_table.add_column("Details", width=32)

        for item in recent_completed:
            total_yrs = item.get('total_years', num_years)
            completed_yrs = item.get('completed_years', total_yrs)
            years_str = f"[green]{completed_yrs}/{total_yrs}[/green]"
            activity_table.add_row(
                "[green]Done[/green]",
                item['ticker'],
                years_str,
                (item.get('company_name') or '')[:31]
            )

        for item in recent_failed:
            error = (item.get('error_message') or 'Unknown error')[:31]
            activity_table.add_row(
                "[red]Failed[/red]",
                item['ticker'],
                "",
                error
            )

        elements.append(activity_table)

    # === WAITING FOR RESET MESSAGE ===
    if status['status'] == 'waiting_reset':
        elements.append(Text(""))
        elements.append(Text(
            "[yellow]Waiting for midnight PST rate limit reset...[/yellow]",
            justify="center"
        ))

    # Build final panel
    return Panel(
        Group(*elements),
        title=f"[bold]{status['name']}[/bold]",
        subtitle=f"batch_id: {batch_id[:8]}... | Last update: {datetime.now().strftime('%H:%M:%S')}",
        border_style="blue"
    )


def _display_batch_progress(batch_service: BatchQueueService, batch_id: str, db: DatabaseRepository, num_years: int):
    """Display live progress of batch processing with detailed worker info."""
    global _shutdown_requested

    with Live(console=console, refresh_per_second=0.5, transient=False) as live:
        while not _shutdown_requested:
            status = batch_service.get_batch_status(batch_id)
            if not status:
                break

            # Build and display progress
            panel = _build_progress_display(batch_service, db, batch_id, num_years)
            live.update(panel)

            # Check if batch is complete
            if status['status'] in ('completed', 'failed', 'stopped'):
                break

            time.sleep(2)  # Update every 2 seconds


@click.command()
@click.argument("ticker-file", type=click.Path(exists=True), required=False)
@click.option("--years", "-y", default=5, show_default=True,
              help="Number of years to analyze per company")
@click.option("--name", "-n", default=None,
              help="Batch job name (default: auto-generated timestamp)")
@click.option("--analysis-type", "-t", default="multi", show_default=True,
              type=click.Choice(['fundamental', 'multi', 'buffett', 'taleb',
                                'contrarian', 'excellent', 'objective', 'scanner'],
                               case_sensitive=False),
              help="Type of analysis to run")
@click.option("--filing-type", "-f", default="10-K", show_default=True,
              help="SEC filing type to analyze (10-K, 20-F, 10-Q, 8-K, 4, DEF 14A, etc.)")
@click.option("--resume", "-r", is_flag=True,
              help="Resume the most recent incomplete batch")
@click.option("--resume-id", default=None,
              help="Resume a specific batch by its ID (use --list-incomplete to find IDs)")
@click.option("--list-incomplete", "-l", is_flag=True,
              help="List all incomplete/paused batches that can be resumed")
@click.option("--cleanup-chrome", is_flag=True,
              help="Cleanup orphaned Chrome processes during daily reset waits")
@click.option("--log-level", "-L", default="none", show_default=True,
              type=click.Choice(['none', 'min', 'verbose'], case_sensitive=False),
              help="Console logging level (none=quiet, min=warnings only, verbose=all). "
                   "File logging is always enabled for debugging.")
def batch(
    ticker_file: Optional[str],
    years: int,
    name: Optional[str],
    analysis_type: str,
    filing_type: str,
    resume: bool,
    resume_id: Optional[str],
    list_incomplete: bool,
    cleanup_chrome: bool,
    log_level: str
):
    """
    Multi-day batch processing of SEC filings analysis.

    Process hundreds or thousands of companies through AI analysis,
    automatically handling API rate limits by waiting for midnight PST reset.

    \b
    ═══════════════════════════════════════════════════════════════════════════
    QUICK START
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1. Create a CSV file with tickers:
       ticker
       AAPL
       MSFT
       GOOGL

    \b
    2. Run the batch:
       fintel batch tickers.csv --years 7

    \b
    3. If interrupted, resume later:
       fintel batch --resume

    \b
    ═══════════════════════════════════════════════════════════════════════════
    TIME ESTIMATES (with 25 API keys @ 20 requests/key/day = 500/day)
    ═══════════════════════════════════════════════════════════════════════════

    \b
    Companies × Years = Total Requests → Days Needed
    ─────────────────────────────────────────────────
    10 × 7   =    70 requests  →  < 1 day
    100 × 7  =   700 requests  →  1.4 days
    500 × 7  = 3,500 requests  →  7 days
    1000 × 7 = 7,000 requests  →  14 days

    \b
    Formula: Days = (Companies × Years) ÷ (API_Keys × 20)

    \b
    ═══════════════════════════════════════════════════════════════════════════
    ANALYSIS TYPES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    multi       - Multi-perspective analysis (Buffett + Taleb + Contrarian)
    fundamental - Basic 10-K financial analysis
    buffett     - Warren Buffett value investing lens
    taleb       - Nassim Taleb antifragility analysis
    contrarian  - Contrarian/skeptical analysis
    excellent   - Excellence/quality analysis
    objective   - Objective factual analysis
    scanner     - Quick screening mode

    \b
    ═══════════════════════════════════════════════════════════════════════════
    FILING TYPES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    Annual filings (one per year):
        10-K      - US annual report (default)
        20-F      - Foreign private issuer annual report
        40-F      - Canadian issuer annual report
        10-K/A    - Amended annual report

    \b
    Quarterly filings (4 per year):
        10-Q      - US quarterly report
        10-Q/A    - Amended quarterly report
        6-K       - Foreign issuer semi-annual/interim

    \b
    Event-based filings (multiple per year):
        8-K       - Current reports (material events)
        4         - Insider trading (Form 4)
        DEF 14A   - Proxy statements
        SC 13D/G  - Beneficial ownership

    \b
    ═══════════════════════════════════════════════════════════════════════════
    RESUME BEHAVIOR
    ═══════════════════════════════════════════════════════════════════════════

    \b
    • Progress is tracked per-COMPANY, not per-year
    • If interrupted mid-company (e.g., year 4 of 7), that company
      restarts from year 1 on resume
    • Completed companies are NEVER re-processed
    • Failed companies are retried up to 3 times

    \b
    ═══════════════════════════════════════════════════════════════════════════
    ENVIRONMENT VARIABLES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    FINTEL_MAX_PARALLEL_WORKERS
        Max companies processed simultaneously (default: 3)
        - Set to 1-3 for free tier (avoids token/minute limits)
        - Set to 10-25 for paid tier
        - Set to 0 for unlimited (use all API keys)

    \b
    FINTEL_SEC_WORKER_STAGGER_DELAY
        Seconds between worker starts (default: 30)
        - Prevents all workers hitting API at once

    \b
    Example (PowerShell):
        $env:FINTEL_MAX_PARALLEL_WORKERS = "2"
        fintel batch tickers.csv --years 7

    \b
    Example (Linux/Mac):
        export FINTEL_MAX_PARALLEL_WORKERS=2
        fintel batch tickers.csv --years 7

    \b
    ═══════════════════════════════════════════════════════════════════════════
    LONG-RUNNING SETUP (recommended for multi-day batches)
    ═══════════════════════════════════════════════════════════════════════════

    \b
    Use tmux or screen to keep the process running after disconnect:

    \b
    # Start a tmux session
    tmux new -s fintel-batch

    \b
    # Run your batch
    fintel batch companies.csv --years 7

    \b
    # Detach from tmux (keeps running): Ctrl+B, then D

    \b
    # Reattach later to check progress
    tmux attach -t fintel-batch

    \b
    # Graceful stop: Press Ctrl+C once (waits for current items)
    # Force stop: Press Ctrl+C twice

    \b
    ═══════════════════════════════════════════════════════════════════════════
    EXAMPLES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    # Basic: 5 years of multi-analysis (10-K filings)
    fintel batch tickers.csv

    \b
    # 7 years with Buffett analysis
    fintel batch tickers.csv --years 7 --analysis-type buffett

    \b
    # Analyze foreign company filings (20-F)
    fintel batch foreign_tickers.csv --filing-type 20-F --years 5

    \b
    # Analyze quarterly filings (10-Q)
    fintel batch tickers.csv --filing-type 10-Q --years 2

    \b
    # Custom batch name
    fintel batch tickers.csv -n "Q1 2024 Analysis" --years 5

    \b
    # List batches that can be resumed
    fintel batch --list-incomplete

    \b
    # Resume most recent batch
    fintel batch --resume

    \b
    # Resume specific batch by ID
    fintel batch --resume-id abc12345-1234-5678-abcd-123456789abc
    """
    global _batch_service, _current_batch_id

    # Configure logging based on --log-level flag
    # File logging is always enabled, console logging is controlled by the flag
    setup_cli_logging(console_mode=log_level.lower())

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
        num_years = status.get('num_years', 5)

        console.print(Panel.fit(
            f"[bold cyan]Resuming Batch[/bold cyan]\n"
            f"Name: {status['name']}\n"
            f"Batch ID: {batch_id[:16]}...\n"
            f"Progress: {status['completed_tickers']}/{status['total_tickers']} companies\n"
            f"Years per company: {num_years}\n"
            f"Previous Status: {status['status']}\n\n"
            f"[dim]Note: Any company that was mid-analysis will restart from year 1[/dim]",
            title="Fintel Batch Resume"
        ))

        # Resume the batch
        if _batch_service.resume_batch(batch_id):
            console.print("[green]Batch resumed successfully[/green]\n")
            _display_batch_progress(_batch_service, batch_id, db, num_years)
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
        f"Filing type: {filing_type}\n"
        f"Analysis type: {analysis_type}\n"
        f"API keys available: {keys_count}\n"
        f"Requests/day: ~{requests_per_day}\n"
        f"Estimated duration: ~{days_estimate:.1f} days\n"
        f"Chrome cleanup: {'Yes' if cleanup_chrome else 'No'}\n\n"
        f"[dim]Resume behavior: Per-company (not per-year)[/dim]",
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
        filing_type=filing_type,
        num_years=years,
        max_retries=2
    )

    batch_id = _batch_service.create_batch_job(batch_config)
    _current_batch_id = batch_id

    console.print(f"\n[green]Created batch: {batch_id}[/green]")
    console.print("[dim]Press Ctrl+C to stop gracefully[/dim]\n")

    # Start batch processing
    if _batch_service.start_batch_job(batch_id):
        _display_batch_progress(_batch_service, batch_id, db, years)

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
