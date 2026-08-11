from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.readings import ChannelPeak, Reading
from app.domain.value_objects import AlertState, GasChannel, Period


@dataclass(frozen=True, slots=True)
class PeriodSummary:
    period: Period
    live: bool
    state: AlertState | None
    event_count: int
    current: Reading | None = None
    peaks: dict[GasChannel, ChannelPeak] = field(default_factory=dict)

    def peak(self, channel: GasChannel) -> ChannelPeak | None:
        return self.peaks.get(channel)
