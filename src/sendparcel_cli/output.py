"""Rich output formatting helpers."""

from typing import Any

from rich.console import Console
from rich.table import Table


def format_providers_table(
    providers: list[dict[str, Any]],
    *,
    console: Console | None = None,
) -> None:
    """Print a table of discovered providers."""
    console = console or Console()

    if not providers:
        console.print("[dim]No providers found.[/dim]")
        return

    table = Table(title="Installed Providers")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Method", style="magenta")
    table.add_column("Countries")
    table.add_column("Config", style="green")
    table.add_column("Label", justify="center")
    table.add_column("Callback", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Cancel", justify="center")

    for p in providers:
        configured = (
            "[green]OK[/green]" if p["configured"] else "[red]---[/red]"
        )

        # Capability flags (✓ = supported, --- = not supported)
        label = "[green]✓[/green]" if p.get("has_label") else "[dim]---[/dim]"
        callback = (
            "[green]✓[/green]" if p.get("has_callback") else "[dim]---[/dim]"
        )
        status = "[green]✓[/green]" if p.get("has_status") else "[dim]---[/dim]"
        cancel = "[green]✓[/green]" if p.get("has_cancel") else "[dim]---[/dim]"

        table.add_row(
            str(p["slug"]),
            str(p["display_name"]),
            str(p["confirmation_method"]),
            ", ".join(str(c) for c in p["countries"]),
            configured,
            label,
            callback,
            status,
            cancel,
        )

    console.print(table)


def format_shipment_result(
    result: dict[str, Any],
    *,
    console: Console | None = None,
) -> None:
    """Print shipment creation result."""
    console = console or Console()

    table = Table(title="Shipment Result")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Provider", result.get("provider", ""))
    table.add_row("External ID", result.get("external_id", ""))
    table.add_row("Tracking Number", result.get("tracking_number", ""))
    table.add_row("Status", result.get("status", ""))

    label_path = result.get("label_path")
    if label_path:
        table.add_row("Label saved to", str(label_path))

    console.print(table)


def format_config_check(
    slug: str,
    schema: dict[str, Any],
    config: dict[str, Any],
    *,
    console: Console | None = None,
) -> None:
    """Print configuration check for a provider."""
    console = console or Console()

    table = Table(title=f"Config: {slug}")
    table.add_column("Field", style="cyan")
    table.add_column("Required")
    table.add_column("Type")
    table.add_column("Value", style="bold")
    table.add_column("Status")

    for field_name, field_info in schema.items():
        field_info_typed = field_info
        required = field_info_typed.get("required", False)
        secret = field_info_typed.get("secret", False)
        field_type = field_info_typed.get("type", "str")
        default = field_info_typed.get("default")
        value = config.get(field_name)

        req_str = "[red]Yes[/red]" if required else "No"

        if value is not None:
            display_value = "***" if secret else str(value)
            status = "[green]OK[/green]"
        elif default is not None:
            display_value = f"(default: {default})"
            status = "[green]OK[/green]"
        elif required:
            display_value = ""
            status = "[red]MISSING[/red]"
        else:
            display_value = ""
            status = "[dim]---[/dim]"

        table.add_row(field_name, req_str, field_type, display_value, status)

    console.print(table)
