from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.measurements import Measure
from app.domain.readings import ChannelPeak
from app.domain.value_objects import AlertState, Condition


@dataclass(frozen=True, slots=True)
class PeriodPeaks:
    status: AlertState | None = None
    conditions: frozenset[Condition] = frozenset()
    channels: dict[Measure, ChannelPeak] = field(default_factory=dict)
    values: dict[Measure, float] = field(default_factory=dict)

    def channel(self, deviation: Measure) -> ChannelPeak | None:
        return self.channels.get(deviation)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)
