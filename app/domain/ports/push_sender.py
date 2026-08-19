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


class PushSender(Protocol):
    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult: ...
