"""기기 저장소 통합 테스트."""

from __future__ import annotations

from datetime import datetime

from app.domain.device import Device
from app.domain.value_objects import AlertState, DeviceId
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository


class TestLookup:
    def test_save_then_lookup_by_hw_id(
        self, devices: SqlAlchemyDeviceRepository, saved_device: Device
    ) -> None:
        found = devices.get_by_hw_id(DeviceId("44bd8d239c28"))

        assert found is not None
        assert found.id == saved_device.id
        assert found.label == "1호차"

    def test_unknown_hw_id_returns_none(self, devices: SqlAlchemyDeviceRepository) -> None:
        assert devices.get_by_hw_id(DeviceId("deadbeef")) is None


class TestSave:
    def test_save_updates_existing_row(
        self,
        devices: SqlAlchemyDeviceRepository,
        saved_device: Device,
        device_id: int,
        now: datetime,
    ) -> None:
        saved_device.observe(seq=7, at=now, state=AlertState.WATCH)
        devices.save(saved_device)

        reloaded = devices.get(device_id)

        assert reloaded is not None
        assert reloaded.last_seq == 7
        assert reloaded.last_state is AlertState.WATCH
