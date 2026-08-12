from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.exceptions import FrameFieldError
from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition, DeviceId

CSV_FRAME_VERSION = 0

_NO_ALERT = "NONE"
_WATER_ALERT = "WATER_LEVEL"
_SATURATED_SUFFIX = "_SATURATED"
_ALERT_SEPARATOR = "|"

_MEASURE_BY_KEY = {
    "MQ7": Measure.CO_DEV,
    "MQ8": Measure.H2_DEV,
    "SGP": Measure.VOC_DEV,
    "FSR": Measure.PRESSURE_DEV,
}

_CONDITION_BY_CAUSE = {
    "MQ7": Condition.CO_RISE,
    "MQ8": Condition.H2_RISE,
    "SGP": Condition.VOC_RISE,
    "SGP40": Condition.VOC_RISE,
    "FSR": Condition.PRESSURE_RISE,
    _WATER_ALERT: Condition.WATER,
}


@dataclass(slots=True)
class NodeCsvParser:
    hw_id: str
    _seq: int = field(default=0, init=False)

    def parse(self, payload: bytes, received_at: datetime) -> TelemetryFrame:
        fields = _fields_of(payload)
        alert = fields.pop("ALERT", _NO_ALERT)
        conditions = _conditions_of(alert)
        self._seq = (self._seq + 1) & 0xFFFF
        return TelemetryFrame(
            version=CSV_FRAME_VERSION,
            hw_id=DeviceId(self.hw_id),
            seq=self._seq,
            measured_at=received_at,
            state=AlertState.from_conditions(conditions),
            conditions=conditions,
            values=_values_of(fields),
            water=_WATER_ALERT in alert,
        )


def _fields_of(payload: bytes) -> dict[str, str]:
    text = payload.decode("utf-8", "replace").strip()
    pairs = (item.partition("=") for item in text.split(",") if item)
    fields = {key.strip(): value.strip() for key, _, value in pairs if key.strip()}
    if not fields:
        raise FrameFieldError(f"노드 CSV로 읽을 수 없다: {text!r}")
    return fields


def _values_of(fields: dict[str, str]) -> dict[Measure, float]:
    found = ((_MEASURE_BY_KEY.get(key), key, value) for key, value in fields.items())
    return {measure: _number(key, value) for measure, key, value in found if measure is not None}


def _number(key: str, value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise FrameFieldError(f"{key} 값이 숫자가 아니다: {value!r}") from exc


def _conditions_of(alert: str) -> frozenset[Condition]:
    if alert == _NO_ALERT or not alert:
        return frozenset()
    causes = alert.split(_ALERT_SEPARATOR)
    return frozenset(_condition_of(cause) for cause in causes)


def _condition_of(cause: str) -> Condition:
    if cause.endswith(_SATURATED_SUFFIX):
        return Condition.SENSOR_FAULT
    found = _CONDITION_BY_CAUSE.get(cause)
    if found is None:
        raise FrameFieldError(f"알 수 없는 ALERT 원인이다: {cause!r}")
    return found
