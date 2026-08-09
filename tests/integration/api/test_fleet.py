"""앱 spec §⑦ GET /devices/{id}/fleet-comparison — 동일 단지 비교."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.api.client import OTHER_MAC, RegisteredDevice, register


class TestFleetComparison:
    async def test_fleet_size_counts_registered_devices(
        self, client: AsyncClient, device: RegisteredDevice
    ) -> None:
        await register(client, OTHER_MAC)

        payload = (await device.get("fleet-comparison")).json()

        assert payload["fleetSize"] == 2
        assert payload["myLevel"] == "NORMAL"
