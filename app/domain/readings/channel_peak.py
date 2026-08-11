from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.timestamps import require_aware


@dataclass(frozen=True, slots=True)
class ChannelPeak:
    at: datetime
    value: float | None = None
    slope: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at, "at"))
