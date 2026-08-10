from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.stored import require_stored
from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, DeviceId


@dataclass(slots=True)
class Device:
    public_id: str
    mac: str
    label: str
    hw_id: DeviceId | None = None
    parking_slot: str | None = None
    management_phone: str | None = None
    firmware_version: str | None = None
    frame_version: int | None = None
    is_active: bool = True
    registered_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_seq: int | None = None
    last_state: AlertState | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("device label은 비어 있을 수 없다")

    @property
    def key(self) -> int:
        return require_stored(self.id, "device")

    def missed_frames_since(self, seq: int) -> int:
        if self.last_seq is None:
            return 0
        gap = seq - self.last_seq - 1
        return max(gap, 0)

    def observe(self, *, seq: int, at: datetime, state: AlertState) -> None:
        at = require_aware(at, "at")
        if self.last_seen_at is not None and at < self.last_seen_at:
            return
        self.last_seq = seq
        self.last_seen_at = at
        self.last_state = state
