"""헬스체크 통합 테스트. 임시 SQLite + ASGI transport."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import Settings

# 파일 읽기는 import 시점에 끝낸다 — async 테스트 안에서 블로킹 I/O를 하지 않는다.
_PROBED_PATHS = re.findall(
    r"curl [^\n]*localhost:\d+(/\S*)", Path("deploy/deploy.sh").read_text("utf-8")
)


async def test_health_returns_component_breakdown(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body["components"]) == {"process", "database", "lora_radio", "push"}


async def test_version_says_dev_when_no_release_was_injected(client: AsyncClient) -> None:
    """주입이 없으면 태그를 지어내지 않는다. 테스트는 배포본이 아니다."""
    body = (await client.get("/health")).json()

    assert body["version"] == "dev"


def test_release_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """deploy.sh가 data/release.env에 쓰고 systemd가 환경변수로 넘긴다."""
    monkeypatch.setenv("APP_RELEASE", "v0.6.0")

    assert Settings(_env_file=None).release == "v0.6.0"


async def test_database_component_is_ok(client: AsyncClient) -> None:
    body = (await client.get("/health")).json()

    assert body["components"]["database"]["status"] == "ok"


async def test_lora_disabled_when_receiver_not_running(client: AsyncClient) -> None:
    """수신 task 미가동은 disabled — 무선 두절(failed)과 구분한다."""
    body = (await client.get("/health")).json()

    assert body["components"]["lora_radio"]["status"] == "disabled"
    assert "미가동" in body["components"]["lora_radio"]["detail"]


async def test_push_disabled_when_delivery_is_log_only(client: AsyncClient) -> None:
    body = (await client.get("/health")).json()

    assert body["components"]["push"]["status"] == "disabled"


async def test_schema_revision_is_reported(client: AsyncClient) -> None:
    """배포된 코드와 DB 스키마가 어긋났는지 대조할 유일한 값이다."""
    body = (await client.get("/health")).json()

    assert body["revision"]


async def test_deploy_script_probes_a_path_that_exists(client: AsyncClient) -> None:
    """배포 스크립트가 없는 경로를 치면 정상 기동도 '헬스체크 실패'로 끝난다."""
    assert _PROBED_PATHS, "배포 스크립트에 헬스체크 curl이 없다"
    spec = (await client.get("/openapi.json")).json()
    assert set(_PROBED_PATHS) <= set(spec["paths"])


async def test_openapi_documents_health_endpoint(client: AsyncClient) -> None:
    """앱 팀이 읽는 계약. summary·tags 누락은 여기서 잡는다."""
    spec = (await client.get("/openapi.json")).json()

    operation = spec["paths"]["/health"]["get"]
    assert operation["summary"]
    assert operation["tags"] == ["health"]
