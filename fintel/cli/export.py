"""
Export command for exporting analysis results to various formats.

This module provides the CLI command for exporting all stored analysis results
to CSV, Excel, or Parquet formats.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from fintel.core import get_config, get_logger
from fintel.data.storage import JSONStore, ParquetStore, ResultExporter

console = Console()
logger = get_logger(__name__)


@click.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "excel", "parquet", "all"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)"
)
@click.option("--output", "-o", type=click.Path(), required=True, help="Output file path")
@click.option(
    "--analysis-type",
    "-t",
    type=click.Choice(["fundamental", "perspectives", "success_factors", "all"], case_sensitive=False),
    help="Filter by analysis type (default: all)"
)
@click.option("--source", type=click.Choice(["json", "parquet"], case_sensitive=False), default="json", help="Source storage backend")
@click.option("--stats", is_flag=True, help="Display summary statistics only (no export)")
def export(
    format: str,
    output: str,
    analysis_type: str,
    source: str,
    stats: bool
):
    """
    Export analysis results to various formats.

    Aggregates all stored analysis results and exports them to CSV, Excel,
    or Parquet format. Supports filtering by analysis type.

    Examples:

      # Export all results to CSV
      fintel export --format csv --output results.csv

      # Export only fundamental analysis to Excel
      fintel export --format excel --output results.xlsx --analysis-type fundamental

      # Export to Parquet for efficient querying
      fintel export --format parquet --output results.parquet

      # Show summary statistics only
      fintel export --stats
    """
    config = get_config()
    output_path = Path(output) if output else None

    console.print(Panel.fit(
        f"[bold cyan]Exporting Analysis Results[/bold cyan]\n"
        f"Format: {format}\n"
        f"Analysis Type: {analysis_type or 'all'}\n"
        f"Source: {source}",
        title="Fintel Export"
    ))

    try:
        # Initialize storage backends
        json_store = None
        parquet_store = None

        if source == "json":
            json_dir = config.data_dir / "processed"
            if json_dir.exists():
                json_store = JSONStore(base_dir=json_dir)
            else:
                console.print(f"[yellow]Warning:[/yellow] JSON storage directory not found: {json_dir}")
        elif source == "parquet":
            parquet_dir = config.data_dir / "archive"
            if parquet_dir.exists():
                parquet_store = ParquetStore(base_dir=parquet_dir)
            else:
                console.print(f"[yellow]Warning:[/yellow] Parquet storage directory not found: {parquet_dir}")

        if not json_store and not parquet_store:
            console.print(" No storage backend available. Nothing to export.", style="bold red")
            return

        # Create exporter
        exporter = ResultExporter(json_store=json_store, parquet_store=parquet_store)

        # Display statistics if requested
        if stats:
            _display_stats(exporter, analysis_type)
            return

        # Export to requested format
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            if format in ["csv", "all"]:
                task = progress.add_task("Exporting to CSV...", total=None)

                csv_path = output_path if format == "csv" else output_path.with_suffix(".csv")
                exporter.export_to_csv(
                    output_path=csv_path,
                    analysis_type=analysis_type if analysis_type != "all" else None
                )

                progress.update(task, completed=True)
                console.print(f" Exported to CSV: {csv_path}", style="green")

            if format in ["excel", "all"]:
                task = progress.add_task("Exporting to Excel...", total=None)

                excel_path = output_path if format == "excel" else output_path.with_suffix(".xlsx")

                # Define sheets for Excel export
                sheets = None
                if analysis_type and analysis_type != "all":
                    sheets = {analysis_type.capitalize(): [analysis_type]}

                exporter.export_to_excel(
                    output_path=excel_path,
                    sheets=sheets
                )

                progress.update(task, completed=True)
                console.print(f" Exported to Excel: {excel_path}", style="green")

            if format in ["parquet", "all"]:
                task = progress.add_task("Exporting to Parquet...", total=None)

                parquet_path = output_path if format == "parquet" else output_path.with_suffix(".parquet")
                exporter.export_to_parquet(
                    output_path=parquet_path,
                    analysis_type=analysis_type if analysis_type != "all" else None,
                    partition_by="year"
                )

                progress.update(task, completed=True)
                console.print(f" Exported to Parquet: {parquet_path}", style="green")

        console.print(Panel.fit(
            f"[bold green]Export Complete![/bold green]\n"
            f"Output: {output_path}",
            title="Success"
        ))

    except Exception as e:
        console.print(f"\n Export failed: {e}", style="bold red")
        logger.exception("Export failed")
        raise click.Abort()


def _display_stats(exporter: ResultExporter, analysis_type: str = None) -> None:
    """
    Display summary statistics for stored analyses.

    Args:
        exporter: ResultExporter instance
        analysis_type: Optional filter for analysis type
    """
    stats = exporter.get_summary_stats(analysis_type=analysis_type if analysis_type != "all" else None)

    if "error" in stats:
        console.print(f" Error getting stats: {stats['error']}", style="bold red")
        return

    console.print("\n[bold]Storage Statistics:[/bold]")
    console.print(f"  Total records: {stats.get('total_records', 0)}")
    console.print(f"  Unique tickers: {stats.get('unique_tickers', 0)}")

    if "year_range" in stats:
        console.print(f"  Year range: {stats['year_range']}")

    if "by_type" in stats:
        console.print("\n[bold]By Analysis Type:[/bold]")
        for atype, count in stats["by_type"].items():
            console.print(f"  {atype}: {count} records")
