from __future__ import annotations

from enum import StrEnum


class AlertState(StrEnum):
    WARMUP = "WARMUP"
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ALARM = "ALARM"
    FAULT = "FAULT"

    @property
    def needs_dispatch(self) -> bool:
        return self in (AlertState.WATCH, AlertState.ALARM, AlertState.FAULT)
