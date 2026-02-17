"""Tests for CLI in-memory protocol implementations."""

from decimal import Decimal

from sendparcel.enums import ShipmentStatus
from sendparcel.protocols import Order, Shipment, ShipmentRepository

from sendparcel_cli.models import CLIOrder, CLIShipment, CLIShipmentRepository


class TestCLIOrder:
    def test_satisfies_order_protocol(self) -> None:
        order = CLIOrder(
            sender_address={
                "first_name": "Jan",
                "last_name": "Nadawca",
                "phone": "500100200",
                "email": "sender@test.com",
                "street": "Testowa",
                "building_number": "1",
                "city": "Warszawa",
                "postal_code": "00-001",
                "country_code": "PL",
            },
            receiver_address={
                "first_name": "Anna",
                "last_name": "Odbiorca",
                "phone": "600200300",
                "email": "receiver@test.com",
            },
            parcels=[{"weight_kg": Decimal("2.5")}],
        )
        assert isinstance(order, Order)

    def test_get_total_weight(self) -> None:
        order = CLIOrder(
            sender_address={},
            receiver_address={},
            parcels=[
                {"weight_kg": Decimal("1.0")},
                {"weight_kg": Decimal("2.5")},
            ],
        )
        assert order.get_total_weight() == Decimal("3.5")

    def test_get_total_weight_empty(self) -> None:
        order = CLIOrder(
            sender_address={},
            receiver_address={},
            parcels=[],
        )
        assert order.get_total_weight() == Decimal("0")

    def test_get_parcels(self) -> None:
        parcels = [{"weight_kg": Decimal("1.0")}]
        order = CLIOrder(
            sender_address={},
            receiver_address={},
            parcels=parcels,
        )
        assert order.get_parcels() == parcels

    def test_get_sender_address(self) -> None:
        addr = {"first_name": "Jan", "city": "Warszawa"}
        order = CLIOrder(
            sender_address=addr,
            receiver_address={},
            parcels=[],
        )
        assert order.get_sender_address() == addr

    def test_get_receiver_address(self) -> None:
        addr = {"first_name": "Anna", "city": "Kraków"}
        order = CLIOrder(
            sender_address={},
            receiver_address=addr,
            parcels=[],
        )
        assert order.get_receiver_address() == addr


class TestCLIShipment:
    def test_satisfies_shipment_protocol(self) -> None:
        shipment = CLIShipment(provider="inpost_locker")
        assert isinstance(shipment, Shipment)

    def test_defaults(self) -> None:
        shipment = CLIShipment(provider="dpd_standard")
        assert shipment.status == ShipmentStatus.NEW
        assert shipment.external_id == ""
        assert shipment.tracking_number == ""
        assert shipment.label_url == ""
        assert shipment.id  # auto-generated, non-empty

    def test_id_is_unique(self) -> None:
        s1 = CLIShipment(provider="test")
        s2 = CLIShipment(provider="test")
        assert s1.id != s2.id

    def test_mutable_fields(self) -> None:
        shipment = CLIShipment(provider="test")
        shipment.external_id = "ext-123"
        shipment.tracking_number = "TRACK-456"
        shipment.label_url = "https://example.com/label.pdf"
        shipment.status = ShipmentStatus.CREATED
        assert shipment.external_id == "ext-123"
        assert shipment.tracking_number == "TRACK-456"
        assert shipment.status == ShipmentStatus.CREATED


class TestCLIShipmentRepository:
    def test_satisfies_repository_protocol(self) -> None:
        repo = CLIShipmentRepository()
        assert isinstance(repo, ShipmentRepository)

    async def test_create(self) -> None:
        repo = CLIShipmentRepository()
        shipment = await repo.create(
            provider="inpost_locker",
            status=ShipmentStatus.NEW,
        )
        assert isinstance(shipment, CLIShipment)
        assert shipment.provider == "inpost_locker"
        assert shipment.status == ShipmentStatus.NEW

    async def test_get_by_id(self) -> None:
        repo = CLIShipmentRepository()
        created = await repo.create(
            provider="test",
            status=ShipmentStatus.NEW,
        )
        fetched = await repo.get_by_id(created.id)
        assert fetched.id == created.id

    async def test_get_by_id_not_found(self) -> None:
        import pytest

        repo = CLIShipmentRepository()
        with pytest.raises(KeyError):
            await repo.get_by_id("nonexistent")

    async def test_save(self) -> None:
        repo = CLIShipmentRepository()
        shipment = await repo.create(
            provider="test",
            status=ShipmentStatus.NEW,
        )
        shipment.external_id = "ext-999"
        saved = await repo.save(shipment)
        assert saved.external_id == "ext-999"
        fetched = await repo.get_by_id(shipment.id)
        assert fetched.external_id == "ext-999"

    async def test_update_status(self) -> None:
        repo = CLIShipmentRepository()
        shipment = await repo.create(
            provider="test",
            status=ShipmentStatus.NEW,
        )
        updated = await repo.update_status(
            shipment.id,
            ShipmentStatus.CREATED,
            external_id="ext-1",
        )
        assert updated.status == ShipmentStatus.CREATED
        assert updated.external_id == "ext-1"
