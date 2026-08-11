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
from app.domain.frames import TelemetryFrame
from app.domain.ports.frame_source import FrameSource, RawFrame
from app.infrastructure.lora.frame import parse_frame
from app.infrastructure.lora.stats import ReceiveStats

logger = logging.getLogger(__name__)

_REPORT_EVERY = 50

SessionScope = Callable[[], AbstractContextManager[Session]]
IngestFactory = Callable[[Session], IngestService]
NotifierFactory = Callable[[Session], NotificationService]
FrameParser = Callable[[RawFrame], TelemetryFrame]


def parse_wire_frame(raw: RawFrame) -> TelemetryFrame:
    return parse_frame(raw.payload)


@dataclass(slots=True, kw_only=True)
class FrameReceiver:
    source: FrameSource
    session_scope: SessionScope
    ingest_factory: IngestFactory
    notifier_factory: NotifierFactory
    parse: FrameParser = parse_wire_frame
    on_frame: Callable[[RawFrame], None] | None = None
    stats: ReceiveStats = field(default_factory=ReceiveStats)

    async def run(self) -> None:
        try:
            async for raw in self.source.frames():
                self.stats.received += 1
                if self.on_frame is not None:
                    self.on_frame(raw)
                await self._handle(raw)
                if self.stats.should_report(_REPORT_EVERY):
                    logger.info("lora receive stats", extra=self.stats.as_dict())
        except asyncio.CancelledError:
            logger.info("lora receiver cancelled", extra=self.stats.as_dict())
            raise
        finally:
            await self.source.close()

    async def _handle(self, raw: RawFrame) -> None:
        try:
            outcome = self._store(raw)
        except FrameError as exc:
            self._count_frame_error(exc)
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
            logger.exception("frame handling failed")
            return

        if outcome is not None and outcome.needs_dispatch and outcome.alert is not None:
            await self._dispatch(outcome.alert, outcome.device)

    def _store(self, raw: RawFrame) -> IngestOutcome | None:
        frame = self.parse(raw)
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
        try:
            with self.session_scope() as session:
                report = await self.notifier_factory(session).dispatch(alert, device)
            logger.info("alert dispatched", extra=report.as_dict())
        except Exception:
            logger.exception("alert dispatch failed")

    def _count_frame_error(self, exc: FrameError) -> None:
        if exc.code == "frame_crc_error":
            self.stats.crc_error += 1
        else:
            self.stats.parse_error += 1
