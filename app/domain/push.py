from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PushToken:
    device_id: int
    token: str
    registered_at: datetime
    platform: str | None = None
    last_used_at: datetime | None = None
    is_active: bool = True
    deactivated_reason: str | None = None
    id: int | None = None

    def deactivate(self, reason: str) -> None:
        self.is_active = False
        self.deactivated_reason = reason


@dataclass(slots=True)
class PushDelivery:
    alert_id: int
    token: str
    attempt: int
    status: str
    error_code: str | None = None
    sent_at: datetime | None = None
    id: int | None = None
