"""앱 spec §④ 텔레메트리 폴링. 응답 키는 앱과의 계약이라 회귀가 치명적이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading
from tests.integration.api.client import UNKNOWN_MAC, SeededDevice


class TestMacAddressing:
    async def test_separators_do_not_matter(self, device: SeededDevice) -> None:
        """앱이 라벨을 어떻게 읽어 오든 같은 기기를 가리켜야 한다."""
        bare = await device.client.get("/v1/devices/aabbccddeeff/telemetry/current")

        assert bare.status_code == 200

    async def test_unknown_mac_is_404(self, device: SeededDevice) -> None:
        response = await device.client.get(f"/v1/devices/{UNKNOWN_MAC}/telemetry/current")

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"

    async def test_malformed_mac_is_422(self, device: SeededDevice) -> None:
        response = await device.client.get("/v1/devices/not-a-mac-addr/telemetry/current")

        assert response.status_code == 422


class TestCurrent:
    async def test_reports_the_latest_reading(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """구간 개념이 없다 — 언제 물어도 가장 최근 관측이다."""
        now = datetime.now(UTC)
        _store(session, device_id, now - timedelta(minutes=5), seq=1, voc_dev=9.0)
        _store(session, device_id, now - timedelta(minutes=1), seq=2, voc_dev=2.0)

        payload = (await device.get("telemetry/current")).json()

        assert payload["gas"]["value"] == pytest.approx(2.0)
        assert "from" not in payload
        assert "to" not in payload

    async def test_no_reading_reports_no_status(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """기기가 한 번도 보고하지 않았으면 last_state가 뭐든 지금은 null이다."""
        _set_last_state(session, device_id, AlertState.ALARM)

        payload = (await device.get("telemetry/current")).json()

        assert payload["status"] is None
        assert payload["conditions"] == []
        assert payload["gas"] is None
        assert payload["at"] is None

    async def test_pressure_uses_the_same_shape_as_gas(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """앱이 채널 넷을 같은 코드로 그린다."""
        now = datetime.now(UTC)
        _store(session, device_id, now, seq=1, voc_dev=1.0, pressure_dev=2.5)

        payload = (await device.get("telemetry/current")).json()

        assert set(payload["pressure"]) == set(payload["gas"])
        assert payload["pressure"]["value"] == pytest.approx(2.5)

    async def test_reports_conditions_and_status(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        now = datetime.now(UTC)
        _store(
            session,
            device_id,
            now,
            seq=1,
            voc_dev=1.0,
            state=AlertState.WATCH,
            conditions=frozenset({Condition.CO_RISE, Condition.WATER}),
        )

        payload = (await device.get("telemetry/current")).json()

        assert payload["status"] == "STABLE"
        assert set(payload["conditions"]) == {"CO_RISE", "WATER"}
        assert payload["stage"] == "GAS_LEAK"

    async def test_watch_is_stable_because_the_gauge_has_no_slot_for_it(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """게이지는 안정·정비요망·신고 세 지점뿐이다. 무엇을 지켜보는지는 stage가 답한다."""
        _store(
            session,
            device_id,
            datetime.now(UTC),
            seq=1,
            state=AlertState.FAULT,
            conditions=frozenset({Condition.SENSOR_FAULT}),
        )

        payload = (await device.get("telemetry/current")).json()

        assert payload["status"] == "SERVICE_NEEDED"
        assert payload["stage"] == "NONE"

    async def test_alarm_asks_the_user_to_report(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        _store(session, device_id, datetime.now(UTC), seq=1, state=AlertState.ALARM)

        assert (await device.get("telemetry/current")).json()["status"] == "REPORT"

    async def test_warmup_has_nothing_to_tell_the_user_yet(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """예열 중에 '안정'이라 답하면 감지가 시작되지도 않았는데 괜찮다고 말하는 것이다."""
        _store(session, device_id, datetime.now(UTC), seq=1, state=AlertState.WARMUP)

        assert (await device.get("telemetry/current")).json()["status"] is None

    async def test_stage_is_null_when_no_rule_can_decide_it(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """모르는 것을 '이상 없음'으로 접으면 거짓말이 된다."""
        _store(
            session,
            device_id,
            datetime.now(UTC),
            seq=1,
            state=AlertState.WATCH,
            conditions=frozenset({Condition.PRESSURE_RISE}),
        )

        assert (await device.get("telemetry/current")).json()["stage"] is None

    async def test_temperature_and_humidity_are_not_exposed(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """화면에 없다. 습도는 게이트 판정의 입력이지 표시값이 아니다."""
        _store(session, device_id, datetime.now(UTC), seq=1, temp_c=26.1, humidity_pct=43.4)

        payload = (await device.get("telemetry/current")).json()

        assert "tempC" not in payload
        assert "rh" not in payload
        assert "managementPhone" not in payload


class TestPeaks:
    async def test_reports_peaks_over_the_period(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """값은 기간 중 최고치이고, 채널의 at은 그 최고를 찍은 시각이다."""
        base = datetime(2020, 5, 1, tzinfo=UTC)
        peak_at = base + timedelta(hours=2)
        _store(session, device_id, base, seq=1, voc_dev=1.0)
        _store(session, device_id, peak_at, seq=2, voc_dev=8.1, state=AlertState.WATCH)

        payload = (
            await device.get(
                "telemetry/peaks",
                params={"from": base.isoformat(), "to": (base + timedelta(days=1)).isoformat()},
            )
        ).json()

        assert payload["status"] == "STABLE"
        assert payload["gas"]["value"] == pytest.approx(8.1)
        assert payload["gas"]["at"] == peak_at.isoformat().replace("+00:00", "Z")
        assert payload["co"] is None

    async def test_from_and_to_are_not_echoed(self, device: SeededDevice, now: datetime) -> None:
        """서버가 손대지 않는 값이라 클라가 이미 안다."""
        payload = (
            await device.get(
                "telemetry/peaks",
                params={
                    "from": (now - timedelta(days=1)).isoformat(),
                    "to": now.isoformat(),
                },
            )
        ).json()

        assert "from" not in payload
        assert "to" not in payload
        assert "at" not in payload
        assert "managementPhone" not in payload

    async def test_no_observations_reports_no_status(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        """관측이 없는 구간은 null이다 — 기기의 지금 상태를 과거 구간에 흘려보내지 않는다."""
        _set_last_state(session, device_id, AlertState.ALARM)

        payload = (
            await device.get(
                "telemetry/peaks",
                params={
                    "from": (now - timedelta(days=2)).isoformat(),
                    "to": (now - timedelta(days=1)).isoformat(),
                },
            )
        ).json()

        assert payload["status"] is None
        assert payload["conditions"] == []
        assert payload["gas"] is None

    async def test_observed_period_reports_worst_state(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2020, 5, 1, tzinfo=UTC)
        peak_at = base + timedelta(hours=1)
        _store(session, device_id, base, seq=1, voc_dev=1.0)
        _store(session, device_id, peak_at, seq=2, voc_dev=8.1, state=AlertState.WATCH)

        payload = (
            await device.get(
                "telemetry/peaks",
                params={"from": base.isoformat(), "to": (base + timedelta(days=1)).isoformat()},
            )
        ).json()

        assert payload["status"] == "STABLE"

    async def test_conditions_are_the_union_over_the_period(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2020, 5, 1, tzinfo=UTC)
        _store(
            session,
            device_id,
            base,
            seq=1,
            voc_dev=1.0,
            conditions=frozenset({Condition.CO_RISE}),
        )
        _store(
            session,
            device_id,
            base + timedelta(hours=1),
            seq=2,
            voc_dev=1.0,
            conditions=frozenset({Condition.WATER}),
        )

        payload = (
            await device.get(
                "telemetry/peaks",
                params={"from": base.isoformat(), "to": (base + timedelta(days=1)).isoformat()},
            )
        ).json()

        assert set(payload["conditions"]) == {"CO_RISE", "WATER"}

    async def test_pressure_uses_the_same_shape_as_gas(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2020, 5, 1, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0, pressure_dev=2.5)

        payload = (
            await device.get(
                "telemetry/peaks",
                params={"from": base.isoformat(), "to": (base + timedelta(days=1)).isoformat()},
            )
        ).json()

        assert set(payload["pressure"]) == set(payload["gas"])
        assert payload["pressure"]["value"] == pytest.approx(2.5)


class TestSensorDetail:
    async def test_buckets_by_requested_interval(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base + timedelta(hours=1), seq=1, voc_dev=1.0)
        _store(session, device_id, base + timedelta(hours=3), seq=2, voc_dev=8.0)

        payload = (
            await device.get(
                "sensors/gas/detail",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=4)).isoformat(),
                    "interval": "2h",
                },
            )
        ).json()

        assert [b["start"] for b in payload["buckets"]] == [
            base.isoformat().replace("+00:00", "Z"),
            (base + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        ]
        assert payload["buckets"][1]["value"] == pytest.approx(8.0)

    async def test_single_channel_only(self, device: SeededDevice, now: datetime) -> None:
        """buckets 칸에는 요청한 센서 하나의 값·기울기만 있다."""
        response = await device.get(
            "sensors/gas/detail",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(hours=1)).isoformat(),
                "interval": "5m",
            },
        )

        assert response.status_code == 200
        assert set(response.json()) == {"buckets"}

    async def test_bucket_has_no_state_or_samples(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """단일 채널에 전체 상태를 붙이면 축이 안 맞는다."""
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0, state=AlertState.ALARM)

        payload = (
            await device.get(
                "sensors/gas/detail",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=1)).isoformat(),
                    "interval": "1h",
                },
            )
        ).json()

        bucket = payload["buckets"][0]
        assert set(bucket) == {"start", "level", "value", "slope"}

    async def test_temperature_has_no_slope(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        base = datetime(2026, 8, 4, tzinfo=UTC)
        _store(session, device_id, base, seq=1, voc_dev=1.0)
        SqlAlchemyReadingRepository(session).add_if_absent(
            a_reading(
                base,
                device_id=device_id,
                frame=a_frame(base, seq=99, values={Measure.TEMP_C: 26.1}),
            )
        )
        session.commit()

        payload = (
            await device.get(
                "sensors/temp/detail",
                params={
                    "from": base.isoformat(),
                    "to": (base + timedelta(hours=1)).isoformat(),
                    "interval": "1h",
                },
            )
        ).json()

        assert payload["buckets"][0]["slope"] is None

    async def test_unknown_sensor_is_422(self, device: SeededDevice, now: datetime) -> None:
        response = await device.get(
            "sensors/nope/detail",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(hours=1)).isoformat(),
                "interval": "1h",
            },
        )

        assert response.status_code == 422

    async def test_unknown_interval_is_422(self, device: SeededDevice, now: datetime) -> None:
        response = await device.get(
            "sensors/gas/detail",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(hours=1)).isoformat(),
                "interval": "120m",
            },
        )

        assert response.status_code == 422

    async def test_interval_is_not_echoed(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        _store(session, device_id, now, seq=1, voc_dev=1.0)

        payload = (
            await device.get(
                "sensors/gas/detail",
                params={
                    "from": now.isoformat(),
                    "to": (now + timedelta(hours=1)).isoformat(),
                    "interval": "5m",
                },
            )
        ).json()

        assert "interval" not in payload

    async def test_too_many_buckets_is_rejected(self, device: SeededDevice, now: datetime) -> None:
        response = await device.get(
            "sensors/gas/detail",
            params={
                "from": now.isoformat(),
                "to": (now + timedelta(days=10)).isoformat(),
                "interval": "5m",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_interval"


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
        """기기가 없는 것과 좌표를 아직 못 받은 것은 다른 사건이다."""
        response = await device.get("location")

        assert response.status_code == 404
        assert response.json()["error"] == "location_unavailable"


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
    voc_dev: float = 1.0,
    state: AlertState = AlertState.NORMAL,
    conditions: frozenset[Condition] = frozenset(),
    pressure_dev: float | None = None,
    temp_c: float | None = None,
    humidity_pct: float | None = None,
    location: Coordinates | None = None,
) -> None:
    values = {Measure.VOC_DEV: voc_dev}
    if pressure_dev is not None:
        values[Measure.PRESSURE_DEV] = pressure_dev
    if temp_c is not None:
        values[Measure.TEMP_C] = temp_c
    if humidity_pct is not None:
        values[Measure.HUMIDITY_PCT] = humidity_pct
    SqlAlchemyReadingRepository(session).add_if_absent(
        a_reading(
            at,
            device_id=device_id,
            frame=a_frame(
                at, seq=seq, state=state, conditions=conditions, values=values, location=location
            ),
        )
    )
    session.commit()
