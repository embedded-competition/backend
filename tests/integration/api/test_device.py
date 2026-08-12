"""GET /v1/devices/{mac} — 설정 화면이 쓰는 기기 정보와 모듈 상태."""

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


class TestDeviceProfile:
    async def test_reports_identity_without_telemetry_values(self, device: SeededDevice) -> None:
        """측정값은 여기 없다 — 주기가 다른 것을 같이 담지 않는다."""
        payload = (await _profile(device)).json()

        assert set(payload) == {
            "mac",
            "label",
            "parkingSlot",
            "battery",
            "link",
            "sensorCheck",
            "lastSeenAt",
        }

    async def test_battery_is_null_until_the_node_sends_voltage(self, device: SeededDevice) -> None:
        assert (await _profile(device)).json()["battery"] is None

    async def test_never_heard_from_reports_unknown_link(self, device: SeededDevice) -> None:
        """끊긴 것과 아직 안 온 것은 다르다."""
        payload = (await _profile(device)).json()

        assert payload["link"] is None
        assert payload["sensorCheck"] is None

    async def test_strong_recent_frame_is_a_good_link(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        _observe(session, device_id, rssi=-42, silent_for=timedelta(minutes=1))

        payload = (await _profile(device)).json()

        assert payload["link"] == "GOOD"
        assert payload["sensorCheck"] == "OK"

    async def test_silence_beats_signal_strength(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        _observe(session, device_id, rssi=-30, silent_for=timedelta(days=1))

        assert (await _profile(device)).json()["link"] == "OFFLINE"

    async def test_saturated_sensor_needs_service(
        self, device: SeededDevice, session: Session, device_id: int
    ) -> None:
        _observe(
            session,
            device_id,
            rssi=-42,
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
    rssi: int,
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
            radio=RadioQuality(rssi=rssi, snr=9.0),
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
