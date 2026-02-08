"""
Main CLI entry point for EON.

This module defines the main Click CLI group and imports all subcommands.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from eon.core import get_config, get_logger, setup_logging
from eon.cli.analyze import analyze
from eon.cli.batch import batch
from eon.cli.export import export
from eon.cli.scan import scan_contrarian
from eon.cli.workflows import workflows

# Initialize logging with timestamps
setup_logging(level=20)  # INFO level

console = Console()
logger = get_logger(__name__)


# ==================== CACHE COMMANDS ====================

@click.group()
def cache():
    """
    Manage the file cache for SEC filings.

    The cache tracks downloaded PDFs to avoid redundant SEC API calls.
    """
    pass


@cache.command("scan")
@click.option(
    "--pdf-dir", "-d",
    type=click.Path(exists=True),
    help="Directory containing ticker subdirectories with PDFs (default: data/pdfs)"
)
@click.option(
    "--filing-type", "-t",
    default="10-K",
    show_default=True,
    help="Filing type to scan for"
)
def cache_scan(pdf_dir: str, filing_type: str):
    """
    Scan existing PDF files and populate the cache.

    This is useful for:
    - Populating cache after downloading files outside the system
    - Rebuilding cache after database reset
    - Adding previously downloaded files to the cache

    The command scans for PDFs matching the pattern:
    {TICKER}_{FILING_TYPE}_{YYYY-MM-DD}.pdf

    Example:

      # Scan default pdfs directory
      eon cache scan

      # Scan specific directory for 10-K filings
      eon cache scan --pdf-dir /path/to/pdfs --filing-type 10-K

      # Scan for 20-F filings
      eon cache scan --filing-type 20-F
    """
    from eon.ui.database import DatabaseRepository

    config = get_config()

    if pdf_dir:
        scan_path = Path(pdf_dir)
    else:
        scan_path = config.get_data_path("pdfs")

    console.print(Panel.fit(
        f"[bold cyan]Scanning PDFs[/bold cyan]\n"
        f"Directory: {scan_path}\n"
        f"Filing type: {filing_type}",
        title="Cache Scan"
    ))

    if not scan_path.exists():
        console.print(f"[red]Directory not found: {scan_path}[/red]")
        return

    db = DatabaseRepository()
    results = db.scan_and_cache_existing_pdfs(str(scan_path), filing_type)

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Files scanned: {results['scanned']}")
    console.print(f"  [green]Newly cached: {results['cached']}[/green]")
    console.print(f"  Skipped (already cached or no match): {results['skipped']}")
    if results['errors'] > 0:
        console.print(f"  [red]Errors: {results['errors']}[/red]")

    console.print(f"\n[green]Cache scan complete![/green]")


@cache.command("stats")
def cache_stats():
    """
    Show cache statistics.
    """
    from eon.ui.database import DatabaseRepository

    db = DatabaseRepository()
    count = db.get_cache_count()
    tickers_10k = db.get_tickers_with_cached_files("10-K")

    console.print(Panel.fit(
        f"[bold cyan]Cache Statistics[/bold cyan]\n"
        f"Total cached files: {count}\n"
        f"Tickers with 10-K: {len(tickers_10k)}",
        title="Cache Stats"
    ))

    if tickers_10k:
        console.print(f"\n[dim]Sample tickers: {', '.join(tickers_10k[:10])}{'...' if len(tickers_10k) > 10 else ''}[/dim]")


@cache.command("clear")
@click.option("--older-than-days", "-d", type=int, help="Only clear entries older than N days")
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def cache_clear(older_than_days: int):
    """
    Clear the file cache.
    """
    from eon.ui.database import DatabaseRepository

    db = DatabaseRepository()
    deleted = db.clear_file_cache(older_than_days)

    if older_than_days:
        console.print(f"[yellow]Cleared {deleted} cache entries older than {older_than_days} days[/yellow]")
    else:
        console.print(f"[yellow]Cleared all {deleted} cache entries[/yellow]")


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """
    Erebus Observatory Network

    A comprehensive platform for analyzing SEC 10-K filings through multiple
    investment perspectives (Buffett, Taleb, Contrarian) with parallel processing
    capabilities for 1,000+ companies.

    Features:
    - SEC 10-K fundamental analysis
    - Multi-perspective analysis (Value, Antifragility, Contrarian)
    - Multi-year trend analysis (30+ years)
    - Parallel batch processing (25+ workers)
    - Contrarian opportunity scanner
    - Benchmark comparison against top performers

    Examples:

      # Launch the web UI
      eon web

      # Analyze single company
      eon analyze AAPL --years 5

      # Batch process companies in parallel
      eon batch tickers.csv --workers 10

      # Analyze through all three perspectives
      eon analyze AAPL --perspective

      # Export all results to CSV
      eon export --format csv --output results.csv
    """
    if verbose:
        import logging
        logging.getLogger("eon").setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Display banner on first run
    config = get_config()
    logger.debug(f"Loaded configuration from {config.data_dir}")


@cli.command()
@click.option("--port", "-p", type=int, default=8501, show_default=True, help="Port to run on")
@click.option(
    "--host",
    "-h",
    default="localhost",
    show_default=True,
    help="Host to bind to (use 0.0.0.0 for external access)",
)
def web(port: int, host: str):
    """
    Launch the Streamlit web UI.

    Starts the EON web interface for interactive analysis.

    Examples:

      # Start on default port
      eon web

      # Start on custom port
      eon web --port 8080

      # Allow external connections
      eon web --host 0.0.0.0
    """
    import subprocess
    import sys

    app_path = Path(__file__).resolve().parents[2] / "streamlit_app.py"

    if not app_path.exists():
        console.print(f"[red]Streamlit app not found at {app_path}[/red]")
        raise SystemExit(1)

    console.print(Panel.fit(
        f"[bold cyan]Starting EON Web UI[/bold cyan]\n"
        f"URL: http://{host}:{port}",
        title="EON Web",
    ))

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.address", host,
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Streamlit exited with code {e.returncode}[/red]")
        raise SystemExit(e.returncode)


# Register commands
cli.add_command(analyze)
cli.add_command(batch)
cli.add_command(export)
cli.add_command(scan_contrarian)
cli.add_command(cache)
cli.add_command(workflows)


if __name__ == "__main__":
    cli()
