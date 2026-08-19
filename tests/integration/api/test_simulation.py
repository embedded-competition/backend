"""시뮬레이터 제어 API — 스케줄러 하나로 임베디드 없이 화면을 만든다."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient

MAC = "00:00:00:00:00:01"
OTHER_MAC = "00:00:00:00:00:02"
UNKNOWN_MAC = "AA:BB:CC:DD:EE:FF"

_NODE_COUNT = 5


def _channel(node: dict[str, Any], name: str) -> dict[str, Any]:
    return next(channel for channel in node["channels"] if channel["channel"] == name)


async def _flow(client: AsyncClient, mac: str, channel: str, **command: Any) -> dict[str, Any]:
    response = await client.post(
        f"/v1/simulation/devices/{mac}/channels/{channel}/flow", json=command
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


async def _await_first_tick(client: AsyncClient, mac: str) -> dict[str, Any]:
    """첫 틱이 기기를 만들 때까지 기다린다 — 수신 task는 요청과 별개로 돈다."""
    for _ in range(100):
        response = await client.get(f"/v1/devices/{mac}/telemetry/current")
        if response.status_code == 200:
            return dict(response.json())
        await asyncio.sleep(0.02)
    raise AssertionError(f"첫 틱이 {mac} 기기를 만들지 않았다")


class TestSimulatorState:
    async def test_lists_every_node_at_baseline(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/simulation")).json()

        assert body["running"] is True
        assert body["tickSeconds"] > 0
        assert [node["mac"] for node in body["nodes"]][:2] == [MAC, OTHER_MAC]
        assert len(body["nodes"]) == _NODE_COUNT
        assert all(node["state"] == "NORMAL" for node in body["nodes"])

    async def test_publishes_the_levels_that_change_the_screen(self, client: AsyncClient) -> None:
        """어디까지 올려야 하는지 모르면 흐름을 조절할 수 없다."""
        body = (await client.get("/v1/simulation")).json()
        gas = _channel(body["nodes"][0], "co")
        water = _channel(body["nodes"][0], "water")

        assert (gas["watchAt"], gas["alarmAt"]) == (400.0, 750.0)
        assert water["alarmAt"] is None
        assert body["saturatedAt"] == 1000.0

    async def test_tuning_leaves_untouched_fields_alone(self, client: AsyncClient) -> None:
        before = (await client.get("/v1/simulation")).json()["tickSeconds"]

        body = (await client.patch("/v1/simulation", json={"running": False})).json()

        assert body["running"] is False
        assert body["tickSeconds"] == before


class TestSteering:
    async def test_immediate_rise_moves_the_level_now(self, client: AsyncClient) -> None:
        node = await _flow(client, MAC, "co", direction="rise", amount=400, overSeconds=0)

        assert _channel(node, "co")["level"] == 480.0
        assert node["state"] == "WATCH"
        assert node["conditions"] == ["CO_RISE"]

    async def test_timed_rise_reports_target_and_time_left(self, client: AsyncClient) -> None:
        node = await _flow(client, MAC, "voc", direction="rise", amount=400, overSeconds=30)
        voc = _channel(node, "voc")

        assert voc["level"] == 120.0
        assert voc["target"] == 520.0
        assert voc["secondsLeft"] == pytest.approx(30.0, abs=0.5)

    async def test_fall_steers_the_other_way(self, client: AsyncClient) -> None:
        await _flow(client, MAC, "co", direction="rise", amount=400, overSeconds=0)

        node = await _flow(client, MAC, "co", direction="fall", amount=400, overSeconds=0)

        assert _channel(node, "co")["level"] == 80.0

    async def test_steering_one_node_leaves_the_others_alone(self, client: AsyncClient) -> None:
        await _flow(client, MAC, "co", direction="rise", amount=400, overSeconds=0)

        body = (await client.get("/v1/simulation")).json()
        other = next(node for node in body["nodes"] if node["mac"] == OTHER_MAC)

        assert other["state"] == "NORMAL"

    async def test_reset_returns_the_node_to_baseline(self, client: AsyncClient) -> None:
        await _flow(client, MAC, "h2", direction="rise", amount=900, overSeconds=0)

        node = (await client.post(f"/v1/simulation/devices/{MAC}/reset")).json()

        assert node["state"] == "NORMAL"
        assert node["latched"] is False
        assert _channel(node, "h2")["level"] == 90.0

    async def test_unknown_mac_is_not_found(self, client: AsyncClient) -> None:
        response = await client.post(f"/v1/simulation/devices/{UNKNOWN_MAC}/reset")

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"

    async def test_amount_outside_the_scale_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            f"/v1/simulation/devices/{MAC}/channels/co/flow",
            json={"direction": "rise", "amount": 0, "overSeconds": 5},
        )

        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"


class TestTickReachesTheApp:
    async def test_first_tick_registers_the_device_and_stores_a_reading(
        self, client: AsyncClient
    ) -> None:
        current = await _await_first_tick(client, MAC)

        assert current["status"] == "STABLE"
        assert current["co"]["value"] == 80.0

    async def test_next_tick_carries_the_steered_verdict(self, client: AsyncClient) -> None:
        await _await_first_tick(client, MAC)
        await _flow(client, MAC, "h2", direction="rise", amount=800, overSeconds=0)
        await client.patch("/v1/simulation", json={"tickSeconds": 0.2})

        for _ in range(100):
            current = (await client.get(f"/v1/devices/{MAC}/telemetry/current")).json()
            if current["status"] == "REPORT":
                break
            await asyncio.sleep(0.05)

        assert current["status"] == "REPORT"
        assert current["conditions"] == ["H2_RISE"]
        assert current["latched"] is True
