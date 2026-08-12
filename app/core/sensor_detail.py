from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DetailBucket:
    start: datetime
    value: float | None = None
    slope: float | None = None


@dataclass(frozen=True, slots=True)
class SensorDetail:
    buckets: list[DetailBucket] = field(default_factory=list)
