"""도메인 엔티티. dataclass, 불변식은 메서드 안. 외부 import 0."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.exceptions import AlertAlreadyAcknowledged
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    GasChannel,
    SignatureFlags,
)


def _require_aware(value: datetime, name: str) -> datetime:
    """naive datetime은 받지 않는다 — 저장 시점에 로컬시간과 섞인다."""
    if value.tzinfo is None:
        raise ValueError(f"{name}은 timezone-aware여야 한다")
    return value.astimezone(UTC)


@dataclass(slots=True)
class Device:
    """노드 1개 = 차량 1대 (docs/db-schema.md)."""

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
        at = _require_aware(at, "at")
        # 재전송이 늦게 도착해도 최신 관측을 되돌리지 않는다.
        if self.last_seen_at is not None and at < self.last_seen_at:
            return
        self.last_seq = seq
        self.last_seen_at = at
        self.last_state = state


@dataclass(slots=True)
class Reading:
    """수신 프레임 1건. state는 노드가 보낸 원본 값이다 (D2)."""

    device_id: int
    seq: int
    measured_at: datetime
    received_at: datetime
    frame_version: int
    state: AlertState
    latched: bool | None = None
    channels: tuple[ChannelReading, ...] = ()
    signature: SignatureFlags | None = None
    temp_c: float | None = None
    humidity_pct: float | None = None
    d_rh_dt: float | None = None
    pressure_dev: float | None = None
    pressure_rate: float | None = None
    water: bool | None = None
    batt_mv: int | None = None
    lat: float | None = None
    lon: float | None = None
    rssi: int | None = None
    snr: float | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.measured_at = _require_aware(self.measured_at, "measured_at")
        self.received_at = _require_aware(self.received_at, "received_at")
        if self.humidity_pct is not None and not 0.0 <= self.humidity_pct <= 100.0:
            raise ValueError(f"humidity_pct 범위 이탈: {self.humidity_pct}")
        if self.temp_c is not None and not -40.0 <= self.temp_c <= 125.0:
            raise ValueError(f"temp_c 범위 이탈: {self.temp_c}")
        if self.rssi is not None and self.rssi > 0:
            raise ValueError(f"rssi는 0 이하여야 한다: {self.rssi}")
        if self.lat is not None and not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"lat 범위 이탈: {self.lat}")
        if self.lon is not None and not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"lon 범위 이탈: {self.lon}")

    @property
    def clock_skew_s(self) -> float:
        """노드 시각과 서버 수신 시각의 차이. 값을 보정하지 않고 드러낸다."""
        return (self.received_at - self.measured_at).total_seconds()

    def channel(self, channel: GasChannel) -> ChannelReading | None:
        return next((c for c in self.channels if c.channel is channel), None)


@dataclass(slots=True)
class Alert:
    """상태 전이 이벤트. readings의 요약이지 그 반대가 아니다."""

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
        self.occurred_at = _require_aware(self.occurred_at, "occurred_at")
        self.detected_at = _require_aware(self.detected_at, "detected_at")

    @property
    def is_active(self) -> bool:
        return self.acknowledged_at is None

    def acknowledge(self, *, at: datetime, note: str | None = None) -> None:
        """해제는 명시적 명령으로만. ALARM은 자동 해제되지 않는다."""
        if self.acknowledged_at is not None:
            raise AlertAlreadyAcknowledged(f"alert {self.id}는 이미 해제됨")
        self.acknowledged_at = _require_aware(at, "at")
        self.acknowledged_note = note
