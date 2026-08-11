"""앱 spec §④ 텔레메트리 폴링. 응답 키는 앱과의 계약이라 회귀가 치명적이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.telemetry_service import _EVENT_LIMIT
from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading, an_event
from tests.integration.api.client import MANAGEMENT_PHONE, UNKNOWN_MAC, SeededDevice


class TestMacAddressing:
    async def test_separators_do_not_matter(
        self, device: SeededDevice, client_period: dict[str, str]
    ) -> None:
        """앱이 라벨을 어떻게 읽어 오든 같은 기기를 가리켜야 한다."""
        bare = await device.client.get(
            "/devices/aabbccddeeff/telemetry/summary", params=client_period
        )

        assert bare.status_code == 200

    async def test_unknown_mac_is_404(
        self, device: SeededDevice, client_period: dict[str, str]
    ) -> None:
        response = await device.client.get(
            f"/devices/{UNKNOWN_MAC}/telemetry/summary", params=client_period
        )

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"

    async def test_malformed_mac_is_422(
        self, device: SeededDevice, client_period: dict[str, str]
    ) -> None:
        response = await device.client.get(
            "/devices/not-a-mac-addr/telemetry/summary", params=client_period
        )

        assert response.status_code == 422


class TestHistory:
    async def test_buckets_by_requested_interval(
        self, device: SeededDevice, session: Session, device_id: int
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

        assert payload["interval"] == "2h"
        assert payload["from"] == base.isoformat().replace("+00:00", "Z")
        assert [b["start"] for b in payload["buckets"]] == [
            base.isoformat().replace("+00:00", "Z"),
            (base + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        ]
        assert payload["buckets"][1]["state"] == "WATCH"
        assert payload["buckets"][1]["gas"]["value"] == pytest.approx(8.0)

    async def test_bucket_carries_no_timestamp_per_channel(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """칸의 시각은 start 하나다. 채널마다 되풀이할 이유가 없다."""
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0)

        payload = (
            await device.get(
                "telemetry/history",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=2)).isoformat(),
                    "interval": "1h",
                },
            )
        ).json()

        assert "at" not in payload["buckets"][0]["gas"]

    async def test_events_are_capped(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2026, 8, 4, tzinfo=UTC)
        events = SqlAlchemyEventRepository(session)
        for offset in range(_EVENT_LIMIT + 5):
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

        assert len(payload["events"]) == _EVENT_LIMIT

    async def test_bad_interval_is_rejected(self, device: SeededDevice, now: datetime) -> None:
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

    async def test_too_many_buckets_is_rejected(self, device: SeededDevice, now: datetime) -> None:
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
    async def test_past_period_reports_peaks(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """지난 구간의 값은 기간 중 최고치이고, at은 그 최고를 찍은 시각이다."""
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

        assert payload["live"] is False
        assert payload["state"] == "WATCH"
        assert payload["gas"]["value"] == pytest.approx(8.1)
        assert payload["gas"]["at"] == peak_at.isoformat().replace("+00:00", "Z")
        assert payload["co"] is None
        assert payload["managementPhone"] == MANAGEMENT_PHONE

    async def test_period_covering_now_reports_the_latest_reading(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """live면 최고치가 아니라 지금 값이다 — 같은 자리에 다른 의미가 담긴다."""
        now = datetime.now(UTC)
        _store(session, device_id, now - timedelta(minutes=5), seq=1, voc_dev=9.0)
        _store(session, device_id, now - timedelta(minutes=1), seq=2, voc_dev=2.0)

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": (now - timedelta(hours=1)).isoformat(),
                    "to": (now + timedelta(hours=1)).isoformat(),
                },
            )
        ).json()

        assert payload["live"] is True
        assert payload["gas"]["value"] == pytest.approx(2.0)

    async def test_empty_period_reports_no_state(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        """관측이 없는 구간은 null이다.

        기기의 현재 상태를 과거 구간의 답으로 쓰면, 그 기간에 아무 일도 없었는데도
        화면이 "이 기간 중 경보 단계까지 갔어요"를 띄운다. last_state를 ALARM으로
        세워 두고 검증해야 그 폴백이 되살아나는 것을 잡는다.
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
        assert payload["gas"] is None
        assert payload["at"] is None

    async def test_observed_period_reports_worst_state(
        self, device: SeededDevice, session: Session, device_id: int
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

    async def test_pressure_uses_the_same_shape_as_gas(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """앱이 채널 넷을 같은 코드로 그린다."""
        base = datetime(2020, 5, 1, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0, pressure_dev=2.5)

        payload = (
            await device.get(
                "telemetry/summary",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(days=1)).isoformat(),
                },
            )
        ).json()

        assert set(payload["pressure"]) == set(payload["gas"])
        assert payload["pressure"]["value"] == pytest.approx(2.5)


class TestLocation:
    async def test_returns_the_last_reported_coordinates(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0, location=Coordinates(37.5, 127.0))
        _store(
            session,
            device_id,
            base + timedelta(hours=1),
            seq=2,
            voc_dev=1.0,
            location=Coordinates(37.5573, 127.0329),
        )

        payload = (await device.get("location")).json()

        assert payload["lat"] == pytest.approx(37.5573)
        assert payload["lon"] == pytest.approx(127.0329)
        assert payload["at"] == (base + timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    async def test_frames_without_coordinates_are_skipped(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """좌표는 상태 전이 프레임에만 실린다. 최신 프레임이 아니라 최신 좌표를 준다."""
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0, location=Coordinates(37.5, 127.0))
        _store(session, device_id, base + timedelta(hours=1), seq=2, voc_dev=1.0)

        payload = (await device.get("location")).json()

        assert payload["lat"] == pytest.approx(37.5)

    async def test_device_without_any_coordinates_is_404(self, device: SeededDevice) -> None:
        response = await device.get("location")

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"


@pytest.fixture
def client_period(now: datetime) -> dict[str, str]:
    return {
        "from": (now - timedelta(days=1)).isoformat(),
        "to": now.isoformat(),
    }


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
    pressure_dev: float | None = None,
    location: Coordinates | None = None,
) -> None:
    values = {Measure.VOC_DEV: voc_dev}
    if pressure_dev is not None:
        values[Measure.PRESSURE_DEV] = pressure_dev
    SqlAlchemyReadingRepository(session).add_if_absent(
        a_reading(
            at,
            device_id=device_id,
            frame=a_frame(at, seq=seq, state=state, values=values, location=location),
        )
    )
    session.commit()
