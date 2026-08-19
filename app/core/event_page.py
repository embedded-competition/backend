from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.alerting import Event


@dataclass(frozen=True, slots=True)
class EventPage:
    items: list[Event] = field(default_factory=list)
    truncated: bool = False
