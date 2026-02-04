"""
Main CLI entry point for Fintel.

This module defines the main Click CLI group and imports all subcommands.
"""

import click
from rich.console import Console
from rich.panel import Panel

from fintel.core import get_config, get_logger, setup_logging
from fintel.cli.analyze import analyze
from fintel.cli.batch import batch
from fintel.cli.export import export
from fintel.cli.scan import scan_contrarian

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """
    Fintel - Financial Intelligence Platform

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

      # Analyze single company
      fintel analyze AAPL --years 5

      # Batch process companies in parallel
      fintel batch tickers.csv --workers 10

      # Analyze through all three perspectives
      fintel analyze AAPL --perspective

      # Export all results to CSV
      fintel export --format csv --output results.csv
    """
    import logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(name="fintel", level=log_level, log_to_console=True, log_to_file=True)
    logging.getLogger("fintel").setLevel(log_level)
    for logger_name, logger_obj in logging.Logger.manager.loggerDict.items():
        if logger_name.startswith("fintel") and isinstance(logger_obj, logging.Logger):
            logger_obj.setLevel(log_level)
    logger.debug("Verbose logging enabled")

    # Display banner on first run
    config = get_config()
    logger.debug(f"Loaded configuration from {config.data_dir}")


# Register commands
cli.add_command(analyze)
cli.add_command(batch)
cli.add_command(export)
cli.add_command(scan_contrarian)


if __name__ == "__main__":
    cli()
