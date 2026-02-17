"""Tests for CLI config management."""

import tomllib
from pathlib import Path

from sendparcel_cli.config import (
    ConfigManager,
    get_default_config_path,
)


class TestGetDefaultConfigPath:
    def test_returns_path_under_config_dir(self) -> None:
        path = get_default_config_path()
        assert path.name == "config.toml"
        assert "sendparcel" in str(path)


class TestConfigManager:
    def test_init_with_custom_path(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        mgr = ConfigManager(config_path)
        assert mgr.config_path == config_path

    def test_load_empty_when_file_missing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config == {}

    def test_load_existing_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "[providers.inpost_locker]\n"
            'token = "my-token"\n'
            "organization_id = 12345\n"
            "sandbox = true\n"
        )
        mgr = ConfigManager(config_path)
        config = mgr.load()
        assert config["providers"]["inpost_locker"]["token"] == "my-token"
        assert config["providers"]["inpost_locker"]["organization_id"] == 12345
        assert config["providers"]["inpost_locker"]["sandbox"] is True

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        config_path = tmp_path / "deep" / "nested" / "config.toml"
        mgr = ConfigManager(config_path)
        mgr.save({"providers": {"test": {"key": "value"}}})
        assert config_path.exists()
        loaded = tomllib.loads(config_path.read_text())
        assert loaded["providers"]["test"]["key"] == "value"

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        mgr = ConfigManager(config_path)
        data = {
            "providers": {
                "dpd_standard": {
                    "login": "test",
                    "password": "secret123",
                    "master_fid": 1495,
                    "sandbox": True,
                },
            },
        }
        mgr.save(data)
        loaded = mgr.load()
        assert loaded == data

    def test_get_provider_config_existing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text('[providers.inpost_locker]\ntoken = "tok"\n')
        mgr = ConfigManager(config_path)
        cfg = mgr.get_provider_config("inpost_locker")
        assert cfg == {"token": "tok"}

    def test_get_provider_config_missing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        mgr = ConfigManager(config_path)
        cfg = mgr.get_provider_config("nonexistent")
        assert cfg == {}

    def test_set_provider_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        mgr = ConfigManager(config_path)
        mgr.set_provider_config(
            "dpd_pickup",
            {
                "login": "admin",
                "password": "pass",
                "master_fid": 42,
            },
        )
        cfg = mgr.get_provider_config("dpd_pickup")
        assert cfg["login"] == "admin"
        assert cfg["master_fid"] == 42

    def test_get_flow_config(self, tmp_path: Path) -> None:
        """get_flow_config returns dict keyed by slug for ShipmentFlow."""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "[providers.inpost_locker]\n"
            'token = "t"\n'
            "organization_id = 1\n"
            "\n"
            "[providers.dpd_standard]\n"
            'login = "l"\n'
            'password = "p"\n'
            "master_fid = 1\n"
        )
        mgr = ConfigManager(config_path)
        flow_config = mgr.get_flow_config()
        assert "inpost_locker" in flow_config
        assert "dpd_standard" in flow_config
        assert flow_config["inpost_locker"]["token"] == "t"
