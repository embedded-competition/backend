"""앱 spec §④ 텔레메트리 폴링. 응답 키는 앱과의 계약이라 회귀가 치명적이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.telemetry_service import _EVENT_LIMIT
from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.readings import RadioQuality
from app.domain.value_objects import AlertState, SignatureFlags
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading, an_event
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
    async def test_buckets_by_requested_interval(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base + timedelta(hours=1), seq=1, voc_dev=1.0)
        _store(
            session,
            device_id,
            base + timedelta(hours=3),
            seq=2,
            voc_dev=8.0,
            state=AlertState.WATCH,
        )

        payload = (
            await device.get(
                "telemetry/history",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=4)).isoformat(),
                    "interval": "2h",
                },
            )
        ).json()

        assert payload["range"]["interval"] == "2h"
        assert payload["range"]["bucketCount"] == 2
        assert [b["start"] for b in payload["buckets"]] == [
            base.isoformat().replace("+00:00", "Z"),
            (base + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        ]
        assert payload["buckets"][1]["state"] == "WATCH"
        assert payload["buckets"][1]["gas"]["devZ"] == pytest.approx(8.0)

    async def test_truncated_events_are_countable(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        """잘린 응답이 완전한 응답처럼 보이면 안 된다.

        events는 상한까지만 담긴다. eventCount가 없으면 받은 쪽은 "기록이 N개"인지
        "N개까지만 준 것"인지 구별할 수 없다.
        """
        base = datetime(2026, 8, 4, tzinfo=UTC)
        stored = _EVENT_LIMIT + 5
        events = SqlAlchemyEventRepository(session)
        for offset in range(stored):
            events.add(an_event(base + timedelta(seconds=offset), device_id=device_id))
        session.commit()

        payload = (
            await device.get(
                "telemetry/history",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=1)).isoformat(),
                    "interval": "10m",
                },
            )
        ).json()

        assert payload["eventCount"] == stored
        assert len(payload["events"]) == _EVENT_LIMIT
        assert len(payload["events"]) < payload["eventCount"]

    async def test_bad_interval_is_rejected(self, device: RegisteredDevice, now: datetime) -> None:
        response = await device.get(
            "telemetry/history",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(hours=1)).isoformat(),
                "interval": "2주",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_interval"

    async def test_too_many_buckets_is_rejected(
        self, device: RegisteredDevice, now: datetime
    ) -> None:
        response = await device.get(
            "telemetry/history",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(days=90)).isoformat(),
                "interval": "1m",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_interval"


class TestSummary:
    async def test_past_period_reports_peaks_without_current(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        """지난 구간은 실시간 값이 없다 — 화면은 기간 중 최고치를 쓴다."""
        base = datetime(2020, 5, 1, tzinfo=UTC)
        peak_at = base + timedelta(hours=2)
        _store(session, device_id, base, seq=1, voc_dev=1.0)
        _store(session, device_id, peak_at, seq=2, voc_dev=8.1, state=AlertState.WATCH)

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(days=1)).isoformat(),
                },
            )
        ).json()

        assert payload["range"]["live"] is False
        assert payload["current"] is None
        assert payload["state"] == "WATCH"
        assert payload["peaks"]["gas"]["devZ"] == pytest.approx(8.1)
        assert payload["peaks"]["gas"]["at"] == peak_at.isoformat().replace("+00:00", "Z")
        assert payload["peaks"]["co"] is None

    async def test_period_covering_now_reports_current(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        now = datetime.now(UTC)
        _store(session, device_id, now - timedelta(minutes=1), seq=1, voc_dev=2.0)

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": (now - timedelta(hours=1)).isoformat(),
                    "to": (now + timedelta(hours=1)).isoformat(),
                },
            )
        ).json()

        assert payload["range"]["live"] is True
        assert payload["current"] is not None
        assert payload["current"]["gas"]["devZ"] == pytest.approx(2.0)

    async def test_empty_period_reports_no_state(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        """관측이 없는 구간은 null이다.

        기기의 현재 상태를 과거 구간의 답으로 쓰면, 그 기간에 아무 일도 없었는데도
        화면이 "이 기간 중 경보 단계까지 갔어요"를 띄운다. 반대로 지금이 정상이면
        과거의 실제 경보가 정상으로 덮인다. last_state를 ALARM으로 세워 두고
        검증해야 그 폴백이 되살아나는 것을 잡는다.
        """
        _set_last_state(session, device_id, AlertState.ALARM)

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": (now - timedelta(days=2)).isoformat(),
                    "to": (now - timedelta(days=1)).isoformat(),
                },
            )
        ).json()

        assert payload["state"] is None
        assert payload["peaks"]["gas"] is None
        assert payload["eventCount"] == 0

    async def test_observed_period_reports_worst_state(
        self, device: RegisteredDevice, session: Session, device_id: int
    ) -> None:
        """관측이 있으면 기기의 현재 상태와 무관하게 구간 중 최악이 나온다."""
        base = datetime(2020, 5, 1, tzinfo=UTC)
        _set_last_state(session, device_id, AlertState.NORMAL)
        _store(session, device_id, base, seq=1, voc_dev=1.0)
        _store(
            session,
            device_id,
            base + timedelta(hours=1),
            seq=2,
            voc_dev=8.1,
            state=AlertState.WATCH,
        )

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(days=1)).isoformat(),
                },
            )
        ).json()

        assert payload["state"] == "WATCH"


def _set_last_state(session: Session, device_id: int, state: AlertState) -> None:
    repository = SqlAlchemyDeviceRepository(session)
    found = repository.get(device_id)
    assert found is not None
    found.observe(seq=1, at=datetime(2026, 1, 1, tzinfo=UTC), state=state)
    repository.save(found)
    session.commit()


def _store(
    session: Session,
    device_id: int,
    at: datetime,
    *,
    seq: int,
    voc_dev: float,
    state: AlertState = AlertState.NORMAL,
) -> None:
    SqlAlchemyReadingRepository(session).add_if_absent(
        a_reading(
            at,
            device_id=device_id,
            frame=a_frame(at, seq=seq, state=state, values={Measure.VOC_DEV: voc_dev}),
        )
    )
    session.commit()
