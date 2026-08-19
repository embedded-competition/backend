"""도메인 객체 빌더.

테스트마다 생성자 인자를 나열하면 필드 하나 추가에 모든 테스트가 깨진다.
기본값은 "유효한 최소 객체"이고, 테스트는 자기가 검증하는 필드만 넘긴다.
`key`를 넘기면 저장된 객체가 된다 — 저장 후에만 성립하는 경로를 태울 때 쓴다.
"""

from __future__ import annotations

from datetime import datetime

from app.domain.alerting import Alert, Event
from app.domain.device import Device
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings import RadioQuality, Reading
from app.domain.value_objects import AlertState, Condition, DeviceId, EventKind, SignatureFlags

HW_ID = DeviceId("44bd8d239c28")
MAC = "44:BD:8D:23:9C:28"


def a_device(
    *,
    key: int | None = None,
    public_id: str = "dev_test0001",
    mac: str = MAC,
    hw_id: DeviceId | None = HW_ID,
    label: str = "1호차",
    registered_at: datetime | None = None,
    last_seen_at: datetime | None = None,
    last_seq: int | None = None,
    last_state: AlertState | None = None,
) -> Device:
    return Device(
        id=key,
        public_id=public_id,
        mac=mac,
        hw_id=hw_id,
        label=label,
        registered_at=registered_at,
        last_seen_at=last_seen_at,
        last_seq=last_seq,
        last_state=last_state,
    )


def a_frame(
    measured_at: datetime,
    *,
    version: int = 2,
    seq: int = 1,
    state: AlertState = AlertState.NORMAL,
    conditions: frozenset[Condition] = frozenset(),
    values: dict[Measure, float] | None = None,
    signature: SignatureFlags | None = None,
    batt_mv: int | None = None,
    location: Coordinates | None = None,
    latched: bool = False,
) -> TelemetryFrame:
    return TelemetryFrame(
        version=version,
        hw_id=HW_ID,
        seq=seq,
        measured_at=measured_at,
        state=state,
        conditions=conditions,
        values=values or {},
        signature=signature,
        batt_mv=batt_mv,
        location=location,
        latched=latched,
    )


def a_reading(
    measured_at: datetime,
    *,
    key: int | None = None,
    device_id: int = 1,
    received_at: datetime | None = None,
    radio: RadioQuality | None = None,
    frame: TelemetryFrame | None = None,
) -> Reading:
    """frame을 안 넘기면 measured_at만 다른 최소 프레임이 붙는다."""
    return Reading(
        id=key,
        device_id=device_id,
        frame=frame if frame is not None else a_frame(measured_at),
        received_at=received_at if received_at is not None else measured_at,
        radio=radio if radio is not None else RadioQuality(),
    )


def an_alert(
    occurred_at: datetime,
    *,
    key: int | None = None,
    device_id: int = 1,
    from_state: AlertState = AlertState.NORMAL,
    to_state: AlertState = AlertState.ALARM,
) -> Alert:
    return Alert(
        id=key,
        device_id=device_id,
        from_state=from_state,
        to_state=to_state,
        occurred_at=occurred_at,
        detected_at=occurred_at,
    )


def an_event(
    occurred_at: datetime,
    *,
    device_id: int = 1,
    kind: EventKind = EventKind.SUPPRESSED,
    description: str = "습도 급변으로 가스 채널 승격 보류 (오경보 아님)",
    alert_id: int | None = None,
) -> Event:
    return Event(
        device_id=device_id,
        kind=kind,
        occurred_at=occurred_at,
        description=description,
        alert_id=alert_id,
    )
