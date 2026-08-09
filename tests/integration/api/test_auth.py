"""deviceToken 인증. 실패 응답이 남의 기기 존재를 흘리지 않아야 한다."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.api.client import OTHER_MAC, RegisteredDevice, register

LATEST = "telemetry/latest"


class TestMissingOrBadToken:
    async def test_missing_header_is_unauthorized(
        self, client: AsyncClient, device: RegisteredDevice
    ) -> None:
        response = await client.get(f"/devices/{device.public_id}/{LATEST}")

        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    async def test_bad_token_is_unauthorized(
        self, client: AsyncClient, device: RegisteredDevice
    ) -> None:
        response = await client.get(
            f"/devices/{device.public_id}/{LATEST}",
            headers={"Authorization": "Bearer dtk_wrong"},
        )

        assert response.status_code == 401


class TestOwnership:
    async def test_other_device_id_is_not_found(
        self, client: AsyncClient, device: RegisteredDevice
    ) -> None:
        """다른 기기 id를 넣으면 404 — 403이면 그 기기의 존재가 새어나간다."""
        other = await register(client, OTHER_MAC)

        response = await client.get(f"/devices/{other.public_id}/{LATEST}", headers=device.headers)

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"


class TestErrorBody:
    async def test_carries_request_id(self, client: AsyncClient) -> None:
        response = await client.get(f"/devices/dev_nope/{LATEST}")

        assert response.json()["requestId"]
