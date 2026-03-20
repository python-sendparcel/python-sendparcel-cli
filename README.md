# python-sendparcel-cli

[![PyPI](https://img.shields.io/pypi/v/python-sendparcel-cli.svg)](https://pypi.org/project/python-sendparcel-cli/)
[![Python Version](https://img.shields.io/pypi/pyversions/python-sendparcel-cli.svg)](https://pypi.org/project/python-sendparcel-cli/)
[![License](https://img.shields.io/pypi/l/python-sendparcel-cli.svg)](https://github.com/python-sendparcel/python-sendparcel-cli/blob/main/LICENSE)

Developer CLI for testing and debugging [python-sendparcel](https://github.com/python-sendparcel/python-sendparcel) providers.

> **Alpha (0.1.0)** — API may change between minor releases. Pin your dependency if you use it in production.

## Features

- **Four commands** — `init`, `providers`, `check-config`, and `create-label` cover the full provider testing workflow.
- **Auto-generated config** — `init` discovers all installed providers and generates a TOML config file with required fields from each provider's `config_schema`.
- **Provider discovery** — `providers` lists every installed provider with its slug, display name, confirmation method, supported countries, and configuration status.
- **Configuration validation** — `check-config` inspects a specific provider's config fields, showing required/type/value/status with secret masking.
- **End-to-end label creation** — `create-label` creates a test shipment and downloads the label through the full `ShipmentFlow` pipeline.
- **Flexible address input** — sender and receiver addresses can be provided via JSON files, inline CLI flags, or a combination of both (flags override file values).
- **Provider kwargs passthrough** — arbitrary provider-specific parameters via `--kwarg KEY=VALUE` flags.
- **Rich output** — formatted tables via [Rich](https://github.com/Textualize/rich) for all command output.
- **TOML configuration** — config stored at `~/.config/sendparcel/config.toml` (XDG convention), overridable via `--config` flag or `SENDPARCEL_CONFIG` environment variable.
- **Async-first** — uses `anyio` to run the async `ShipmentFlow` from the synchronous CLI context.

## Installation

```bash
uv add python-sendparcel-cli
```

Or with pip:

```bash
pip install python-sendparcel-cli
```

This installs the `sendparcel` command. Providers are auto-discovered via the `sendparcel.providers` entry-point group — install any provider plugin (e.g. `python-sendparcel-inpost`, `python-sendparcel-dpdpl`) and it will appear automatically.

## Quick Start

### Initialize configuration

Generate a config file with empty sections for all installed providers:

```bash
sendparcel init
# Config created at /home/user/.config/sendparcel/config.toml
```

### List installed providers

```bash
sendparcel providers
```

Output (example with InPost and DPD installed):

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Installed Providers                          │
├────────────────┬──────────────────┬────────┬───────────┬───────────┤
│ Slug           │ Name             │ Method │ Countries │ Config    │
├────────────────┼──────────────────┼────────┼───────────┼───────────┤
│ inpost_locker  │ InPost Paczkomat │ PUSH   │ PL        │ OK        │
│ inpost_courier │ InPost Kurier    │ PUSH   │ PL        │ ---       │
│ dpd_standard   │ DPD Kurier       │ NONE   │ PL        │ OK        │
└────────────────┴──────────────────┴────────┴───────────┴───────────┘
```

### Check provider configuration

```bash
sendparcel check-config inpost_locker
```

Output shows each config field with its required/type/value/status:

```
┌──────────────────────────────────────────────────────────────────┐
│                     Config: inpost_locker                        │
├──────────────────┬──────────┬──────┬────────────────┬────────────┤
│ Field            │ Required │ Type │ Value          │ Status     │
├──────────────────┼──────────┼──────┼────────────────┼────────────┤
│ token            │ Yes      │ str  │ ***            │ OK         │
│ organization_id  │ Yes      │ int  │ 12345          │ OK         │
│ sandbox          │ No       │ bool │ (default: False)│ OK        │
└──────────────────┴──────────┴──────┴────────────────┴────────────┘
```

Secret fields (like `token`) are masked in the output.

### Create a test label

Using JSON address files:

```bash
sendparcel create-label inpost_locker \
    --sender-file sender.json \
    --receiver-file receiver.json \
    --weight 2.5 \
    --output-dir ./labels \
    --kwarg target_point=KRA010
```

Using inline flags:

```bash
sendparcel create-label dpd_standard \
    --sender-first-name "Jan" \
    --sender-last-name "Nadawca" \
    --sender-phone "500100200" \
    --sender-email "sender@test.com" \
    --sender-street "Testowa" \
    --sender-building-number "1" \
    --sender-city "Warszawa" \
    --sender-postal-code "00-001" \
    --sender-country-code "PL" \
    --receiver-first-name "Anna" \
    --receiver-last-name "Odbiorca" \
    --receiver-phone "600200300" \
    --receiver-email "receiver@test.com" \
    --weight 2.5 \
    --output-dir ./labels
```

## Configuration

### Config file location

The CLI reads configuration from a TOML file. The location is resolved in this order:

1. `--config <path>` flag (highest priority)
2. `SENDPARCEL_CONFIG` environment variable
3. `~/.config/sendparcel/config.toml` (XDG default)

### Config file format

```toml
[providers.inpost_locker]
token = "your-shipx-api-token"
organization_id = 12345
sandbox = true

[providers.inpost_courier]
token = "your-shipx-api-token"
organization_id = 12345
sandbox = true

[providers.dpd_standard]
login = "your-dpd-login"
password = "your-dpd-password"
master_fid = 1495
sandbox = true
```

Each `[providers.<slug>]` section contains the key-value pairs expected by that provider's `config_schema`. Run `sendparcel init` to auto-generate this file with the correct fields for all installed providers.

## Commands

### `sendparcel init`

Discovers all installed providers via entry points and generates a config file with empty required fields and default values from each provider's `config_schema`.

| Option | Type | Default | Description |
|---|---|---|---|
| `--config` | `Path` | `~/.config/sendparcel/config.toml` | Config file path |

If the config file already exists, the command prints a notice and does **not** overwrite it.

### `sendparcel providers`

Lists all installed providers in a Rich table with their slug, display name, confirmation method, supported countries, and configuration status (OK if all required fields are present, `---` otherwise).

| Option | Type | Default | Description |
|---|---|---|---|
| `--config` | `Path` | `~/.config/sendparcel/config.toml` | Config file path |

### `sendparcel check-config <slug>`

Displays a detailed table for a specific provider's configuration. Each field shows whether it is required, its type, its current value (secrets are masked), and status (OK / MISSING / `---`).

| Argument/Option | Type | Default | Description |
|---|---|---|---|
| `slug` | `str` | *(required)* | Provider slug (e.g. `inpost_locker`) |
| `--config` | `Path` | `~/.config/sendparcel/config.toml` | Config file path |

Exits with code 1 if the provider slug is not found.

### `sendparcel create-label <slug>`

Creates a test shipment through the full `ShipmentFlow` pipeline (create shipment + create label) and saves the label file to disk.

| Argument/Option | Type | Default | Description |
|---|---|---|---|
| `slug` | `str` | *(required)* | Provider slug |
| `--config` | `Path` | `~/.config/sendparcel/config.toml` | Config file path |
| `--sender-file` | `Path` | `None` | Sender address JSON file |
| `--receiver-file` | `Path` | `None` | Receiver address JSON file |
| `--sender-first-name` | `str` | `None` | Sender first name (inline) |
| `--sender-last-name` | `str` | `None` | Sender last name (inline) |
| `--sender-phone` | `str` | `None` | Sender phone (inline) |
| `--sender-email` | `str` | `None` | Sender email (inline) |
| `--sender-street` | `str` | `None` | Sender street (inline) |
| `--sender-building-number` | `str` | `None` | Sender building number (inline) |
| `--sender-city` | `str` | `None` | Sender city (inline) |
| `--sender-postal-code` | `str` | `None` | Sender postal code (inline) |
| `--sender-country-code` | `str` | `None` | Sender country code (inline) |
| `--sender-company` | `str` | `None` | Sender company name (inline) |
| `--receiver-first-name` | `str` | `None` | Receiver first name (inline) |
| `--receiver-last-name` | `str` | `None` | Receiver last name (inline) |
| `--receiver-phone` | `str` | `None` | Receiver phone (inline) |
| `--receiver-email` | `str` | `None` | Receiver email (inline) |
| `--receiver-street` | `str` | `None` | Receiver street (inline) |
| `--receiver-building-number` | `str` | `None` | Receiver building number (inline) |
| `--receiver-city` | `str` | `None` | Receiver city (inline) |
| `--receiver-postal-code` | `str` | `None` | Receiver postal code (inline) |
| `--receiver-country-code` | `str` | `None` | Receiver country code (inline) |
| `--receiver-company` | `str` | `None` | Receiver company name (inline) |
| `--weight` | `float` | `1.0` | Parcel weight in kg |
| `--output-dir` | `Path` | `.` (current dir) | Directory to save the label file |
| `--kwarg` | `str` | `None` | Provider kwargs as `KEY=VALUE` (repeatable) |

Addresses can be provided three ways:

1. **JSON file only** — `--sender-file sender.json`
2. **Inline flags only** — `--sender-first-name "Jan" --sender-last-name "Nadawca" ...`
3. **Combined** — load a base from file, override specific fields with inline flags

At least one of sender or receiver address must be provided. Exits with code 1 if neither is given or if the provider slug is not found.

### Address JSON format

```json
{
    "first_name": "Jan",
    "last_name": "Nadawca",
    "phone": "500100200",
    "email": "sender@test.com",
    "street": "Testowa",
    "building_number": "1",
    "city": "Warszawa",
    "postal_code": "00-001",
    "country_code": "PL"
}
```

Optional fields: `company`, `flat_number`.

### Provider kwargs

Use `--kwarg KEY=VALUE` to pass provider-specific parameters. This flag is repeatable:

```bash
sendparcel create-label inpost_locker \
    --sender-file sender.json \
    --receiver-file receiver.json \
    --kwarg target_point=KRA010 \
    --kwarg sending_method=dispatch_order
```

These kwargs are forwarded directly to `ShipmentFlow.create_shipment()` and `ShipmentFlow.create_label()`.

## Label Handling

The `create-label` command saves labels to disk automatically:

- **Base64 payloads** from `label["content_base64"]` are decoded and saved as binary `.pdf` files.
- **URL results** from `label["url"]` are saved as text files containing the URL.
- Binary labels are saved as `label-<external_id>.pdf`; URL-only labels are saved as `label-<external_id>.txt`.

## Programmatic Usage

While primarily a CLI tool, the package exports its models and config manager for scripting:

```python
from sendparcel_cli import CLIShipment, CLIShipmentRepository, ConfigManager

# Load config
mgr = ConfigManager()  # uses default path
config = mgr.get_provider_config("inpost_locker")

# In-memory shipment + repository for scripting
shipment = CLIShipment(provider="inpost_locker")
repo = CLIShipmentRepository()
```

## Error Handling

The CLI handles errors with colored Rich output and appropriate exit codes:

| Situation | Behavior |
|---|---|
| Unknown provider slug | Prints `Provider '<slug>' not found.` in red, exits with code 1 |
| Missing sender/receiver addresses | Prints error message, exits with code 1 |
| Invalid `--kwarg` format | Raises `BadParameter` with format hint |
| Address file not found | Raises `BadParameter` with file path |
| Config file already exists (`init`) | Prints notice, does not overwrite |
| Label creation failure | Silently suppressed (shipment result is still displayed) |
| Any other provider error | Prints error in red, exits with code 1 |

## Supported Versions

| Dependency | Version |
|---|---|
| Python | >= 3.12 |
| python-sendparcel | >= 0.1.1 |
| typer | >= 0.15.0 |
| rich | >= 13.0 |
| tomli-w | >= 1.0 |

## Running Tests

The test suite uses **pytest** with **pytest-asyncio** (`asyncio_mode = "auto"`)
and **Typer's CliRunner** for command testing.

```bash
# Install dev dependencies
uv sync --extra dev

# Run the full test suite
uv run pytest

# With coverage
uv run pytest --cov=sendparcel_cli --cov-report=term-missing
```

Test coverage includes:

- **`test_config.py`** — `ConfigManager` load/save/roundtrip, provider config get/set, flow config format, default path resolution.
- **`test_main.py`** — all four CLI commands tested via `CliRunner`: `init` (create + no-overwrite), `providers` (listing), `check-config` (missing fields + unknown provider), `create-label` (JSON files, inline flags, kwarg passthrough, missing addresses).
- **`test_models.py`** — `CLIOrder`, `CLIShipment`, `CLIShipmentRepository` protocol conformance, weight calculation, unique IDs, mutable fields, async CRUD operations.
- **`test_output.py`** — Rich table rendering for providers, shipment results, and config checks including secret masking.

## Credits

- **Author**: Dominik Kozaczko ([dominik@kozaczko.info](mailto:dominik@kozaczko.info))
- Built on top of [python-sendparcel](https://github.com/python-sendparcel/python-sendparcel) core library
- CLI powered by [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)

## License

[MIT](https://github.com/python-sendparcel/python-sendparcel-cli/blob/main/LICENSE)
