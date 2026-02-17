"""In-memory protocol implementations for CLI use."""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sendparcel.enums import ShipmentStatus
from sendparcel.types import AddressInfo, ParcelInfo


@dataclass
class CLIOrder:
    """In-memory Order for CLI testing. Satisfies sendparcel Order protocol."""

    sender_address: AddressInfo
    receiver_address: AddressInfo
    parcels: list[ParcelInfo]

    def get_total_weight(self) -> Decimal:
        """Sum of all parcel weights."""
        return sum(
            (p["weight_kg"] for p in self.parcels),
            start=Decimal("0"),
        )

    def get_parcels(self) -> list[ParcelInfo]:
        """Return parcel list."""
        return self.parcels

    def get_sender_address(self) -> AddressInfo:
        """Return sender address."""
        return self.sender_address

    def get_receiver_address(self) -> AddressInfo:
        """Return receiver address."""
        return self.receiver_address


@dataclass
class CLIShipment:
    """In-memory Shipment for CLI.

    Satisfies sendparcel Shipment protocol.
    """

    provider: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = ShipmentStatus.NEW
    external_id: str = ""
    tracking_number: str = ""
    label_url: str = ""


class CLIShipmentRepository:
    """In-memory repository for CLI.

    Satisfies sendparcel ShipmentRepository protocol.
    """

    def __init__(self) -> None:
        self._store: dict[str, CLIShipment] = {}

    async def get_by_id(self, shipment_id: str) -> CLIShipment:
        """Get shipment by ID. Raises KeyError if not found."""
        return self._store[shipment_id]

    async def create(self, **kwargs) -> CLIShipment:
        """Create and store a new shipment."""
        shipment = CLIShipment(
            provider=kwargs["provider"],
            status=kwargs.get("status", ShipmentStatus.NEW),
        )
        self._store[shipment.id] = shipment
        return shipment

    async def save(self, shipment: CLIShipment) -> CLIShipment:
        """Persist shipment changes."""
        self._store[shipment.id] = shipment
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields
    ) -> CLIShipment:
        """Update shipment status and optional fields."""
        shipment = self._store[shipment_id]
        shipment.status = status
        for key, value in fields.items():
            if hasattr(shipment, key):
                setattr(shipment, key, value)
        return shipment
