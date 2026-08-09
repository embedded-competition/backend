"""도메인 엔티티. dataclass, 불변식은 메서드 안. 외부 import 0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.exceptions import AlertAlreadyAcknowledged
from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    EventKind,
    GasChannel,
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


@dataclass(frozen=True, slots=True)
class RadioQuality:
    """수신 품질. 유실 원인 추적의 유일한 지표다."""

    rssi: int | None = None
    snr: float | None = None

    def __post_init__(self) -> None:
        if self.rssi is not None and self.rssi > 0:
            raise ValueError(f"rssi는 0 이하여야 한다: {self.rssi}")


@dataclass(slots=True)
class Reading:
    """수신 프레임 1건 + 서버가 덧붙인 것.

    센서 값을 다시 나열하지 않고 frame을 합성한다 — 항목 추가가 이 클래스를
    건드리지 않는다.
    """

    device_id: int
    frame: TelemetryFrame
    received_at: datetime
    radio: RadioQuality = field(default_factory=RadioQuality)
    id: int | None = None

    def __post_init__(self) -> None:
        self.received_at = _require_aware(self.received_at, "received_at")

    # frame으로 위임 — 호출부가 reading.frame.state를 매번 쓰지 않게
    @property
    def seq(self) -> int:
        return self.frame.seq

    @property
    def state(self) -> AlertState:
        return self.frame.state

    @property
    def measured_at(self) -> datetime:
        return self.frame.measured_at

    @property
    def clock_skew_s(self) -> float:
        """노드 시각과 서버 수신 시각의 차이. 값을 보정하지 않고 드러낸다."""
        return (self.received_at - self.frame.measured_at).total_seconds()

    def value(self, measure: Measure) -> float | None:
        return self.frame.value(measure)

    def channel(self, channel: GasChannel) -> ChannelReading | None:
        return self.frame.channel(channel)


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


@dataclass(slots=True)
class Event:
    """기록 탭 항목. description은 서버가 생성한다 (D10)."""

    device_id: int
    kind: EventKind
    occurred_at: datetime
    description: str
    alert_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.occurred_at = _require_aware(self.occurred_at, "occurred_at")
        if not self.description.strip():
            raise ValueError("event description은 비어 있을 수 없다")
        if self.kind is EventKind.STATE_CHANGE and self.alert_id is None:
            raise ValueError("state_change 이벤트는 alert_id를 가져야 한다")


@dataclass(slots=True)
class AccessToken:
    """deviceToken. 원문은 발급 순간에만 존재하고 저장되지 않는다 (D9)."""

    device_id: int
    token_hash: str
    created_at: datetime
    last_used_at: datetime | None = None
    id: int | None = None


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
