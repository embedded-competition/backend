"""수신 기록 저장소 통합 테스트. wide 컬럼 왕복이 핵심이다."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, GasChannel, SignatureFlags
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading


class TestIdempotentInsert:
    def test_stored_reading_carries_its_key(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """이 값이 없으면 이 기록을 가리키는 FK(alerts.reading_id)가 전부 빈다."""
        stored = readings.add_if_absent(a_reading(now, device_id=device_id))

        assert stored is not None
        assert stored.key > 0

    def test_duplicate_frame_is_ignored(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """LoRa 재전송 멱등 — 같은 (device, measured_at, seq)는 한 번만 저장."""
        reading = a_reading(now, device_id=device_id)
        readings.add_if_absent(reading)

        assert readings.add_if_absent(reading) is None
        assert readings.latest(device_id) is not None


class TestValueRoundTrip:
    def test_channels_roundtrip_through_wide_columns(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(
                    now,
                    values={
                        Measure.VOC_DEV: 6.2,
                        Measure.VOC_SLOPE: 7.1,
                        Measure.H2_DEV: 1.0,
                    },
                ),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        voc = stored.channel(GasChannel.VOC)
        assert voc is not None
        assert voc.deviation == pytest.approx(6.2)
        assert voc.slope == pytest.approx(7.1)
        # 값이 하나도 없는 채널은 도메인에 올리지 않는다 (미장착 센서와 구분)
        assert stored.channel(GasChannel.CO) is None

    def test_timestamps_survive_as_aware_utc(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """SQLite에 tz 타입이 없어 naive로 돌아오는 함정을 UtcDateTime이 막는다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.measured_at.tzinfo is not None
        assert stored.measured_at == now

    def test_signature_roundtrip(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(
                    now,
                    signature=SignatureFlags(rise=True, hold=False, no_recover=True, hold_s=18),
                ),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.signature is not None
        assert stored.frame.signature.hold_s == 18
        # 3요소가 각각 왕복해야 한다 — 하나로 뭉치면 어느 게 빠졌는지 잃는다
        assert stored.frame.signature.rise is True
        assert stored.frame.signature.hold is False
        assert stored.frame.signature.no_recover is True

    def test_signature_absent_stays_none(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """노드가 signature를 안 보낸 경우와 '전부 false'를 구분해야 한다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.signature is None

    def test_gps_and_batt_roundtrip(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(now, location=Coordinates(lat=37.5573, lon=127.0329), batt_mv=3960),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.location is not None
        assert stored.frame.location.lat == pytest.approx(37.5573)
        assert stored.frame.batt_mv == 3960

    def test_gps_missing_is_null_not_zero(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """GPS 미장착(정합화 C2)을 좌표 0,0으로 뭉개지 않는다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.location is None


class TestRangeQuery:
    def test_respects_bounds_and_orders_newest_first(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _fill(readings, device_id, now, count=5)

        window = readings.list_in_range(
            device_id,
            start=now + timedelta(minutes=1),
            end=now + timedelta(minutes=3),
            limit=10,
        )

        assert len(window) == 3
        assert [r.seq for r in window] == [3, 2, 1]

    def test_limit_caps_result(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _fill(readings, device_id, now, count=5)

        window = readings.list_in_range(device_id, start=now, end=now + timedelta(hours=1), limit=2)

        assert len(window) == 2


def _fill(
    readings: SqlAlchemyReadingRepository, device_id: int, now: datetime, *, count: int
) -> None:
    for offset in range(count):
        at = now + timedelta(minutes=offset)
        readings.add_if_absent(
            a_reading(
                at,
                device_id=device_id,
                frame=a_frame(at, seq=offset, state=AlertState.NORMAL),
            )
        )
