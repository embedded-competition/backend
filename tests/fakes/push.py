"""PushSender fake. Protocol 구현이라 시그니처가 바뀌면 타입 체크로 잡힌다."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.ports.push_sender import PushResult


@dataclass
class RecordingPushSender:
    results: list[PushResult] = field(default_factory=list)
    sent: list[tuple[str, str]] = field(default_factory=list)

    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult:
        self.sent.append((token, alert.to_state.value))
        if self.results:
            return self.results.pop(0)
        return PushResult(delivered=True)
