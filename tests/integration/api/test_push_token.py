"""앱 spec §③ POST /devices/{id}/push-token."""

from __future__ import annotations

from tests.integration.api.client import RegisteredDevice

PAYLOAD = {"token": "ExponentPushToken[abc123]"}


class TestRegisterPushToken:
    async def test_returns_registered(self, device: RegisteredDevice) -> None:
        response = await device.post("push-token", json=PAYLOAD)

        assert response.status_code == 200
        assert response.json() == {"registered": True}

    async def test_reregistration_is_idempotent(self, device: RegisteredDevice) -> None:
        """앱은 재실행마다 토큰을 보낸다 — 중복 행이 생기면 푸시가 중복된다."""
        first = await device.post("push-token", json=PAYLOAD)
        second = await device.post("push-token", json=PAYLOAD)

        assert first.status_code == second.status_code == 200
