from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.measurements import Measure
from app.domain.readings import ChannelPeak
from app.domain.value_objects import AlertState, Period


@dataclass(frozen=True, slots=True)
class PeriodSummary:
    period: Period
    live: bool
    at: datetime | None = None
    state: AlertState | None = None
    latched: bool = False
    water: bool = False
    management_phone: str | None = None
    channels: dict[Measure, ChannelPeak] = field(default_factory=dict)
    values: dict[Measure, float] = field(default_factory=dict)

    def channel(self, deviation: Measure) -> ChannelPeak | None:
        return self.channels.get(deviation)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)
