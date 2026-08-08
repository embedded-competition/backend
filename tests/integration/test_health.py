"""헬스체크 통합 테스트. 임시 SQLite + ASGI transport."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_component_breakdown(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body["components"]) == {"process", "database", "lora_radio", "push"}
    assert body["version"] == "0.1.0"


async def test_database_component_is_ok(client: AsyncClient) -> None:
    body = (await client.get("/health")).json()

    assert body["components"]["database"]["status"] == "ok"


async def test_lora_disabled_when_receiver_not_running(client: AsyncClient) -> None:
    """수신 task 미가동은 disabled — 무선 두절(failed)과 구분한다."""
    body = (await client.get("/health")).json()

    assert body["components"]["lora_radio"]["status"] == "disabled"


async def test_push_disabled_without_credentials(client: AsyncClient) -> None:
    body = (await client.get("/health")).json()

    assert body["components"]["push"]["status"] == "disabled"


async def test_openapi_documents_health_endpoint(client: AsyncClient) -> None:
    """앱 팀이 읽는 계약. summary·tags 누락은 여기서 잡는다."""
    spec = (await client.get("/openapi.json")).json()

    operation = spec["paths"]["/health"]["get"]
    assert operation["summary"]
    assert operation["tags"] == ["health"]
