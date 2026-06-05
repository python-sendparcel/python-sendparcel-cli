"""In-memory protocol implementations for CLI use."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sendparcel.enums import ShipmentStatus


@dataclass(frozen=False, slots=True)
class CLIShipment:
    """In-memory Shipment for CLI.

    Satisfies sendparcel Shipment protocol.
    """

    provider: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = ShipmentStatus.NEW.value
    external_id: str = ""
    tracking_number: str = ""


class CLIShipmentRepository:
    """In-memory repository for CLI.

    Satisfies sendparcel ShipmentRepository protocol.
    """

    def __init__(self) -> None:
        self._store: dict[str, CLIShipment] = {}

    async def get_by_id(self, shipment_id: str) -> CLIShipment:
        """Get shipment by ID. Raises KeyError if not found."""
        return self._store[shipment_id]

    async def create(self, **kwargs: Any) -> CLIShipment:
        """Create and store a new shipment."""
        shipment = CLIShipment(
            provider=kwargs["provider"],
            status=kwargs.get("status", ShipmentStatus.NEW.value),
        )
        self._store[shipment.id] = shipment
        return shipment

    async def save(self, shipment: CLIShipment) -> CLIShipment:
        """Persist shipment changes."""
        self._store[shipment.id] = shipment
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields: Any
    ) -> CLIShipment:
        """Update shipment status and optional fields."""
        shipment = self._store[shipment_id]
        shipment.status = status
        for key, value in fields.items():
            if hasattr(shipment, key):
                setattr(shipment, key, value)
        return shipment

    async def update_fields(
        self, shipment_id: str, **fields: Any
    ) -> CLIShipment:
        """Atomically update shipment fields by ID."""
        shipment = self._store[shipment_id]
        for key, value in fields.items():
            if hasattr(shipment, key):
                setattr(shipment, key, value)
        return shipment

    async def delete(self, shipment_id: str) -> None:
        """Delete a shipment by ID."""
        self._store.pop(shipment_id, None)

    def get_by_id_sync(
        self, shipment_id: str, *, for_update: bool = False
    ) -> CLIShipment:
        """Synchronous fetch — required for transactional helpers."""
        return self._store[shipment_id]

    async def find_by_reference(
        self, provider: str, reference_id: str
    ) -> CLIShipment | None:
        """Find a shipment by provider and reference ID."""
        for shipment in self._store.values():
            if (
                shipment.provider == provider
                and shipment.tracking_number == reference_id
            ):
                return shipment
        return None

    async def create_with_idempotency_key(
        self,
        provider: str,
        status: str,
        reference_id: str,
        **kwargs: Any,
    ) -> tuple[CLIShipment | None, CLIShipment | None]:
        """Atomically check for existing + create if absent."""
        existing = await self.find_by_reference(provider, reference_id)
        if existing is not None:
            return (existing, None)
        shipment = CLIShipment(
            provider=provider,
            status=status,
            tracking_number=reference_id,
        )
        self._store[shipment.id] = shipment
        return (None, shipment)
