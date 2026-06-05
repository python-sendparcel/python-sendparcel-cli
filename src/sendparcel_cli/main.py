"""CLI entry point and typer app."""

import base64
import json
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

import anyio
import typer
from rich.console import Console
from sendparcel.exceptions import ProviderNotFoundError
from sendparcel.types import LabelInfo

from sendparcel_cli.config import ConfigManager, get_default_config_path
from sendparcel_cli.models import CLIShipmentRepository
from sendparcel_cli.output import (
    format_config_check,
    format_providers_table,
    format_shipment_result,
)

app = typer.Typer(
    name="sendparcel",
    help="Developer CLI for python-sendparcel provider testing and debugging.",
    add_completion=False,
)
console = Console()

ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        help="Path to config file.",
        envvar="SENDPARCEL_CONFIG",
    ),
]


def _get_config_manager(config_path: Path | None) -> ConfigManager:
    return ConfigManager(config_path or get_default_config_path())


def _parse_kwargs(kwarg_list: list[str] | None) -> dict[str, str]:
    """Parse --kwarg KEY=VALUE pairs into a dict."""
    result: dict[str, str] = {}
    for item in kwarg_list or []:
        if "=" not in item:
            raise typer.BadParameter(
                f"Invalid kwarg format: {item!r}. Expected KEY=VALUE."
            )
        key, _, value = item.partition("=")
        result[key.strip()] = value.strip()
    return result


def _load_address_file(path: Path | None) -> dict[str, Any]:
    """Load address from a JSON file."""
    if path is None:
        return {}
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise typer.BadParameter(f"Expected JSON object in {path}")
    return data


