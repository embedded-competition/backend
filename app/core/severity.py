"""상태 심각도 순위. 정렬·비교·집계가 공유하는 단일 기준."""

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


def state_for(severity: float) -> AlertState:
    """평균 심각도를 대표 상태로 되돌린다."""
    if severity >= 2.5:
        return AlertState.ALARM
    if severity >= 1.5:
        return AlertState.WATCH
    if severity >= 0.5:
        return AlertState.FAULT
    return AlertState.NORMAL
