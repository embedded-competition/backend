from __future__ import annotations

from dataclasses import dataclass

from app.domain.measurements.aspect import Aspect
from app.domain.value_objects import GasChannel


@dataclass(frozen=True, slots=True)
class MeasureSpec:
    unit: str
    minimum: float | None = None
    maximum: float | None = None
    channel: GasChannel | None = None
    aspect: Aspect | None = None
