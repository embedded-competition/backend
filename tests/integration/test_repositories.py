"""repository 통합 테스트. 스키마는 Alembic으로 만든다 — 마이그레이션도 같이 검증된다."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.domain.models import Alert, Device, Reading
from app.domain.value_objects import AlertState, ChannelReading, DeviceId, GasChannel
from app.infrastructure.db.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemyReadingRepository,
)


@pytest.fixture
def devices(session: Session) -> SqlAlchemyDeviceRepository:
    return SqlAlchemyDeviceRepository(session)


@pytest.fixture
def readings(session: Session) -> SqlAlchemyReadingRepository:
    return SqlAlchemyReadingRepository(session)


@pytest.fixture
def alerts(session: Session) -> SqlAlchemyAlertRepository:
    return SqlAlchemyAlertRepository(session)


@pytest.fixture
def saved_device(devices: SqlAlchemyDeviceRepository, now: datetime) -> Iterator[Device]:
    yield devices.save(Device(hw_id=DeviceId("44bd8d239c28"), label="1호차", registered_at=now))


def _reading(device_id: int, now: datetime, **kwargs: object) -> Reading:
    defaults: dict[str, object] = {
        "device_id": device_id,
        "seq": 1,
        "measured_at": now,
        "received_at": now,
        "frame_version": 1,
        "state": AlertState.NORMAL,
    }
    defaults.update(kwargs)
    return Reading(**defaults)  # type: ignore[arg-type]


class TestDeviceRepository:
    def test_save_then_lookup_by_hw_id(
        self, devices: SqlAlchemyDeviceRepository, saved_device: Device
    ) -> None:
        found = devices.get_by_hw_id(DeviceId("44bd8d239c28"))

        assert found is not None
        assert found.id == saved_device.id
        assert found.label == "1호차"

    def test_unknown_hw_id_returns_none(self, devices: SqlAlchemyDeviceRepository) -> None:
        assert devices.get_by_hw_id(DeviceId("deadbeef")) is None

    def test_save_updates_existing_row(
        self, devices: SqlAlchemyDeviceRepository, saved_device: Device, now: datetime
    ) -> None:
        saved_device.observe(seq=7, at=now, state=AlertState.WATCH)
        devices.save(saved_device)

        reloaded = devices.get(saved_device.id or 0)

        assert reloaded is not None
        assert reloaded.last_seq == 7
        assert reloaded.last_state is AlertState.WATCH


class TestReadingRepository:
    def test_add_returns_true_first_time(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        assert readings.add_if_absent(_reading(saved_device.id or 0, now)) is True

    def test_duplicate_frame_is_ignored(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        """LoRa 재전송 멱등 — 같은 (device, measured_at, seq)는 한 번만 저장."""
        reading = _reading(saved_device.id or 0, now)
        readings.add_if_absent(reading)

        assert readings.add_if_absent(reading) is False
        assert readings.latest(saved_device.id or 0) is not None

    def test_channels_roundtrip_through_wide_columns(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        readings.add_if_absent(
            _reading(
                saved_device.id or 0,
                now,
                channels=(
                    ChannelReading(channel=GasChannel.VOC, deviation=6.2, slope=7.1),
                    ChannelReading(channel=GasChannel.H2, deviation=1.0, slope=None),
                ),
            )
        )

        stored = readings.latest(saved_device.id or 0)

        assert stored is not None
        voc = stored.channel(GasChannel.VOC)
        assert voc is not None
        assert voc.deviation == pytest.approx(6.2)
        assert voc.slope == pytest.approx(7.1)
        # 값이 하나도 없는 채널은 도메인에 올리지 않는다 (미장착 센서와 구분)
        assert stored.channel(GasChannel.CO) is None

    def test_timestamps_survive_as_aware_utc(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        """SQLite에 tz 타입이 없어 naive로 돌아오는 함정을 UtcDateTime이 막는다."""
        readings.add_if_absent(_reading(saved_device.id or 0, now))

        stored = readings.latest(saved_device.id or 0)

        assert stored is not None
        assert stored.measured_at.tzinfo is not None
        assert stored.measured_at == now

    def test_range_query_respects_bounds_and_limit(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        device_id = saved_device.id or 0
        for offset in range(5):
            readings.add_if_absent(_reading(device_id, now + timedelta(minutes=offset), seq=offset))

        window = readings.list_in_range(
            device_id,
            start=now + timedelta(minutes=1),
            end=now + timedelta(minutes=3),
            limit=10,
        )

        assert len(window) == 3
        assert [r.seq for r in window] == [3, 2, 1]  # 최신순

    def test_limit_caps_result(
        self, readings: SqlAlchemyReadingRepository, saved_device: Device, now: datetime
    ) -> None:
        device_id = saved_device.id or 0
        for offset in range(5):
            readings.add_if_absent(_reading(device_id, now + timedelta(minutes=offset), seq=offset))

        window = readings.list_in_range(device_id, start=now, end=now + timedelta(hours=1), limit=2)

        assert len(window) == 2


class TestAlertRepository:
    def test_active_alerts_exclude_acknowledged(
        self, alerts: SqlAlchemyAlertRepository, saved_device: Device, now: datetime
    ) -> None:
        device_id = saved_device.id or 0
        open_alert = alerts.add(
            Alert(
                device_id=device_id,
                from_state=AlertState.NORMAL,
                to_state=AlertState.ALARM,
                occurred_at=now,
                detected_at=now,
            )
        )
        closed = alerts.add(
            Alert(
                device_id=device_id,
                from_state=AlertState.NORMAL,
                to_state=AlertState.WATCH,
                occurred_at=now - timedelta(hours=1),
                detected_at=now - timedelta(hours=1),
            )
        )
        closed.acknowledge(at=now)
        alerts.save(closed)

        active = alerts.list_active()

        assert [a.id for a in active] == [open_alert.id]

    def test_acknowledge_persists(
        self, alerts: SqlAlchemyAlertRepository, saved_device: Device, now: datetime
    ) -> None:
        alert = alerts.add(
            Alert(
                device_id=saved_device.id or 0,
                from_state=AlertState.WATCH,
                to_state=AlertState.ALARM,
                occurred_at=now,
                detected_at=now,
            )
        )
        alert.acknowledge(at=now + timedelta(minutes=3), note="현장 확인")
        alerts.save(alert)

        reloaded = alerts.get(alert.id or 0)

        assert reloaded is not None
        assert reloaded.is_active is False
        assert reloaded.acknowledged_note == "현장 확인"
        assert reloaded.acknowledged_at == (now + timedelta(minutes=3)).astimezone(UTC)
