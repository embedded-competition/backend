"""푸시 대상과 발송 이력. 어떤 푸시 제공자인지는 여기서 모른다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PushToken:
    """Expo 푸시 토큰."""

    device_id: int
    token: str
    registered_at: datetime
    platform: str | None = None
    last_used_at: datetime | None = None
    is_active: bool = True
    deactivated_reason: str | None = None
    id: int | None = None

    def deactivate(self, reason: str) -> None:
        """영구 실패(UNREGISTERED 등) 시 호출. 방치하면 실패율이 계속 쌓인다."""
        self.is_active = False
        self.deactivated_reason = reason


@dataclass(slots=True)
class PushDelivery:
    """발송 시도 1건. 실패 원인 추적의 근거다."""

    alert_id: int
    token: str
    attempt: int
    status: str
    error_code: str | None = None
    sent_at: datetime | None = None
    id: int | None = None
