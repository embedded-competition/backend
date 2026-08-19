"""시뮬레이터 노드가 보내는 payload.

와이어 프레임 v1은 판정을 나르지 못한다 — 상태 바이트가 없고, 파서는 늘 NORMAL을
쓴다. 그 포맷으로 시뮬레이션하면 값만 오르내리고 화면은 영원히 정상이라, 만들려던
화면을 하나도 만들지 못한다. 그래서 노드가 이미 갖고 있는 판정(상태·조건·latch)을
그대로 싣는 별도 payload를 쓴다. 프레임 v2가 나르기로 한 것과 같은 내용이다.

측정 시각은 싣지 않는다. 실기 노드에 시계가 없어 수신 시각이 곧 측정 시각이고,
시뮬레이터도 같은 규칙을 따른다.
"""

from __future__ import annotations

import json
from datetime import datetime

from app.domain.exceptions import FrameFieldError
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition, DeviceId
from app.infrastructure.lora.frame import ABSENT_SEQ
from app.simulation.node import SIMULATED_FRAME_VERSION

_ENCODING = "utf-8"


def encode(frame: TelemetryFrame) -> bytes:
    body = {
        "hw_id": str(frame.hw_id),
        "state": frame.state.value,
        "conditions": sorted(condition.value for condition in frame.conditions),
        "latched": frame.latched,
        "water": bool(frame.water),
        "values": {measure.value: value for measure, value in frame.values.items()},
        "location": _location_wire(frame.location),
    }
    return json.dumps(body, separators=(",", ":")).encode(_ENCODING)


def decode(payload: bytes, received_at: datetime) -> TelemetryFrame:
    try:
        body = json.loads(payload.decode(_ENCODING))
        return TelemetryFrame(
            version=SIMULATED_FRAME_VERSION,
            hw_id=DeviceId(body["hw_id"]),
            seq=ABSENT_SEQ,
            measured_at=received_at,
            state=AlertState(body["state"]),
            conditions=frozenset(Condition(name) for name in body["conditions"]),
            latched=bool(body["latched"]),
            water=bool(body["water"]),
            values={Measure(name): float(value) for name, value in body["values"].items()},
            location=_location_of(body["location"]),
        )
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise FrameFieldError(f"시뮬레이터 payload를 읽을 수 없다: {exc}") from exc


def _location_wire(location: Coordinates | None) -> list[float] | None:
    return None if location is None else [location.lat, location.lon]


def _location_of(wire: list[float] | None) -> Coordinates | None:
    return None if wire is None else Coordinates(lat=wire[0], lon=wire[1])
