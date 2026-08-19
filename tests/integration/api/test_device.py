"""GET /v1/devices/{mac} — 설정 화면이 쓰는 센서 점검 결과."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import Response
from sqlalchemy.orm import Session

from app.domain.readings import RadioQuality, Reading
from app.domain.value_objects import AlertState, Condition
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame
from tests.integration.api.client import UNKNOWN_MAC, SeededDevice


class TestSensorCheck:
    async def test_carries_the_verdict_only(self, device: SeededDevice) -> None:
        payload = (await _profile(device)).json()

        assert set(payload) == {"sensorCheck"}

    async def test_no_observation_is_unknown(self, device: SeededDevice) -> None:
        """점검한 적 없는 것과 이상 없는 것은 다르다."""
        assert (await _profile(device)).json()["sensorCheck"] is None

    async def test_rising_values_do_not_blame_the_sensor(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        """값이 오르는 것은 센서가 멀쩡하다는 뜻이다."""
        _observe(
            session,
            device_id,
            silent_for=timedelta(minutes=1),
            conditions=frozenset({Condition.CO_RISE, Condition.WATER}),
            state=AlertState.WATCH,
        )

        assert (await _profile(device)).json()["sensorCheck"] == "OK"

    async def test_saturated_sensor_needs_service(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        _observe(
            session,
            device_id,
            silent_for=timedelta(minutes=1),
            conditions=frozenset({Condition.SENSOR_FAULT}),
            state=AlertState.FAULT,
        )

        assert (await _profile(device)).json()["sensorCheck"] == "FAULT"

    async def test_unknown_mac_is_404(self, device: SeededDevice) -> None:
        response = await device.client.get(f"/v1/devices/{UNKNOWN_MAC}")

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"


def _observe(
    session: Session,
    device_id: int,
    *,
    silent_for: timedelta,
    conditions: frozenset[Condition] = frozenset(),
    state: AlertState = AlertState.NORMAL,
) -> None:
    at = datetime.now(UTC) - silent_for
    SqlAlchemyReadingRepository(session).add_if_absent(
        Reading(
            device_id=device_id,
            frame=a_frame(at, seq=1, state=state, conditions=conditions),
            received_at=at,
            radio=RadioQuality(rssi=-42, snr=9.0),
        )
    )
    devices = SqlAlchemyDeviceRepository(session)
    stored = devices.get(device_id)
    assert stored is not None
    stored.last_seen_at = at
    devices.save(stored)
    session.commit()


async def _profile(device: SeededDevice) -> Response:
    """라우터 경로가 /v1/devices/{mac}이라 SeededDevice.get의 하위 경로 규칙과 다르다."""
    return await device.client.get(f"/v1/devices/{device.mac}")
