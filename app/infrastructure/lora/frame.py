from __future__ import annotations

import math
from datetime import datetime

from app.domain.exceptions import FrameFieldError
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, DeviceId
from app.infrastructure.lora import codec
from app.infrastructure.lora.codec import WireFrame

WIRE_FORMAT_ID = 1
"""서버가 어느 포맷으로 읽었는지만 남긴다.

와이어에는 version 바이트가 없다 — 노드가 보내지 않는다. 이 값은 계약이 아니라
저장된 판독이 어느 파서를 거쳤는지 되짚기 위한 서버 내부 식별자다.
"""

ABSENT_SEQ = 0
"""노드가 seq를 보내지 않는다. 지어내지 않고 0으로 둔다.

서버가 수신 카운터를 세워 seq인 척하면 유실·중복 통계가 거짓이 된다. 셀 수 없으면
셀 수 없다고 말한다. 중복은 (device, measured_at, seq) 유일키가 걸러낸다.
"""

_MEASURE_BY_FIELD = {
    "mq7": Measure.CO_DEV,
    "mq8": Measure.H2_DEV,
    "pressure": Measure.PRESSURE_DEV,
    "water": Measure.WATER_LEVEL,
    "voc": Measure.VOC_DEV,
}


def parse_frame(payload: bytes, received_at: datetime) -> TelemetryFrame:
    """노드에 시계가 없다. 수신 시각이 곧 측정 시각이다."""
    return to_domain(codec.decode(payload), received_at)


def build_frame(frame: TelemetryFrame) -> bytes:
    return codec.encode(to_wire(frame))


def to_domain(wire: WireFrame, received_at: datetime) -> TelemetryFrame:
    """노드가 판정을 보내지 않는다. 상태는 값만으로 정해지지 않으므로 NORMAL로 둔다."""
    try:
        return TelemetryFrame(
            version=WIRE_FORMAT_ID,
            hw_id=DeviceId(wire.mac_hex),
            seq=ABSENT_SEQ,
            measured_at=received_at,
            state=AlertState.NORMAL,
            values=_values_of(wire),
            location=_location_of(wire),
        )
    except ValueError as exc:
        raise FrameFieldError(str(exc)) from exc


def to_wire(frame: TelemetryFrame) -> WireFrame:
    levels = {
        field: _level(frame.values.get(measure)) for field, measure in _MEASURE_BY_FIELD.items()
    }
    location = frame.location
    return WireFrame(
        mac_hex=str(frame.hw_id),
        lat=location.lat if location else math.nan,
        lon=location.lon if location else math.nan,
        **levels,
    )


def _values_of(wire: WireFrame) -> dict[Measure, float]:
    return {measure: float(getattr(wire, field)) for field, measure in _MEASURE_BY_FIELD.items()}


def _location_of(wire: WireFrame) -> Coordinates | None:
    if not wire.has_fix:
        return None
    return Coordinates(lat=wire.lat, lon=wire.lon)


def _level(value: float | None) -> int:
    if value is None:
        return codec.LEVEL_MIN
    return round(value)
