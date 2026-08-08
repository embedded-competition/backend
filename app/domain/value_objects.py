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

    @property
    def is_auto_clearable(self) -> bool:
        """ALARM은 자동 해제 없음 — 해제는 명시적 명령으로만."""
        return self is not AlertState.ALARM


class GasChannel(StrEnum):
    VOC = "VOC"
    H2 = "H2"
    CO = "CO"

    @property
    def can_promote_alone(self) -> bool:
        """단독 승격 경로가 있는 채널인가.

        CO는 S3부터 증가하는 확증 채널이라 단독 승격 없음
        (gas-detection-algorithm-design.md P4).
        """
        return self is not GasChannel.CO


@dataclass(frozen=True, slots=True)
class DeviceId:
    """LoRa 프레임의 노드 식별자. MAC 하위 바이트 hex."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("device hw_id는 비어 있을 수 없다")
        if len(self.value) > 32:
            raise ValueError(f"device hw_id가 너무 길다: {len(self.value)}자")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ChannelReading:
    """가스 채널 1개의 정규화 측정값. raw는 저장하지 않는다 (docs/db-schema.md D3)."""

    channel: GasChannel
    deviation: float | None
    """baseline 대비 z-score. 가스 방향이 양수 (VOC는 부호 반전 적용됨)."""
    slope: float | None
    """deviation 변화율 (z/min)."""
