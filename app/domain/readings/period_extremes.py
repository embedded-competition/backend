from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.measurements import Measure
from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState


@dataclass(frozen=True, slots=True)
class PeriodExtremes:
    at: datetime
    state: AlertState
    latched: bool = False
    water: bool = False
    values: dict[Measure, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at, "at"))

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)
