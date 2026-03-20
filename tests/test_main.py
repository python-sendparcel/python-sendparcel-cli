"""Tests for CLI commands."""

import base64
from pathlib import Path
from typing import Any

from sendparcel.enums import LabelFormat
from sendparcel.provider import BaseProvider
from sendparcel.registry import registry
from sendparcel.types import ShipmentCreateResult
from typer.testing import CliRunner

from sendparcel_cli.main import app

runner = CliRunner()


class TestInitCommand:
    def test_creates_config_file(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            ["init", "--config", str(config_path)],
        )
        assert result.exit_code == 0
        assert config_path.exists()

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text('[providers.test]\nkey = "value"\n')
        result = runner.invoke(
            app,
            ["init", "--config", str(config_path)],
        )
        assert result.exit_code == 0
        assert (
            "already exists" in result.stdout.lower()
            or "exists" in result.stdout.lower()
        )
        assert config_path.read_text() == '[providers.test]\nkey = "value"\n'


class TestProvidersCommand:
    def test_lists_providers(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            ["providers", "--config", str(config_path)],
        )
        assert result.exit_code == 0
        # At minimum, DummyProvider is always registered
        assert (
            "dummy" in result.stdout.lower()
            or "provider" in result.stdout.lower()
        )


class TestCheckConfigCommand:
    def test_shows_missing_fields(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        result = runner.invoke(
            app,
            ["check-config", "dummy", "--config", str(config_path)],
        )
        assert result.exit_code == 0

    def test_unknown_provider_exits_with_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        result = runner.invoke(
            app,
            [
                "check-config",
                "nonexistent_provider_xyz",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower()


class TestCreateLabelCommand:
    def test_provider_with_inline_label_succeeds(self, tmp_path: Path) -> None:
        class InlineLabelProvider(BaseProvider):
            slug = "inline_label_cli_test"
            display_name = "Inline Label CLI Test"

            async def create_shipment(
                self,
                *,
                sender_address: Any,
                receiver_address: Any,
                parcels: Any,
                **kwargs: Any,
            ) -> ShipmentCreateResult:
                return ShipmentCreateResult(
                    external_id="inline-1",
                    tracking_number="TRACK-1",
                    label={
                        "format": LabelFormat.PDF,
                        "content_base64": base64.b64encode(
                            b"%PDF-inline-label"
                        ).decode("ascii"),
                    },
                )

        registry.register(InlineLabelProvider)
        try:
            config_path = tmp_path / "config.toml"
            config_path.write_text("")
            result = runner.invoke(
                app,
                [
                    "create-label",
                    "inline_label_cli_test",
                    "--config",
                    str(config_path),
                    "--sender-first-name",
                    "Jan",
                    "--receiver-first-name",
                    "Anna",
                    "--output-dir",
                    str(tmp_path),
                ],
            )
            assert result.exit_code == 0
            label_files = list(tmp_path.glob("label-*.pdf"))
            assert len(label_files) == 1
            assert label_files[0].read_bytes() == b"%PDF-inline-label"
        finally:
            registry.unregister("inline_label_cli_test")

    def test_provider_with_zpl_label_uses_zpl_extension(
        self, tmp_path: Path
    ) -> None:
        class ZplLabelProvider(BaseProvider):
            slug = "zpl_label_cli_test"
            display_name = "ZPL Label CLI Test"

            async def create_shipment(
                self,
                *,
                sender_address: Any,
                receiver_address: Any,
                parcels: Any,
                **kwargs: Any,
            ) -> ShipmentCreateResult:
                return ShipmentCreateResult(
                    external_id="zpl-1",
                    tracking_number="TRACK-ZPL",
                    label={
                        "format": LabelFormat.ZPL,
                        "content_base64": base64.b64encode(
                            b"^XA^FO50,50^FDHello^FS^XZ"
                        ).decode("ascii"),
                    },
                )

        registry.register(ZplLabelProvider)
        try:
            config_path = tmp_path / "config.toml"
            config_path.write_text("")
            result = runner.invoke(
                app,
                [
                    "create-label",
                    "zpl_label_cli_test",
                    "--config",
                    str(config_path),
                    "--sender-first-name",
                    "Jan",
                    "--receiver-first-name",
                    "Anna",
                    "--output-dir",
                    str(tmp_path),
                ],
            )
            assert result.exit_code == 0
            label_files = list(tmp_path.glob("label-*.zpl"))
            assert len(label_files) == 1
            assert label_files[0].read_bytes() == b"^XA^FO50,50^FDHello^FS^XZ"
        finally:
            registry.unregister("zpl_label_cli_test")

    def test_provider_without_any_label_support_fails(
        self, tmp_path: Path
    ) -> None:
        class NoLabelProvider(BaseProvider):
            slug = "no_label_cli_test"
            display_name = "No Label CLI Test"

            async def create_shipment(
                self,
                *,
                sender_address: Any,
                receiver_address: Any,
                parcels: Any,
                **kwargs: Any,
            ) -> ShipmentCreateResult:
                return ShipmentCreateResult(
                    external_id="no-label-1",
                    tracking_number="TRACK-1",
                )

        registry.register(NoLabelProvider)
        try:
            config_path = tmp_path / "config.toml"
            config_path.write_text("")
            result = runner.invoke(
                app,
                [
                    "create-label",
                    "no_label_cli_test",
                    "--config",
                    str(config_path),
                    "--sender-first-name",
                    "Jan",
                    "--receiver-first-name",
                    "Anna",
                    "--output-dir",
                    str(tmp_path),
                ],
            )
            assert result.exit_code != 0
            assert "did not return a label" in result.stdout.lower()
        finally:
            registry.unregister("no_label_cli_test")

    def test_unknown_provider_exits_with_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        result = runner.invoke(
            app,
            [
                "create-label",
                "nonexistent_provider_xyz",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower()

    def test_missing_required_address_flags(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        result = runner.invoke(
            app,
            [
                "create-label",
                "dummy",
                "--config",
                str(config_path),
            ],
        )
        # Should fail because required sender/receiver info is missing
        assert (
            result.exit_code != 0
            or "error" in result.stdout.lower()
            or "missing" in result.stdout.lower()
        )

    def test_with_sender_and_receiver_files(self, tmp_path: Path) -> None:
        import json

        config_path = tmp_path / "config.toml"
        config_path.write_text("")

        sender_file = tmp_path / "sender.json"
        sender_file.write_text(
            json.dumps(
                {
                    "first_name": "Jan",
                    "last_name": "Nadawca",
                    "phone": "500100200",
                    "email": "sender@test.com",
                    "street": "Testowa",
                    "building_number": "1",
                    "city": "Warszawa",
                    "postal_code": "00-001",
                    "country_code": "PL",
                }
            )
        )

        receiver_file = tmp_path / "receiver.json"
        receiver_file.write_text(
            json.dumps(
                {
                    "first_name": "Anna",
                    "last_name": "Odbiorca",
                    "phone": "600200300",
                    "email": "receiver@test.com",
                    "city": "Kraków",
                    "postal_code": "30-001",
                    "country_code": "PL",
                }
            )
        )

        result = runner.invoke(
            app,
            [
                "create-label",
                "dummy",
                "--config",
                str(config_path),
                "--sender-file",
                str(sender_file),
                "--receiver-file",
                str(receiver_file),
                "--weight",
                "2.5",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        label_files = list(tmp_path.glob("label-*.txt"))
        assert len(label_files) == 1
        assert "https://dummy.local/labels/" in label_files[0].read_text()

    def test_with_inline_flags(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")

        result = runner.invoke(
            app,
            [
                "create-label",
                "dummy",
                "--config",
                str(config_path),
                "--sender-first-name",
                "Jan",
                "--sender-last-name",
                "Nadawca",
                "--sender-phone",
                "500100200",
                "--sender-email",
                "sender@test.com",
                "--sender-street",
                "Testowa",
                "--sender-building-number",
                "1",
                "--sender-city",
                "Warszawa",
                "--sender-postal-code",
                "00-001",
                "--sender-country-code",
                "PL",
                "--receiver-first-name",
                "Anna",
                "--receiver-last-name",
                "Odbiorca",
                "--receiver-phone",
                "600200300",
                "--receiver-email",
                "receiver@test.com",
                "--weight",
                "2.5",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert len(list(tmp_path.glob("label-*.txt"))) == 1

    def test_kwarg_passthrough(self, tmp_path: Path) -> None:
        import json

        config_path = tmp_path / "config.toml"
        config_path.write_text("")

        sender_file = tmp_path / "sender.json"
        sender_file.write_text(
            json.dumps(
                {
                    "first_name": "Jan",
                    "last_name": "Test",
                    "phone": "500100200",
                    "email": "t@t.com",
                    "city": "Warszawa",
                    "postal_code": "00-001",
                    "country_code": "PL",
                }
            )
        )

        receiver_file = tmp_path / "receiver.json"
        receiver_file.write_text(
            json.dumps(
                {
                    "first_name": "Anna",
                    "last_name": "Test",
                    "phone": "600200300",
                    "email": "r@t.com",
                    "city": "Kraków",
                    "postal_code": "30-001",
                    "country_code": "PL",
                }
            )
        )

        result = runner.invoke(
            app,
            [
                "create-label",
                "dummy",
                "--config",
                str(config_path),
                "--sender-file",
                str(sender_file),
                "--receiver-file",
                str(receiver_file),
                "--weight",
                "1.0",
                "--output-dir",
                str(tmp_path),
                "--kwarg",
                "target_point=KRA010",
                "--kwarg",
                "sending_method=dispatch_order",
            ],
        )
        assert result.exit_code == 0
        assert len(list(tmp_path.glob("label-*.txt"))) == 1
