from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain import measurements as m
from app.domain.frames.coordinates import Coordinates
from app.domain.measurements import Aspect, Measure
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    GasChannel,
    SignatureFlags,
)


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    version: int
    seq: int
    measured_at: datetime
    state: AlertState
    hw_id: DeviceId | None = None
    latched: bool = False
    values: dict[Measure, float] = field(default_factory=dict)
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
        slots = m.channel_measures(channel)
        deviation = self.values.get(slots[Aspect.DEVIATION])
        slope = self.values.get(slots[Aspect.SLOPE])
        if deviation is None and slope is None:
            return None
        return ChannelReading(channel=channel, deviation=deviation, slope=slope)
