"""Configuration file management."""

import tomllib
from pathlib import Path

import tomli_w


def get_default_config_path() -> Path:
    """Return the default config file path.

    Uses ~/.config/sendparcel/config.toml (XDG convention).
    """
    return Path.home() / ".config" / "sendparcel" / "config.toml"


class ConfigManager:
    """Read and write sendparcel CLI configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_default_config_path()

    def load(self) -> dict:
        """Load config from TOML file. Returns empty dict if missing."""
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "rb") as f:
            return tomllib.load(f)

    def save(self, data: dict) -> None:
        """Save config to TOML file, creating parent directories."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "wb") as f:
            tomli_w.dump(data, f)

    def get_provider_config(self, slug: str) -> dict:
        """Get configuration for a specific provider."""
        config = self.load()
        return config.get("providers", {}).get(slug, {})

    def set_provider_config(self, slug: str, provider_config: dict) -> None:
        """Set configuration for a specific provider and save."""
        config = self.load()
        if "providers" not in config:
            config["providers"] = {}
        config["providers"][slug] = provider_config
        self.save(config)

    def get_flow_config(self) -> dict:
        """Get config dict keyed by provider slug for ShipmentFlow.

        ShipmentFlow expects config like:
            {"inpost_locker": {"token": "...", ...}, "dpd_standard": {...}}
        """
        config = self.load()
        return config.get("providers", {})
