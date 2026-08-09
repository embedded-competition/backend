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


# 평균 심각도 → 대표 상태 경계. 각 등급의 중간값이다 (ALARM=3, WATCH=2, FAULT=1).
_ALARM_FLOOR = 2.5
_WATCH_FLOOR = 1.5
_FAULT_FLOOR = 0.5


def state_for(severity: float) -> AlertState:
    """평균 심각도를 대표 상태로 되돌린다."""
    if severity >= _ALARM_FLOOR:
        return AlertState.ALARM
    if severity >= _WATCH_FLOOR:
        return AlertState.WATCH
    if severity >= _FAULT_FLOOR:
        return AlertState.FAULT
    return AlertState.NORMAL
