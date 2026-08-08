"""외부 시스템 port. 구현은 infrastructure에, 조립은 main/deps에서."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models import Alert, Device


class Clock(Protocol):
    """시간 주입. 도메인·서비스에서 datetime.now()를 직접 부르지 않는다."""

    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class RawFrame:
    """수신 어댑터가 넘기는 원시 프레임. 파싱 전 상태."""

    payload: bytes
    received_at: datetime
    rssi: int | None = None
    snr: float | None = None


class FrameSource(Protocol):
    """LoRa 수신 어댑터. 하드웨어 없는 환경에서는 fake 구현을 주입한다."""

    async def frames(self) -> AsyncIterator[RawFrame]: ...

    async def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PushResult:
    delivered: bool
    error_code: str | None = None
    permanent_failure: bool = False
    """True면 재시도하지 않고 토큰을 비활성화한다 (UNREGISTERED 등)."""


class PushSender(Protocol):
    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult: ...
