"""푸시 발송 port. 제공자(Expo/FCM)는 어댑터가 안다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.alerting import Alert
from app.domain.device import Device


@dataclass(frozen=True, slots=True)
class PushResult:
    delivered: bool
    error_code: str | None = None
    permanent_failure: bool = False
    """True면 재시도하지 않고 토큰을 비활성화한다 (UNREGISTERED 등)."""


class PushSender(Protocol):
    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult: ...
