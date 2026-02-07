"""
Export command for exporting analysis results to various formats.

This module provides the CLI command for exporting all stored analysis results
to CSV, Excel, or Parquet formats. Supports both file-based storage backends
and direct database export via --batch-id.
"""

import csv
import json
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from eon.core import get_config, get_logger
from eon.data.storage import JSONStore, ParquetStore, ResultExporter

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
@click.option("--batch-id", "-b", default=None,
              help="Export results from a specific batch (queries database directly)")
@click.option("--status-filter", default=None,
              type=click.Choice(["completed", "failed", "skipped", "all"], case_sensitive=False),
              help="Filter batch items by status (with --batch-id)")
def export(
    format: str,
    output: str,
    analysis_type: str,
    source: str,
    stats: bool,
    batch_id: str,
    status_filter: str
):
    """
    Export analysis results to various formats.

    Aggregates all stored analysis results and exports them to CSV, Excel,
    or Parquet format. Supports filtering by analysis type.

    Examples:

      # Export all results to CSV
      eon export --format csv --output results.csv

      # Export only fundamental analysis to Excel
      eon export --format excel --output results.xlsx --analysis-type fundamental

      # Export to Parquet for efficient querying
      eon export --format parquet --output results.parquet

      # Export results from a specific batch run
      eon export --batch-id abc12345 --output batch_results.csv

      # Show summary statistics only
      eon export --stats
    """
    config = get_config()
    output_path = Path(output) if output else None

    # Handle batch export (direct database query)
    if batch_id:
        _export_batch(batch_id, output_path, format, status_filter)
        return

    console.print(Panel.fit(
        f"[bold cyan]Exporting Analysis Results[/bold cyan]\n"
        f"Format: {format}\n"
        f"Analysis Type: {analysis_type or 'all'}\n"
        f"Source: {source}",
        title="EON Export"
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


def _export_batch(
    batch_id: str,
    output_path: Path,
    format: str,
    status_filter: str = None
) -> None:
    """
    Export results from a specific batch job via database query.

    Joins batch_items with analysis_results to produce a comprehensive export
    of all results from a batch run.

    Args:
        batch_id: Batch ID (can be partial - first 8 chars)
        output_path: Output file path
        format: Output format (csv, excel)
        status_filter: Optional status filter (completed, failed, skipped, all)
    """
    from eon.ui.database import DatabaseRepository

    db = DatabaseRepository()

    # Resolve partial batch ID
    query = "SELECT batch_id, name, analysis_type FROM batch_jobs WHERE batch_id LIKE ?"
    rows = db._execute_with_retry(query, (f"{batch_id}%",), fetch_all=True)

    if not rows:
        console.print(f"[red]No batch found matching: {batch_id}[/red]")
        return
    if len(rows) > 1:
        console.print(f"[red]Multiple batches match '{batch_id}'. Please be more specific.[/red]")
        for r in rows:
            console.print(f"  {r['batch_id'][:12]}... - {r['name']}")
        return

    full_batch_id = rows[0]['batch_id']
    batch_name = rows[0]['name']

    # Build query for results
    status_clause = ""
    params = [full_batch_id]
    if status_filter and status_filter != "all":
        status_clause = "AND bi.status = ?"
        params.append(status_filter)

    query = f"""
        SELECT
            bi.ticker,
            bi.company_name,
            bi.status AS item_status,
            bi.attempts,
            bi.completed_years,
            bi.total_years,
            ar.fiscal_year,
            ar.filing_type,
            ar.result_type,
            ar.result_json,
            ar.created_at
        FROM batch_items bi
        LEFT JOIN analysis_results ar ON ar.run_id = bi.run_id
        WHERE bi.batch_id = ? {status_clause}
        ORDER BY bi.ticker, ar.fiscal_year
    """
    results = db._execute_with_retry(query, tuple(params), fetch_all=True)

    if not results:
        console.print(f"[yellow]No results found for batch {batch_id}[/yellow]")
        return

    console.print(Panel.fit(
        f"[bold cyan]Batch Export[/bold cyan]\n"
        f"Batch: {batch_name}\n"
        f"ID: {full_batch_id[:16]}...\n"
        f"Results: {len(results)} rows",
        title="EON Batch Export"
    ))

    if format in ["csv", "all"]:
        csv_path = output_path if format == "csv" else output_path.with_suffix(".csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ticker", "company_name", "item_status", "attempts",
                "completed_years", "total_years", "fiscal_year",
                "filing_type", "result_type", "result_json", "created_at"
            ])
            for row in results:
                writer.writerow([
                    row['ticker'], row['company_name'], row['item_status'],
                    row['attempts'], row['completed_years'], row['total_years'],
                    row['fiscal_year'], row['filing_type'], row['result_type'],
                    row['result_json'], row['created_at']
                ])
        console.print(f"[green]Exported {len(results)} rows to {csv_path}[/green]")

    elif format == "excel":
        try:
            import pandas as pd
            df = pd.DataFrame([dict(row) for row in results])
            excel_path = output_path if output_path.suffix == ".xlsx" else output_path.with_suffix(".xlsx")
            df.to_excel(excel_path, index=False)
            console.print(f"[green]Exported {len(results)} rows to {excel_path}[/green]")
        except ImportError:
            console.print("[red]pandas/openpyxl required for Excel export. Use --format csv instead.[/red]")

    console.print(Panel.fit(
        f"[bold green]Batch Export Complete![/bold green]\n"
        f"Output: {output_path}",
        title="Success"
    ))


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
