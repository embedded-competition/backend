from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.timestamps import require_aware
from app.domain.value_objects import AlertState, GasChannel


@dataclass(frozen=True, slots=True)
class ChannelPeak:
    channel: GasChannel
    at: datetime
    state: AlertState
    deviation: float | None = None
    slope: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at, "at"))
