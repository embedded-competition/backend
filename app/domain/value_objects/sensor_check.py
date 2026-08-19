from __future__ import annotations

from enum import StrEnum

from app.domain.value_objects.condition import Condition


class SensorCheck(StrEnum):
    """센서를 믿을 수 있는가. 측정값이 무엇을 가리키는가와 다른 축이다.

    값이 오르는 것은 센서가 멀쩡하다는 뜻이지 고장이 아니다. 포화된 센서만
    못 믿는 상태다.
    """

    OK = "OK"
    FAULT = "FAULT"

    @classmethod
    def of(cls, conditions: frozenset[Condition] | None) -> SensorCheck | None:
        """관측이 없으면 None이다 — 점검한 적 없는 것과 이상 없는 것은 다르다."""
        if conditions is None:
            return None
        return cls.FAULT if Condition.SENSOR_FAULT in conditions else cls.OK
