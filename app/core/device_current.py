from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition


@dataclass(frozen=True, slots=True)
class DeviceCurrent:
    status: AlertState | None = None
    conditions: frozenset[Condition] = frozenset()
    at: datetime | None = None
    latched: bool = False
    water: bool = False
    values: dict[Measure, float] = field(default_factory=dict)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)
