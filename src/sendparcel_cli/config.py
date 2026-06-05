"""Configuration file management."""

from __future__ import annotations

import logging
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import tomli_w

logger = logging.getLogger(__name__)


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file with error handling.

    Returns an empty dict if the file is empty or contains no valid TOML.
    Raises ``ValueError`` for malformed TOML.
    """
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed TOML in {path}: {exc}") from exc
    except ValueError as exc:
        # Empty file or non-TOML content
        if "could not determine a parser" in str(exc):
            return {}
        raise


def get_default_config_path() -> Path:
    """Return the default config file path.

    Uses ~/.config/sendparcel/config.toml (XDG convention).
    """
    return Path.home() / ".config" / "sendparcel" / "config.toml"


class ConfigManager:
    """Read and write sendparcel CLI configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_default_config_path()

    def load(self) -> dict[str, Any]:
        """Load config from TOML file.

        Returns an empty dict if the file is missing. Raises ValueError
        for malformed TOML content.
        """
        if not self.config_path.exists():
            return {}
        return _parse_toml(self.config_path)

    def save(self, data: Mapping[str, Any]) -> None:
        """Save config to TOML file, creating parent directories."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "wb") as f:
            tomli_w.dump(data, f)

    def get_provider_config(self, slug: str) -> dict[str, Any]:
        """Get configuration for a specific provider."""
        config = self.load()
        providers = config.get("providers", {})
        if not isinstance(providers, dict):
            return {}
        return cast(dict[str, Any], providers.get(slug, {}))

    def set_provider_config(
        self, slug: str, provider_config: dict[str, Any]
    ) -> None:
        """Set configuration for a specific provider and save."""
        config = self.load()
        if "providers" not in config:
            config["providers"] = {}
        config["providers"][slug] = provider_config
        self.save(config)

    def get_flow_config(self) -> dict[str, Any]:
        """Get config dict keyed by provider slug for ShipmentFlow.

        ShipmentFlow expects config like:
            {"inpost_locker": {"token": "...", ...}, "dpd_standard": {...}}
        """
        config = self.load()
        providers = config.get("providers", {})
        if not isinstance(providers, dict):
            return {}
        return cast(dict[str, Any], providers)
