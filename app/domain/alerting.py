from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.exceptions import AlertAlreadyAcknowledged
from app.domain.stored import require_stored
from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, EventKind


@dataclass(slots=True)
class Alert:
    device_id: int
    from_state: AlertState
    to_state: AlertState
    occurred_at: datetime
    detected_at: datetime
    reading_id: int | None = None
    acknowledged_at: datetime | None = None
    acknowledged_note: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.from_state is self.to_state:
            raise ValueError("전이가 아닌 값으로 Alert를 만들 수 없다")
        self.occurred_at = require_aware(self.occurred_at, "occurred_at")
        self.detected_at = require_aware(self.detected_at, "detected_at")

    @property
    def key(self) -> int:
        return require_stored(self.id, "alert")

    @property
    def is_active(self) -> bool:
        return self.acknowledged_at is None

    def acknowledge(self, *, at: datetime, note: str | None = None) -> None:
        if self.acknowledged_at is not None:
            raise AlertAlreadyAcknowledged(f"alert {self.id}는 이미 해제됨")
        self.acknowledged_at = require_aware(at, "at")
        self.acknowledged_note = note


@dataclass(slots=True)
class Event:
    device_id: int
    kind: EventKind
    occurred_at: datetime
    description: str
    alert_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.occurred_at = require_aware(self.occurred_at, "occurred_at")
        if not self.description.strip():
            raise ValueError("event description은 비어 있을 수 없다")
        if self.kind is EventKind.STATE_CHANGE and self.alert_id is None:
            raise ValueError("state_change 이벤트는 alert_id를 가져야 한다")
