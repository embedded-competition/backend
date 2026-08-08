"""FastAPI 인스턴스 + lifespan + wiring. endpoint 정의는 여기 없다."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.v1 import health
from app.core.config import Settings, get_settings
from app.infrastructure.db.session import create_db_engine, create_session_factory

logger = logging.getLogger(__name__)

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """자원 수명 단일 관리 지점. 모듈 import 시점에 부작용을 만들지 않는다."""
    settings: Settings = get_settings()

    # 조립(wiring)은 여기서만. infrastructure에 Settings를 넘기지 않는다.
    engine = create_db_engine(
        settings.database_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    app.state.session_factory = create_session_factory(engine)
    app.state.settings = settings
    # LoRa 수신 task는 다음 단계에서 붙인다. 상태 키는 헬스체크가 먼저 참조한다.
    app.state.lora_running = False
    app.state.lora_last_frame_at = None
    app.state.alembic_revision = None

    logger.info(
        "app started",
        extra={
            "version": VERSION,
            "environment": settings.environment,
            "database": str(settings.database_path),
            "lora_source": settings.lora_source,
        },
    )
    try:
        yield
    finally:
        engine.dispose()
        logger.info("app stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """앱 팩토리. 테스트가 설정을 바꿔 다시 만들 수 있어야 한다."""
    settings = settings or get_settings()
    app = FastAPI(
        title="Orca Backend",
        description="EV 배터리 화재 조기감지 — LoRa 수신 + 알람 디스패치",
        version=VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_allow_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(health.router, prefix="/api/v1")
    return app


app = create_app()
