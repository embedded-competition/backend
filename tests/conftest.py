"""공용 fixture. 하드웨어·실제 DB에 의존하지 않는다."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """테스트마다 임시 SQLite. 개발용 DB 파일을 건드리지 않는다."""
    return Settings(
        environment="local",
        database_path=tmp_path / "test.db",
        lora_source="fake",
        fcm_credentials_path=None,
    )


@pytest.fixture
def app(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    # lifespan이 get_settings()를 부르므로 캐시된 설정을 테스트용으로 바꾼다.
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    application = create_app(settings)
    yield application
    application.dependency_overrides.clear()  # 정리 누락은 다음 테스트를 오염시킨다


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    # lifespan을 직접 태워 app.state(session_factory 등)를 채운다.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture
def now() -> datetime:
    """고정 시각. 실제 시각에 의존하는 단정을 만들지 않는다."""
    return datetime(2026, 8, 8, 12, 0, 0, tzinfo=UTC)
