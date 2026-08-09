"""저장된 수신 기록. 프레임(무선이 준 것) + 서버가 덧붙인 것."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, ChannelReading, GasChannel


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
        self.received_at = require_aware(self.received_at, "received_at")

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
