"""기기 애그리게이트. 노드 1개 = 차량 1대 (docs/db-schema.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, DeviceId


@dataclass(slots=True)
class Device:
    public_id: str
    mac: str
    label: str
    # 앱이 MAC으로 먼저 등록하고, 노드 첫 프레임에서 hw_id가 채워진다
    hw_id: DeviceId | None = None
    parking_slot: str | None = None
    management_phone: str | None = None
    firmware_version: str | None = None
    frame_version: int | None = None
    is_active: bool = True
    registered_at: datetime | None = None
    # 비정규화 필드 (D7) — 헬스체크·유실 판정 비용 절감
    last_seen_at: datetime | None = None
    last_seq: int | None = None
    last_state: AlertState | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("device label은 비어 있을 수 없다")

    def is_offline(self, *, now: datetime, threshold_s: int) -> bool:
        """무응답 판정. 한 번도 수신한 적 없으면 offline으로 본다."""
        if self.last_seen_at is None:
            return True
        return (now - self.last_seen_at).total_seconds() > threshold_s

    def missed_frames_since(self, seq: int) -> int:
        """seq 건너뜀 수. 유실률은 안테나·거리 문제의 유일한 정량 지표다."""
        if self.last_seq is None:
            return 0
        gap = seq - self.last_seq - 1
        return max(gap, 0)

    def observe(self, *, seq: int, at: datetime, state: AlertState) -> None:
        at = require_aware(at, "at")
        # 재전송이 늦게 도착해도 최신 관측을 되돌리지 않는다.
        if self.last_seen_at is not None and at < self.last_seen_at:
            return
        self.last_seq = seq
        self.last_seen_at = at
        self.last_state = state
