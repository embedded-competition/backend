"""앱 spec §④ 텔레메트리 폴링. 응답 키는 앱과의 계약이라 회귀가 치명적이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.readings import RadioQuality
from app.domain.value_objects import AlertState, SignatureFlags
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading
from tests.integration.api.client import RegisteredDevice


class TestLatest:
    async def test_before_any_frame(self, device: RegisteredDevice) -> None:
        """프레임을 한 번도 못 받았어도 상태를 지어내지 않는다."""
        response = await device.get("telemetry/latest")

        assert response.status_code == 200
        payload = response.json()
        assert payload["state"] == "WARMUP"
        assert payload["module"]["lastSeen"] is None

    async def test_returns_camel_case_contract(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        SqlAlchemyReadingRepository(session).add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                radio=RadioQuality(rssi=-74),
                frame=a_frame(
                    now,
                    seq=7,
                    state=AlertState.WATCH,
                    values={
                        Measure.VOC_DEV: 3.1,
                        Measure.VOC_SLOPE: 2.4,
                        Measure.TEMP_C: 24.5,
                        Measure.HUMIDITY_PCT: 41.0,
                    },
                    signature=SignatureFlags(rise=True, hold=False, no_recover=True, hold_s=18),
                    batt_mv=3960,
                    location=Coordinates(lat=37.5573, lon=127.0329),
                ),
            )
        )
        session.commit()

        payload = (await device.get("telemetry/latest")).json()

        assert payload["state"] == "WATCH"
        assert payload["gas"] == {"devZ": 3.1, "slope": 2.4}
        assert payload["signature"]["noRecover"] is True
        assert payload["signature"]["holdS"] == 18
        assert payload["location"] == {"lat": 37.5573, "lon": 127.0329}
        assert payload["module"]["battMv"] == 3960
        assert payload["module"]["rssi"] == -74

    async def test_raw_sensor_fields_are_absent(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        """raw는 서버가 채울 수 없다 (정합화 B2). 0으로 채워 내보내지 않는다."""
        SqlAlchemyReadingRepository(session).add_if_absent(a_reading(now, device_id=device_id))
        session.commit()

        payload = (await device.get("telemetry/latest")).json()

        assert "sraw" not in payload["gas"]
        assert "mv" not in payload["h2"]


class TestHistory:
    async def test_aggregates_by_hour(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        readings = SqlAlchemyReadingRepository(session)
        base = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
        for index, state in enumerate([AlertState.NORMAL, AlertState.WATCH]):
            at = base + timedelta(minutes=5 * index)
            readings.add_if_absent(
                a_reading(
                    at,
                    device_id=device_id,
                    frame=a_frame(
                        at, seq=index, state=state, values={Measure.VOC_DEV: float(index)}
                    ),
                )
            )
        session.commit()

        payload = (await device.get("telemetry/history", params={"date": "2026-08-08"})).json()

        assert len(payload["samples"]) == 1
        sample = payload["samples"][0]
        assert sample["hour"] == "14:00"
        # 한 시간 안 최악값을 쓴다 — 평균 내면 경보가 묻힌다
        assert sample["state"] == "WATCH"
        assert sample["gas"]["devZ"] == pytest.approx(0.5)
