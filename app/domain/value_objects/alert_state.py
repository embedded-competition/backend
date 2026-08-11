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

    @property
    def severity(self) -> int:
        return _WORST_LAST.index(self)

    @classmethod
    def of_severity(cls, severity: int) -> AlertState:
        return _WORST_LAST[severity]


_WORST_LAST: tuple[AlertState, ...] = (
    AlertState.WARMUP,
    AlertState.NORMAL,
    AlertState.FAULT,
    AlertState.WATCH,
    AlertState.ALARM,
)