def _build_address(
    file_data: dict[str, Any],
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    street: str | None = None,
    building_number: str | None = None,
    city: str | None = None,
    postal_code: str | None = None,
    country_code: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Merge file data with inline flags. Flags override file values."""
    addr = dict(file_data)
    overrides = {
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "email": email,
        "street": street,
        "building_number": building_number,
        "city": city,
        "postal_code": postal_code,
        "country_code": country_code,
        "company": company,
    }
    for key, value in overrides.items():
        if value is not None:
            addr[key] = value
    return addr


@app.command()
def init(config: ConfigOption = None) -> None:
    """Initialize config file with empty provider sections."""
    from sendparcel.registry import registry

    mgr = _get_config_manager(config)
    if mgr.config_path.exists():
        console.print(
            f"Config already exists at [cyan]{mgr.config_path}[/cyan]"
        )
        return

    registry.discover()
    providers_config: dict[str, dict[str, Any]] = {}
    for slug, _display_name in registry.get_choices():
        provider_class = registry.get_by_slug(slug)
        schema = getattr(provider_class, "config_schema", {})
        provider_cfg: dict[str, Any] = {}
        for field_name, field_info in schema.items():
            default = field_info.get("default")
            if default is not None:
                provider_cfg[field_name] = default
            elif not field_info.get("required", False):
                pass  # skip optional fields without defaults
            else:
                provider_cfg[field_name] = ""
        if provider_cfg:
            providers_config[slug] = provider_cfg

    mgr.save({"providers": providers_config})
    console.print(f"Config created at [cyan]{mgr.config_path}[/cyan]")


@app.command()
def providers(config: ConfigOption = None) -> None:
    """List installed providers and their configuration status."""
    from sendparcel.provider import (
        CancellableProvider,
        LabelProvider,
        PullStatusProvider,
        PushCallbackProvider,
    )
    from sendparcel.registry import registry

    mgr = _get_config_manager(config)
    registry.discover()

    provider_list = []
    for slug, display_name in registry.get_choices():
        provider_class = registry.get_by_slug(slug)
        provider_config = mgr.get_provider_config(slug)
        schema = getattr(provider_class, "config_schema", {})

        configured = True
        if schema:
            for field_name, field_info in schema.items():
                if field_info.get(
                    "required", False
                ) and not provider_config.get(field_name):
                    configured = False
                    break

        provider_list.append(
            {
                "slug": slug,
                "display_name": display_name,
                "confirmation_method": str(provider_class.confirmation_method),
                "countries": provider_class.supported_countries,
                "configured": configured,
                "has_label": issubclass(provider_class, LabelProvider),
                "has_callback": issubclass(
                    provider_class, PushCallbackProvider
                ),
                "has_status": issubclass(provider_class, PullStatusProvider),
                "has_cancel": issubclass(provider_class, CancellableProvider),
            }
        )

    format_providers_table(provider_list, console=console)


@app.command("check-config")
def check_config(
    slug: Annotated[str, typer.Argument(help="Provider slug.")],
    config: ConfigOption = None,
) -> None:
    """Check configuration for a specific provider."""
    from sendparcel.registry import registry

    mgr = _get_config_manager(config)
    registry.discover()

    try:
        provider_class = registry.get_by_slug(slug)
    except ProviderNotFoundError:
        console.print(f"[red]Provider {slug!r} not found.[/red]")
        raise typer.Exit(code=1) from None

    schema = getattr(provider_class, "config_schema", {})
    provider_config = mgr.get_provider_config(slug)

    format_config_check(
        slug=slug,
        schema=schema,
        config=provider_config,
        console=console,
    )


@app.command("create-label")
def create_label(
    slug: Annotated[str, typer.Argument(help="Provider slug.")],
    config: ConfigOption = None,
    sender_file: Annotated[
        Path | None,
        typer.Option(help="Sender address JSON file."),
    ] = None,
    receiver_file: Annotated[
        Path | None,
        typer.Option(help="Receiver address JSON file."),
    ] = None,
    sender_first_name: Annotated[
        str | None, typer.Option(help="Sender first name.")
    ] = None,
    sender_last_name: Annotated[
        str | None, typer.Option(help="Sender last name.")
    ] = None,
    sender_phone: Annotated[
        str | None, typer.Option(help="Sender phone.")
    ] = None,
    sender_email: Annotated[
        str | None, typer.Option(help="Sender email.")
    ] = None,
    sender_street: Annotated[
        str | None, typer.Option(help="Sender street.")
    ] = None,
    sender_building_number: Annotated[
        str | None,
        typer.Option(help="Sender building number."),
    ] = None,
    sender_city: Annotated[
        str | None, typer.Option(help="Sender city.")
    ] = None,
    sender_postal_code: Annotated[
        str | None, typer.Option(help="Sender postal code.")
    ] = None,
    sender_country_code: Annotated[
        str | None,
        typer.Option(help="Sender country code."),
    ] = None,
    sender_company: Annotated[
        str | None, typer.Option(help="Sender company.")
    ] = None,
    receiver_first_name: Annotated[
        str | None,
        typer.Option(help="Receiver first name."),
    ] = None,
    receiver_last_name: Annotated[
        str | None,
        typer.Option(help="Receiver last name."),
    ] = None,
    receiver_phone: Annotated[
        str | None, typer.Option(help="Receiver phone.")
    ] = None,
    receiver_email: Annotated[
        str | None, typer.Option(help="Receiver email.")
    ] = None,
    receiver_street: Annotated[
        str | None, typer.Option(help="Receiver street.")
    ] = None,
    receiver_building_number: Annotated[
        str | None,
        typer.Option(help="Receiver building number."),
    ] = None,
    receiver_city: Annotated[
        str | None, typer.Option(help="Receiver city.")
    ] = None,
    receiver_postal_code: Annotated[
        str | None,
        typer.Option(help="Receiver postal code."),
    ] = None,
    receiver_country_code: Annotated[
        str | None,
        typer.Option(help="Receiver country code."),
    ] = None,
    receiver_company: Annotated[
        str | None,
        typer.Option(help="Receiver company."),
    ] = None,
    weight: Annotated[float, typer.Option(help="Parcel weight in kg.")] = 1.0,
    output_dir: Annotated[
        Path | None,
        typer.Option(help="Directory to save label file."),
    ] = None,
    kwarg: Annotated[
        list[str] | None,
        typer.Option(help="Provider kwargs as KEY=VALUE."),
    ] = None,
) -> None:
    """Create a test shipment and download the label."""
    from sendparcel.flow import ShipmentFlow
    from sendparcel.registry import registry

    mgr = _get_config_manager(config)
    registry.discover()

    try:
        registry.get_by_slug(slug)
    except ProviderNotFoundError:
        console.print(f"[red]Provider {slug!r} not found.[/red]")
        raise typer.Exit(code=1) from None

    sender_data = _load_address_file(sender_file)
    sender_addr = _build_address(
        sender_data,
        first_name=sender_first_name,
        last_name=sender_last_name,
        phone=sender_phone,
        email=sender_email,
        street=sender_street,
        building_number=sender_building_number,
        city=sender_city,
        postal_code=sender_postal_code,
        country_code=sender_country_code,
        company=sender_company,
    )

    receiver_data = _load_address_file(receiver_file)
    receiver_addr = _build_address(
        receiver_data,
        first_name=receiver_first_name,
        last_name=receiver_last_name,
        phone=receiver_phone,
        email=receiver_email,
        street=receiver_street,
        building_number=receiver_building_number,
        city=receiver_city,
        postal_code=receiver_postal_code,
        country_code=receiver_country_code,
        company=receiver_company,
    )

    if not sender_addr and not receiver_addr:
        console.print(
            "[red]Error: provide sender/receiver addresses "
            "via --sender-file/--receiver-file "
            "or inline flags.[/red]"
        )
        raise typer.Exit(code=1)

    extra_kwargs = _parse_kwargs(kwarg)

    repo = CLIShipmentRepository()
    flow_config = mgr.get_flow_config()
    flow = ShipmentFlow(
        repository=repo,  # type: ignore[arg-type]
        config=flow_config,
        validators=[],
    )

    async def _run() -> dict[str, Any]:
        # Build TypedDict-compatible address dicts from the merged data.
        sender_addr_info: dict[str, Any] = {
            k: v for k, v in sender_addr.items() if v is not None
        }
        receiver_addr_info: dict[str, Any] = {
            k: v for k, v in receiver_addr.items() if v is not None
        }
        if not sender_addr_info and not receiver_addr_info:
            raise ValueError(
                "No address fields provided. "
                "Use --sender-file/--receiver-file or inline flags."
            )
        created = await flow.create_shipment(
            slug,
            sender_address=sender_addr_info,  # type: ignore[arg-type]
            receiver_address=receiver_addr_info,  # type: ignore[arg-type]
            parcels=[{"weight_kg": Decimal(str(weight))}],
            **extra_kwargs,
        )
        shipment = created.shipment
        result: dict[str, Any] = {
            "external_id": shipment.external_id,
            "tracking_number": shipment.tracking_number,
            "provider": shipment.provider,
            "status": shipment.status,
        }
        label_payload = created.label

        if label_payload is None:
            try:
                labelled = await flow.create_label(
                    shipment,
                    **extra_kwargs,
                )
            except ProviderNotFoundError:
                raise
            except Exception as exc:
                console.print(f"[yellow]Label creation failed: {exc}[/]")
                labelled = None
            if labelled is not None:
                shipment = labelled.shipment
                label_payload = labelled.label

        label_path = _save_label(
            label_payload, shipment.external_id, output_dir
        )
        if label_payload is None or label_path is None:
            raise ValueError(
                f"Provider {slug!r} did not return a label payload"
            )
        if label_path:
            result["label_path"] = str(label_path)

        return result

    try:
        result = anyio.run(_run)
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from None

    format_shipment_result(result, console=console)


def _save_label(
    label: LabelInfo | None,
    external_id: str,
    output_dir: Path | None,
) -> Path | None:
    """Save a returned label payload to disk."""
    if output_dir is None:
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    if not label:
        return None

    content_base64 = str(label.get("content_base64", ""))
    if content_base64:
        label_format = str(label.get("format", "PDF")).lower()
        extension = {
            "pdf": ".pdf",
            "png": ".png",
            "zpl": ".zpl",
            "epl": ".epl",
        }.get(label_format, ".bin")
        filename = f"label-{external_id or 'label'}{extension}"
        label_path = output_dir / filename

        label_path.write_bytes(base64.b64decode(content_base64))
        return label_path

    label_url = str(label.get("url", ""))
    if not label_url:
        return None

    label_path = output_dir / f"label-{external_id or 'label'}.txt"
    label_path.write_text(f"Label URL: {label_url}\n")
    return label_path
