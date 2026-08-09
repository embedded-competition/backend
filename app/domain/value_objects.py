"""식별자 없는 불변 값. 외부 import 0 (stdlib만)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AlertState(StrEnum):
    """노드가 판정해 올려보내는 상태. 서버는 재판정하지 않는다."""

    WARMUP = "WARMUP"
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ALARM = "ALARM"
    FAULT = "FAULT"

    @property
    def needs_dispatch(self) -> bool:
        """이 상태로의 전이가 대응 대상 통지를 유발하는가."""
        return self in (AlertState.WATCH, AlertState.ALARM, AlertState.FAULT)


class GasChannel(StrEnum):
    VOC = "VOC"
    H2 = "H2"
    CO = "CO"


_HW_ID_MAX_LENGTH = 32


@dataclass(frozen=True, slots=True)
class DeviceId:
    """LoRa 프레임의 노드 식별자. MAC 하위 바이트 hex."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("device hw_id는 비어 있을 수 없다")
        if len(self.value) > _HW_ID_MAX_LENGTH:
            raise ValueError(f"device hw_id가 너무 길다: {len(self.value)}자")

    def __str__(self) -> str:
        return self.value


class EventKind(StrEnum):
    """기록 탭 항목 종류 (앱 interface.md §4)."""

    STATE_CHANGE = "state_change"
    ACTION = "action"
    SUPPRESSED = "suppressed"
    """오경보 차단 기록 — 습도 게이트 등으로 승격을 보류한 사실.

    아직 이 값을 쓰는 서버 경로는 없다. 앱 계약과 `ck_events_kind` 제약이 이미
    이 값을 포함하므로 지우면 두 곳이 어긋난다.
    """


@dataclass(frozen=True, slots=True)
class SignatureFlags:
    """판단 근거 3요소. 노드가 계산해 전송한다 (정합화 B1).

    급변(rise) + 지속(hold) + 무회복(no_recover)이 모두 참일 때만 시그니처 성립
    (gas-detection-algorithm-design.md P5 — 크기 단독 판정 금지).
    """

    rise: bool
    hold: bool
    no_recover: bool
    hold_s: int


@dataclass(frozen=True, slots=True)
class ChannelReading:
    """가스 채널 1개의 정규화 측정값. raw는 저장하지 않는다 (docs/db-schema.md D3)."""

    channel: GasChannel
    deviation: float | None
    """baseline 대비 z-score. 가스 방향이 양수 (VOC는 부호 반전 적용됨)."""
    slope: float | None
    """deviation 변화율 (z/min)."""
