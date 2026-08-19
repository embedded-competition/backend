from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.ingest_service import IngestOutcome, IngestService
from app.core.notification_service import NotificationService
from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.exceptions import DeviceInactive, FrameError
from app.domain.frames import TelemetryFrame
from app.domain.ports.frame_source import FrameSource, RawFrame
from app.infrastructure.lora.frame import parse_frame
from app.infrastructure.lora.stats import ReceiveStats

logger = logging.getLogger(__name__)

SessionScope = Callable[[], AbstractContextManager[Session]]
IngestFactory = Callable[[Session], IngestService]
NotifierFactory = Callable[[Session], NotificationService]
FrameParser = Callable[[RawFrame], TelemetryFrame]


def parse_wire_frame(raw: RawFrame) -> TelemetryFrame:
    return parse_frame(raw.payload, raw.received_at)


def _frame_fields(frame: TelemetryFrame, raw: RawFrame) -> dict[str, object]:
    """한 프레임을 되짚는 데 필요한 것만 — 무엇이, 어디서, 얼마나 세게 왔는가."""
    fields: dict[str, object] = {
        "hw_id": str(frame.hw_id),
        "rssi": raw.rssi,
        "snr": raw.snr,
        "bytes": len(raw.payload),
    }
    fields.update({measure.value: value for measure, value in frame.values.items()})
    return fields


@dataclass(slots=True, kw_only=True)
class FrameReceiver:
    source: FrameSource
    session_scope: SessionScope
    ingest_factory: IngestFactory
    notifier_factory: NotifierFactory
    parse: FrameParser = parse_wire_frame
    on_frame: Callable[[RawFrame], None] | None = None
    stats: ReceiveStats = field(default_factory=ReceiveStats)
    report_every: timedelta = timedelta(minutes=10)
    """수신 통계를 남기는 간격. 개수가 아니라 시간이다 — 이유는 ReceiveStats에 적었다."""
    silence_report_s: float = 60.0
    label: str = "lora"
    """로그에서 이 수신기를 가리키는 이름.

    수신기가 둘 이상 돌면 같은 문장이 두 번 나오고, 어느 쪽이 조용한지 구별할 수
    없다. 무선의 침묵과 시뮬레이터의 정지는 뜻이 전혀 다르다.
    """

    async def run(self) -> None:
        watchdog = asyncio.create_task(self._watch_silence(), name="lora-silence")
        try:
            async for raw in self.source.frames():
                self.stats.received += 1
                if self.on_frame is not None:
                    self.on_frame(raw)
                await self._handle(raw)
                if self.stats.should_report(raw.received_at, self.report_every):
                    logger.info("receive stats", extra=self._reported())
        except asyncio.CancelledError:
            logger.info("receiver cancelled", extra=self._reported())
            raise
        finally:
            watchdog.cancel()
            await asyncio.gather(watchdog, return_exceptions=True)
            await self.source.close()

    async def _watch_silence(self) -> None:
        """수신이 없으면 로그도 없다 — 조용한 것과 죽은 것이 구별되지 않는다.

        주파수·SF가 한쪽만 어긋나면 수신이 0이 되는데, 0은 에러가 아니라 침묵이라
        아무 흔적을 남기지 않는다. 살아 있다는 사실과 얼마나 조용한지를 직접 말한다.
        """
        seen = self.stats.received
        silent_ticks = 0
        while True:
            await asyncio.sleep(self.silence_report_s)
            if self.stats.received != seen:
                seen = self.stats.received
                silent_ticks = 0
                continue
            silent_ticks += 1
            logger.warning(
                "receiver silent",
                extra={
                    "silent_s": round(silent_ticks * self.silence_report_s),
                    **self._reported(),
                },
            )

    async def _handle(self, raw: RawFrame) -> None:
        try:
            outcome = self._store(raw)
        except FrameError as exc:
            self._count_frame_error(exc)
            logger.warning(
                "frame rejected",
                extra={"receiver": self.label, "code": exc.code, "payload": raw.payload.hex()},
            )
            return
        except DeviceInactive as exc:
            self.stats.unknown_device += 1
            logger.warning(
                "frame from inactive device",
                extra={"receiver": self.label, "code": exc.code},
            )
            return
        except Exception:
            logger.exception("frame handling failed")
            return

        if outcome is not None and outcome.needs_dispatch and outcome.alert is not None:
            await self._dispatch(outcome.alert, outcome.device)

    def _store(self, raw: RawFrame) -> IngestOutcome | None:
        frame = self.parse(raw)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("frame received", extra=_frame_fields(frame, raw))
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

    def _reported(self) -> dict[str, object]:
        return {"receiver": self.label, **self.stats.as_dict()}

    def _count_frame_error(self, exc: FrameError) -> None:
        if exc.code == "frame_crc_error":
            self.stats.crc_error += 1
        else:
            self.stats.parse_error += 1
