from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings.radio_quality import RadioQuality
from app.domain.stored import require_stored
from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, ChannelReading, Condition, GasChannel


@dataclass(slots=True)
class Reading:
    device_id: int
    frame: TelemetryFrame
    received_at: datetime
    radio: RadioQuality = field(default_factory=RadioQuality)
    id: int | None = None

    def __post_init__(self) -> None:
        self.received_at = require_aware(self.received_at, "received_at")

    @property
    def key(self) -> int:
        return require_stored(self.id, "reading")

    @property
    def seq(self) -> int:
        return self.frame.seq

    @property
    def state(self) -> AlertState:
        return self.frame.state

    @property
    def conditions(self) -> frozenset[Condition]:
        return self.frame.conditions

    @property
    def measured_at(self) -> datetime:
        return self.frame.measured_at

    def value(self, measure: Measure) -> float | None:
        return self.frame.value(measure)

    def channel(self, channel: GasChannel) -> ChannelReading | None:
        return self.frame.channel(channel)
