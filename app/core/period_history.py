from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.alerting import Event
from app.domain.readings import Bucket
from app.domain.value_objects import Interval, Period


@dataclass(frozen=True, slots=True)
class PeriodHistory:
    period: Period
    interval: Interval
    buckets: list[Bucket] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
