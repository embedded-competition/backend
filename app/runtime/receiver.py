"""LoRa 수신 루프.

lifespan에서 뜬 장수 asyncio task. 프레임 1건 실패가 루프를 죽이지 않는다.
저장은 IngestService, 발송은 NotificationService가 하고 이 모듈은 흐름만 잇는다.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.ingest_service import IngestOutcome, IngestService
from app.core.notification_service import NotificationService
from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.exceptions import DeviceInactive, DeviceNotRegistered, FrameError
from app.domain.ports.frame_source import FrameSource, RawFrame
from app.infrastructure.lora.frame import parse_frame
from app.infrastructure.lora.stats import ReceiveStats

logger = logging.getLogger(__name__)

_REPORT_EVERY = 50

SessionScope = Callable[[], AbstractContextManager[Session]]
IngestFactory = Callable[[Session], IngestService]
NotifierFactory = Callable[[Session], NotificationService]


@dataclass(slots=True, kw_only=True)
class FrameReceiver:
    source: FrameSource
    session_scope: SessionScope
    ingest_factory: IngestFactory
    notifier_factory: NotifierFactory
    on_frame: Callable[[RawFrame], None] | None = None
    stats: ReceiveStats = field(default_factory=ReceiveStats)

    async def run(self) -> None:
        """취소될 때까지 돈다. 예외로 조용히 멈추지 않는 게 이 루프의 계약이다."""
        try:
            async for raw in self.source.frames():
                self.stats.received += 1
                if self.on_frame is not None:
                    self.on_frame(raw)
                await self._handle(raw)
                if self.stats.should_report(_REPORT_EVERY):
                    logger.info("lora receive stats", extra=self.stats.as_dict())
        except asyncio.CancelledError:
            # 정리 후 재전파 — 삼키면 서비스가 안 내려간다.
            logger.info("lora receiver cancelled", extra=self.stats.as_dict())
            raise
        finally:
            await self.source.close()

    async def _handle(self, raw: RawFrame) -> None:
        try:
            outcome = self._store(raw)
        except FrameError as exc:
            self._count_frame_error(exc)
            # 무선 경로는 재현이 어렵다 — 원본 hex가 유일한 증거다.
            logger.warning(
                "frame rejected",
                extra={"code": exc.code, "payload": raw.payload.hex()},
            )
            return
        except (DeviceNotRegistered, DeviceInactive) as exc:
            self.stats.unknown_device += 1
            logger.warning("frame from unknown device", extra={"code": exc.code})
            return
        except Exception:
            # 한 프레임 실패가 수신을 멈추게 하지 않는다.
            logger.exception("frame handling failed")
            return

        if outcome is not None and outcome.needs_dispatch and outcome.alert is not None:
            await self._dispatch(outcome.alert, outcome.device)

    def _store(self, raw: RawFrame) -> IngestOutcome | None:
        frame = parse_frame(raw.payload)
        with self.session_scope() as session:
            outcome = self.ingest_factory(session).ingest(frame, raw)
        if outcome.duplicate:
            self.stats.duplicate += 1
            return None
        self.stats.stored += 1
        self.stats.missed_frames += outcome.missed_frames
        if outcome.alert is not None:
            self.stats.alerts += 1
        return outcome

    async def _dispatch(self, alert: Alert, device: Device) -> None:
        """저장 커밋 이후에만 호출된다 (롤백 시 유령 알림 방지).

        alert를 인자로 받는다 — outcome을 통째로 넘기면 "alert가 있다"를
        assert로 다시 주장해야 하고, assert는 `python -O`에서 사라진다.
        """
        try:
            with self.session_scope() as session:
                report = await self.notifier_factory(session).dispatch(alert, device)
            logger.info("alert dispatched", extra=report.__dict__)
        except Exception:
            # 발송 실패가 측정값 저장을 되돌리지 않는다.
            logger.exception("alert dispatch failed")

    def _count_frame_error(self, exc: FrameError) -> None:
        if exc.code == "frame_crc_error":
            self.stats.crc_error += 1
        else:
            self.stats.parse_error += 1
