from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime

from alembic.runtime.migration import MigrationContext
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.api.exception_handlers import register_exception_handlers
from app.api.routes import alerts, devices, health, telemetry
from app.core.config import Settings, get_settings
from app.domain.ports.frame_source import RawFrame
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.runtime import wiring
from app.runtime.log_config import configure_logging
from app.runtime.lora import create_frame_source
from app.runtime.receiver import FrameReceiver
from app.runtime.state import STATE_ATTRIBUTE, ReceiverLiveness, RuntimeState

logger = logging.getLogger(__name__)

VERSION = "0.1.0"


def build_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """호출자가 준 설정으로 실행 자원을 연다.

    settings를 인자로 받는 이유 — 전역에서 다시 읽으면 create_app(settings)의
    주입이 시늉만 하게 된다. 만든 앱과 실제로 붙는 DB가 달라진다.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(
            settings.database_path, busy_timeout_ms=settings.sqlite_busy_timeout_ms
        )
        state = RuntimeState(
            session_factory=create_session_factory(engine),
            settings=settings,
            schema_revision=_schema_revision(engine),
            lora=ReceiverLiveness(enabled=settings.lora_enabled),
        )
        setattr(app.state, STATE_ATTRIBUTE, state)

        receiver: FrameReceiver | None = None
        if settings.lora_enabled:
            receiver = _build_receiver(state, settings)
            state.lora.task = asyncio.create_task(receiver.run(), name="lora-receiver")
            state.lora.task.add_done_callback(_log_receiver_death)

        logger.info(
            "app started",
            extra={
                "version": VERSION,
                "environment": settings.environment,
                "database": str(settings.database_path),
                "schema_revision": state.schema_revision,
                "lora_source": settings.lora_source,
                "push_delivery": settings.push_delivery,
            },
        )
        try:
            yield
        finally:
            await state.lora.stop()
            engine.dispose()
            logger.info(
                "app stopped",
                extra=receiver.stats.as_dict() if receiver is not None else {},
            )

    return lifespan


def _schema_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def _build_receiver(state: RuntimeState, settings: Settings) -> FrameReceiver:
    def remember_last_frame(_: RawFrame) -> None:
        state.lora.observe(datetime.now(UTC))

    return FrameReceiver(
        source=create_frame_source(settings),
        session_scope=wiring.session_scope_factory(state.session_factory),
        ingest_factory=wiring.build_ingest_service,
        notifier_factory=wiring.notifier_factory(settings, wiring.create_push_sender(settings)),
        on_frame=remember_last_frame,
    )


def _log_receiver_death(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    exception = task.exception()
    if exception is not None:
        logger.critical("lora receiver died", exc_info=exception)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="Orca Backend",
        description="전동 킥보드 배터리 화재 조기감지 — LoRa 수신 + 알람 디스패치",
        version=VERSION,
        lifespan=build_lifespan(settings),
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
    app.include_router(health.router)
    app.include_router(devices.router)
    app.include_router(telemetry.router)
    app.include_router(alerts.router)
    return app
