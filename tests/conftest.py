"""공용 fixture. 하드웨어·실제 DB에 의존하지 않는다."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """테스트마다 임시 SQLite. 개발용 DB 파일을 건드리지 않는다."""
    return Settings(
        environment="local",
        database_path=tmp_path / "test.db",
        lora_enabled=False,
        lora_source="none",
        push_delivery="log",
        management_phone="01029015899",
    )


@pytest.fixture
def migrated_db(settings: Settings) -> None:
    """스키마를 Alembic으로 만든다.

    create_all()을 쓰지 않는 이유 — 리비전이 깨졌는지도 같이 검증하기 위해서다.
    app·session 양쪽이 이 fixture에 의존해야 어느 쪽을 먼저 잡아도 테이블이 있다.
    """
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_config, "head")


@pytest.fixture
def app(settings: Settings, migrated_db: None) -> Iterator[FastAPI]:
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


@pytest.fixture
def session_factory(settings: Settings, migrated_db: None) -> Iterator[sessionmaker[Session]]:
    """백그라운드 task용 — 요청 스코프와 달리 프레임마다 세션을 연다."""
    engine = create_db_engine(settings.database_path)
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture
def session(settings: Settings, migrated_db: None) -> Iterator[Session]:
    """테스트가 직접 쓰는 세션. 앱이 쓰는 세션과 같은 DB 파일을 본다."""
    engine = create_db_engine(settings.database_path)
    factory = create_session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        engine.dispose()
