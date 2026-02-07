"""
Workflows command for listing available custom analysis workflows.

This module provides the CLI command for discovering and inspecting
custom workflows that can be used with ``eon analyze`` and
``eon batch`` via the ``custom:<workflow_id>`` analysis type.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from eon.core import get_logger

console = Console()
logger = get_logger(__name__)


@click.command()
@click.option(
    "--verbose", "-v", is_flag=True,
    help="Show additional details (category, estimated tokens)",
)
def workflows(verbose: bool):
    """
    List all available custom analysis workflows.

    Custom workflows are Python files in the custom_workflows/ directory
    that are auto-discovered on startup. Use them with the CLI via:

    \b
      eon analyze AAPL --analysis-type custom:<workflow_id>
      eon batch tickers.csv --analysis-type custom:<workflow_id>

    \b
    EXAMPLES

    \b
      # List all custom workflows
      eon workflows

    \b
      # Show detailed info
      eon workflows --verbose

    \b
      # Run analysis with a custom workflow
      eon analyze AAPL --analysis-type custom:examples.moonshot_analyzer
    """
    from custom_workflows import list_workflows

    wf_list = list_workflows()

    if not wf_list:
        console.print(
            Panel.fit(
                "[yellow]No custom workflows found.[/yellow]\n\n"
                "Add Python files to [bold]custom_workflows/[/bold] to get started.\n"
                "See [bold]docs/CUSTOM_WORKFLOWS.md[/bold] for guidance.",
                title="Custom Workflows",
            )
        )
        return

    table = Table(title=f"Custom Workflows ({len(wf_list)} available)")
    table.add_column("Workflow ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description", max_width=50)
    table.add_column("Min Years", justify="center")

    if verbose:
        table.add_column("Category", style="dim")

    for wf in wf_list:
        row = [
            f"custom:{wf['id']}",
            f"{wf['icon']} {wf['name']}",
            (wf['description'][:47] + "...") if len(wf['description']) > 50 else wf['description'],
            str(wf['min_years']),
        ]
        if verbose:
            row.append(wf.get('category', 'custom'))

        table.add_row(*row)

    console.print(table)
    console.print()
    console.print(
        "[dim]Usage:[/dim]  eon analyze AAPL --analysis-type [cyan]custom:<workflow_id>[/cyan]"
    )
    console.print(
        "[dim]       [/dim] eon batch tickers.csv --analysis-type [cyan]custom:<workflow_id>[/cyan]"
    )
