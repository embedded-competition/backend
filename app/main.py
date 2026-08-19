from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from alembic.runtime.migration import MigrationContext
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.api.exception_handlers import register_exception_handlers
from app.api.routes import alerts, devices, health, telemetry
from app.core.config import Settings, get_settings
from app.domain.ports.frame_source import FrameSource, RawFrame
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.runtime import wiring
from app.runtime.log_config import configure_logging
from app.runtime.lora import create_frame_parser, create_frame_source
from app.runtime.receiver import FrameParser, FrameReceiver
from app.runtime.state import STATE_ATTRIBUTE, ReceiverLiveness, RuntimeState
from app.simulation import NodeSimulator, decode_simulated_payload
from app.simulation.routes import STATE_ATTRIBUTE as SIMULATOR_ATTRIBUTE
from app.simulation.routes import router as simulation_router

logger = logging.getLogger(__name__)

API_VERSION = "0.1.0"
"""OpenAPI 문서에 실리는 스펙 버전. 배포마다 바뀌면 안 된다 — 바뀌면 매 배포가
docs/openapi.json 드리프트가 된다. 지금 돌고 있는 배포를 알고 싶으면
/health의 version(= Settings.release)을 본다."""


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
            lora=ReceiverLiveness(label="lora", enabled=settings.radio_enabled),
        )
        setattr(app.state, STATE_ATTRIBUTE, state)

        simulator = NodeSimulator.always_on()
        setattr(app.state, SIMULATOR_ATTRIBUTE, simulator)
        simulation = _simulation_receiver(state, settings, simulator)
        _start(state.simulation, simulation.run(), name="simulation-receiver")

        radio: FrameReceiver | None = None
        if settings.radio_enabled:
            radio = _radio_receiver(state, settings)
            _start(state.lora, radio.run(), name="lora-receiver")

        logger.info(
            "app started",
            extra={
                "release": settings.release,
                "environment": settings.environment,
                "database": str(settings.database_path),
                "schema_revision": state.schema_revision,
                "lora_source": settings.lora_source,
                "radio_enabled": settings.radio_enabled,
                "push_delivery": settings.push_delivery,
            },
        )
        try:
            yield
        finally:
            await state.simulation.stop()
            await state.lora.stop()
            engine.dispose()
            logger.info(
                "app stopped",
                extra={
                    "simulation": simulation.stats.as_dict(),
                    "radio": radio.stats.as_dict() if radio is not None else {},
                },
            )

    return lifespan


def _schema_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def _start(liveness: ReceiverLiveness, run: Coroutine[Any, Any, None], *, name: str) -> None:
    liveness.task = asyncio.create_task(run, name=name)
    liveness.task.add_done_callback(_log_receiver_death)


def _radio_receiver(state: RuntimeState, settings: Settings) -> FrameReceiver:
    """실기 노드를 듣는 수신기. 마지막 수신 시각이 /health의 라디오 상태가 된다."""
    return _receiver(
        state,
        settings,
        liveness=state.lora,
        source=create_frame_source(settings),
        parse=create_frame_parser(settings),
    )


def _simulation_receiver(
    state: RuntimeState, settings: Settings, simulator: NodeSimulator
) -> FrameReceiver:
    """시뮬레이터를 듣는 수신기. 생존을 따로 센다 — 시뮬레이터의 틱으로 무선 침묵을
    덮으면 /health가 죽은 라디오를 살아 있다고 답한다."""
    return _receiver(
        state,
        settings,
        liveness=state.simulation,
        source=simulator,
        parse=lambda raw: decode_simulated_payload(raw.payload, raw.received_at),
    )


def _receiver(
    state: RuntimeState,
    settings: Settings,
    *,
    liveness: ReceiverLiveness,
    source: FrameSource,
    parse: FrameParser,
) -> FrameReceiver:
    def remember_last_frame(_: RawFrame) -> None:
        liveness.observe(datetime.now(UTC))

    return FrameReceiver(
        source=source,
        session_scope=wiring.session_scope_factory(state.session_factory),
        ingest_factory=wiring.ingest_factory(settings),
        notifier_factory=wiring.notifier_factory(settings, wiring.create_push_sender(settings)),
        parse=parse,
        on_frame=remember_last_frame,
        label=liveness.label,
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
        version=API_VERSION,
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
    app.include_router(devices.router, prefix="/v1")
    app.include_router(telemetry.router, prefix="/v1")
    app.include_router(alerts.router, prefix="/v1")
    app.include_router(simulation_router, prefix="/v1")
    return app
