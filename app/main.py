"""FastAPI 인스턴스 + lifespan + wiring. endpoint 정의는 여기 없다."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from app.api import wiring
from app.api.exception_handlers import register_exception_handlers
from app.api.routes import alerts, devices, health, telemetry
from app.core.config import Settings, get_settings
from app.domain.ports import RawFrame
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.infrastructure.lora.factory import create_frame_source
from app.infrastructure.lora.receiver import FrameReceiver

logger = logging.getLogger(__name__)

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """자원 수명 단일 관리 지점. 모듈 import 시점에 부작용을 만들지 않는다."""
    settings: Settings = get_settings()

    engine = create_db_engine(
        settings.database_path, busy_timeout_ms=settings.sqlite_busy_timeout_ms
    )
    session_factory = create_session_factory(engine)
    app.state.session_factory = session_factory
    app.state.settings = settings
    app.state.lora_last_frame_at = None
    app.state.alembic_revision = None

    receiver: FrameReceiver | None = None
    task: asyncio.Task[None] | None = None
    if settings.lora_enabled:
        receiver = _build_receiver(app, settings, session_factory)
        task = asyncio.create_task(receiver.run(), name="lora-receiver")
        # 지역 변수로만 두면 GC로 사라진다.
        app.state.lora_task = task
        app.state.lora_receiver = receiver
        task.add_done_callback(_log_receiver_death)
    app.state.lora_running = settings.lora_enabled

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
        app.state.lora_running = False
        if task is not None:
            task.cancel()
            # 취소된 task를 회수하지 않으면 종료가 매달린다.
            await asyncio.gather(task, return_exceptions=True)
        engine.dispose()
        logger.info(
            "app stopped",
            extra=receiver.stats.as_dict() if receiver is not None else {},
        )


def _build_receiver(
    app: FastAPI, settings: Settings, factory: sessionmaker[Session]
) -> FrameReceiver:
    def remember_last_frame(_: RawFrame) -> None:
        # 헬스체크가 "무선 두절"을 판단하는 근거.
        app.state.lora_last_frame_at = datetime.now(UTC)

    return FrameReceiver(
        source=create_frame_source(settings),
        session_scope=wiring.session_scope_factory(factory),
        ingest_factory=wiring.build_ingest_service,
        notifier_factory=wiring.notifier_factory(settings, wiring.create_push_sender(settings)),
        on_frame=remember_last_frame,
    )


def _log_receiver_death(task: asyncio.Task[None]) -> None:
    """수신 task가 조용히 죽으면 수신이 멈춘 걸 아무도 모른다."""
    if task.cancelled():
        return
    exception = task.exception()
    if exception is not None:
        logger.critical("lora receiver died", exc_info=exception)


def create_app(settings: Settings | None = None) -> FastAPI:
    """앱 팩토리. 테스트가 설정을 바꿔 다시 만들 수 있어야 한다."""
    settings = settings or get_settings()
    app = FastAPI(
        title="Orca Backend",
        description="전동 킥보드 배터리 화재 조기감지 — LoRa 수신 + 알람 디스패치",
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
    # 앱 계약에 버전 prefix가 없다 (api-contract-reconciliation.md A1)
    app.include_router(health.router)
    app.include_router(devices.router)
    app.include_router(telemetry.router)
    app.include_router(alerts.router)
    return app


app = create_app()
