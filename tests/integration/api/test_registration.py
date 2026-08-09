"""앱 spec §② POST /devices — 기기 등록."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.api.client import MAC, register


class TestRegister:
    async def test_returns_id_and_token(self, client: AsyncClient) -> None:
        device = await register(client)

        assert device.public_id.startswith("dev_")
        assert device.token.startswith("dtk_")


class TestDuplicate:
    async def test_duplicate_mac_is_rejected(self, client: AsyncClient) -> None:
        await register(client)

        response = await client.post("/devices", json={"mac": MAC})

        assert response.status_code == 409
        assert response.json()["error"] == "already_paired"

    async def test_mac_is_normalized_before_duplicate_check(self, client: AsyncClient) -> None:
        """구분자·대소문자가 달라도 같은 기기다."""
        await register(client)

        response = await client.post("/devices", json={"mac": "aa-bb-cc-dd-ee-ff"})

        assert response.status_code == 409


class TestValidation:
    async def test_malformed_mac_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post("/devices", json={"mac": "not-a-mac-at-all"})

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_mac"
