"""디코딩된 텔레메트리 프레임.

무선 인코딩(오프셋·스케일·CRC)은 infrastructure가 알고, 이 타입은 "노드가 무엇을
보냈는가"만 표현한다. 센서 값은 개별 필드가 아니라 measurements 하나로 받는다 —
항목 추가가 이 파일을 건드리지 않게.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain import measurements as m
from app.domain.measurements import Aspect, Measure
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    GasChannel,
    SignatureFlags,
)

_LAT_LIMIT = 90.0
_LON_LIMIT = 180.0


@dataclass(frozen=True, slots=True)
class Coordinates:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -_LAT_LIMIT <= self.lat <= _LAT_LIMIT:
            raise ValueError(f"lat 범위 이탈: {self.lat}")
        if not -_LON_LIMIT <= self.lon <= _LON_LIMIT:
            raise ValueError(f"lon 범위 이탈: {self.lon}")


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    """프레임 1건. 아직 내부 device PK를 모른다 — hw_id로만 식별된다."""

    version: int
    seq: int
    measured_at: datetime
    state: AlertState
    hw_id: DeviceId | None = None
    """수신 경로에만 있다. DB에서 복원한 프레임은 device FK로 식별되므로 None."""
    latched: bool = False
    values: dict[Measure, float] = field(default_factory=dict)
    """결측 항목은 키 자체가 없다 — None과 '값 0'을 구분한다."""
    signature: SignatureFlags | None = None
    batt_mv: int | None = None
    water: bool | None = None
    location: Coordinates | None = None

    def __post_init__(self) -> None:
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at은 timezone-aware여야 한다")
        m.validate(self.values)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)

    def channel(self, channel: GasChannel) -> ChannelReading | None:
        """채널 값이 하나도 없으면 None — 미장착 센서와 구분한다."""
        slots = m.channel_measures(channel)
        deviation = self.values.get(slots[Aspect.DEVIATION])
        slope = self.values.get(slots[Aspect.SLOPE])
        if deviation is None and slope is None:
            return None
        return ChannelReading(channel=channel, deviation=deviation, slope=slope)
