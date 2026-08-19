from __future__ import annotations

from enum import StrEnum

from app.domain.value_objects.condition import Condition


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

    @classmethod
    def from_conditions(cls, conditions: frozenset[Condition]) -> AlertState:
        """SENSOR_FAULT는 위험이 아니라 불신이라 다른 원인과 섞이지 않는다."""
        if not conditions:
            return cls.NORMAL
        if conditions <= {Condition.SENSOR_FAULT}:
            return cls.FAULT
        return cls.WATCH


_WORST_LAST: tuple[AlertState, ...] = (
    AlertState.WARMUP,
    AlertState.NORMAL,
    AlertState.FAULT,
    AlertState.WATCH,
    AlertState.ALARM,
)
