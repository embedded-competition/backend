from __future__ import annotations

from app.domain.value_objects import AlertState

_SEVERITY: dict[AlertState, int] = {
    AlertState.WARMUP: 0,
    AlertState.NORMAL: 0,
    AlertState.FAULT: 1,
    AlertState.WATCH: 2,
    AlertState.ALARM: 3,
}


def severity_of(state: AlertState) -> int:
    return _SEVERITY[state]


_ALARM_FLOOR = 2.5
_WATCH_FLOOR = 1.5
_FAULT_FLOOR = 0.5


def state_for(severity: float) -> AlertState:
    if severity >= _ALARM_FLOOR:
        return AlertState.ALARM
    if severity >= _WATCH_FLOOR:
        return AlertState.WATCH
    if severity >= _FAULT_FLOOR:
        return AlertState.FAULT
    return AlertState.NORMAL
