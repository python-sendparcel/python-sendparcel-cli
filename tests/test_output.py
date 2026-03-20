"""Tests for Rich output formatting helpers."""

from io import StringIO

from rich.console import Console

from sendparcel_cli.output import (
    format_config_check,
    format_providers_table,
    format_shipment_result,
)


class TestFormatProvidersTable:
    def test_renders_provider_rows(self) -> None:
        providers = [
            {
                "slug": "inpost_locker",
                "display_name": "InPost Paczkomat",
                "confirmation_method": "PUSH",
                "countries": ["PL"],
                "configured": True,
            },
            {
                "slug": "dpd_standard",
                "display_name": "DPD Kurier",
                "confirmation_method": "NONE",
                "countries": ["PL"],
                "configured": False,
            },
        ]
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_providers_table(providers, console=console)
        output = buf.getvalue()
        assert "inpost_locker" in output
        assert "InPost Paczkomat" in output
        assert "dpd_standard" in output
        assert "NONE" in output

    def test_empty_providers(self) -> None:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_providers_table([], console=console)
        output = buf.getvalue()
        assert "No providers" in output or "provider" in output.lower()


class TestFormatShipmentResult:
    def test_renders_result_fields(self) -> None:
        result = {
            "external_id": "ext-123",
            "tracking_number": "TRACK-456",
            "provider": "inpost_locker",
            "status": "created",
        }
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_shipment_result(result, console=console)
        output = buf.getvalue()
        assert "ext-123" in output
        assert "TRACK-456" in output

    def test_renders_label_saved_path(self) -> None:
        result = {
            "external_id": "ext-1",
            "tracking_number": "",
            "provider": "test",
            "status": "created",
            "label_path": "/tmp/label.pdf",
        }
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_shipment_result(result, console=console)
        output = buf.getvalue()
        assert "/tmp/label.pdf" in output


class TestFormatConfigCheck:
    def test_all_fields_present(self) -> None:
        schema = {
            "token": {
                "type": "str",
                "required": True,
                "secret": True,
                "description": "API token",
            },
            "sandbox": {
                "type": "bool",
                "required": False,
                "secret": False,
                "description": "Sandbox mode",
                "default": False,
            },
        }
        config = {"token": "my-secret-token", "sandbox": True}
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_config_check(
            slug="inpost_locker",
            schema=schema,
            config=config,
            console=console,
        )
        output = buf.getvalue()
        assert "token" in output
        assert "my-secret-token" not in output  # secret masked
        assert "sandbox" in output

    def test_missing_required_field(self) -> None:
        schema = {
            "token": {
                "type": "str",
                "required": True,
                "secret": True,
                "description": "API token",
            },
        }
        config: dict[str, str] = {}
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        format_config_check(
            slug="inpost_locker",
            schema=schema,
            config=config,
            console=console,
        )
        output = buf.getvalue()
        assert "MISSING" in output.upper() or "missing" in output.lower()
