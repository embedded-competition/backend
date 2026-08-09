"""ORM ↔ domain 변환. repository 구현이 소유한다 — 계층 누수 차단 지점."""

from __future__ import annotations

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.models import (
    Alert,
    Device,
    Event,
    PushToken,
    RadioQuality,
    Reading,
)
from app.domain.value_objects import (
    AlertState,
    DeviceId,
    EventKind,
    SignatureFlags,
)
from app.infrastructure.db.orm import (
    AlertOrm,
    DeviceOrm,
    EventOrm,
    PushTokenOrm,
    ReadingOrm,
)


def device_to_domain(row: DeviceOrm) -> Device:
    return Device(
        id=row.id,
        public_id=row.public_id,
        mac=row.mac,
        hw_id=DeviceId(row.hw_id) if row.hw_id else None,
        label=row.label,
        parking_slot=row.parking_slot,
        management_phone=row.management_phone,
        firmware_version=row.firmware_version,
        frame_version=row.frame_version,
        is_active=row.is_active,
        registered_at=row.registered_at,
        last_seen_at=row.last_seen_at,
        last_seq=row.last_seq,
        last_state=AlertState(row.last_state) if row.last_state else None,
    )


def apply_device(row: DeviceOrm, device: Device) -> DeviceOrm:
    row.public_id = device.public_id
    row.mac = device.mac
    row.hw_id = str(device.hw_id) if device.hw_id else None
    row.label = device.label
    row.parking_slot = device.parking_slot
    row.management_phone = device.management_phone
    row.firmware_version = device.firmware_version
    row.frame_version = device.frame_version
    row.is_active = device.is_active
    if device.registered_at is not None:
        row.registered_at = device.registered_at
    row.last_seen_at = device.last_seen_at
    row.last_seq = device.last_seq
    row.last_state = device.last_state.value if device.last_state else None
    return row


def reading_to_domain(row: ReadingOrm) -> Reading:
    """센서 값은 Measure enum이 컬럼명이라 루프 하나로 끝난다."""
    return Reading(
        id=row.id,
        device_id=row.device_id,
        received_at=row.received_at,
        radio=RadioQuality(rssi=row.rssi, snr=row.snr),
        frame=TelemetryFrame(
            version=row.frame_version,
            seq=row.seq,
            measured_at=row.measured_at,
            state=AlertState(row.state),
            latched=bool(row.latched),
            values=_values_of(row),
            signature=_signature_to_domain(row),
            batt_mv=row.batt_mv,
            water=row.water,
            location=Coordinates(lat=row.lat, lon=row.lon)
            if row.lat is not None and row.lon is not None
            else None,
        ),
    )


def _values_of(row: ReadingOrm) -> dict[Measure, float]:
    found = ((measure, getattr(row, measure.value)) for measure in Measure)
    return {measure: value for measure, value in found if value is not None}


def _signature_to_domain(row: ReadingOrm) -> SignatureFlags | None:
    """플래그가 하나도 없으면 노드가 signature를 안 보낸 것 — None으로 구분한다."""
    if row.sig_rise is None and row.sig_hold is None and row.sig_no_recover is None:
        return None
    return SignatureFlags(
        rise=bool(row.sig_rise),
        hold=bool(row.sig_hold),
        no_recover=bool(row.sig_no_recover),
        hold_s=row.sig_hold_s or 0,
    )


def reading_to_columns(reading: Reading) -> dict[str, object]:
    """멱등 삽입(ON CONFLICT)에 쓰려고 dict로 낸다."""
    frame = reading.frame
    columns: dict[str, object] = {
        "device_id": reading.device_id,
        "seq": frame.seq,
        "measured_at": frame.measured_at,
        "received_at": reading.received_at,
        "frame_version": frame.version,
        "state": frame.state.value,
        "latched": frame.latched,
        "water": frame.water,
        "batt_mv": frame.batt_mv,
        "lat": frame.location.lat if frame.location else None,
        "lon": frame.location.lon if frame.location else None,
        "rssi": reading.radio.rssi,
        "snr": reading.radio.snr,
        "sig_rise": frame.signature.rise if frame.signature else None,
        "sig_hold": frame.signature.hold if frame.signature else None,
        "sig_no_recover": frame.signature.no_recover if frame.signature else None,
        "sig_hold_s": frame.signature.hold_s if frame.signature else None,
    }
    # Measure.value == 컬럼명이라 항목 추가 시 이 함수는 안 바뀐다.
    columns.update({measure.value: frame.values.get(measure) for measure in Measure})
    return columns


def alert_to_domain(row: AlertOrm) -> Alert:
    return Alert(
        id=row.id,
        device_id=row.device_id,
        reading_id=row.reading_id,
        from_state=AlertState(row.from_state),
        to_state=AlertState(row.to_state),
        occurred_at=row.occurred_at,
        detected_at=row.detected_at,
        acknowledged_at=row.acknowledged_at,
        acknowledged_note=row.acknowledged_note,
    )


def apply_alert(row: AlertOrm, alert: Alert) -> AlertOrm:
    row.device_id = alert.device_id
    row.reading_id = alert.reading_id
    row.from_state = alert.from_state.value
    row.to_state = alert.to_state.value
    row.occurred_at = alert.occurred_at
    row.detected_at = alert.detected_at
    row.acknowledged_at = alert.acknowledged_at
    row.acknowledged_note = alert.acknowledged_note
    return row


def event_to_domain(row: EventOrm) -> Event:
    return Event(
        id=row.id,
        device_id=row.device_id,
        alert_id=row.alert_id,
        kind=EventKind(row.kind),
        occurred_at=row.occurred_at,
        description=row.description,
    )


def apply_event(row: EventOrm, event: Event) -> EventOrm:
    row.device_id = event.device_id
    row.alert_id = event.alert_id
    row.kind = event.kind.value
    row.occurred_at = event.occurred_at
    row.description = event.description
    return row


def push_token_to_domain(row: PushTokenOrm) -> PushToken:
    return PushToken(
        id=row.id,
        device_id=row.device_id,
        token=row.token,
        platform=row.platform,
        registered_at=row.registered_at,
        last_used_at=row.last_used_at,
        is_active=row.is_active,
        deactivated_reason=row.deactivated_reason,
    )


def apply_push_token(row: PushTokenOrm, token: PushToken) -> PushTokenOrm:
    row.device_id = token.device_id
    row.token = token.token
    row.platform = token.platform
    row.registered_at = token.registered_at
    row.last_used_at = token.last_used_at
    row.is_active = token.is_active
    row.deactivated_reason = token.deactivated_reason
    return row
