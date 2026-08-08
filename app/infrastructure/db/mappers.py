"""ORM ↔ domain 변환. repository 구현이 소유한다 — 계층 누수 차단 지점."""

from __future__ import annotations

from app.domain.models import Alert, Device, Event, PushToken, Reading
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    EventKind,
    GasChannel,
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
    channels = tuple(
        ChannelReading(channel=channel, deviation=dev, slope=slope)
        for channel, dev, slope in (
            (GasChannel.VOC, row.voc_dev, row.voc_slope),
            (GasChannel.H2, row.h2_dev, row.h2_slope),
            (GasChannel.CO, row.co_dev, row.co_slope),
        )
        # 값이 하나도 없는 채널은 도메인에 올리지 않는다 (미장착 센서와 구분)
        if dev is not None or slope is not None
    )
    return Reading(
        id=row.id,
        device_id=row.device_id,
        seq=row.seq,
        measured_at=row.measured_at,
        received_at=row.received_at,
        frame_version=row.frame_version,
        state=AlertState(row.state),
        latched=row.latched,
        channels=channels,
        signature=_signature_to_domain(row),
        temp_c=row.temp_c,
        humidity_pct=row.humidity_pct,
        d_rh_dt=row.d_rh_dt,
        pressure_dev=row.pressure_dev,
        pressure_rate=row.pressure_rate,
        water=row.water,
        batt_mv=row.batt_mv,
        lat=row.lat,
        lon=row.lon,
        rssi=row.rssi,
        snr=row.snr,
    )


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
    values: dict[str, object] = {
        "device_id": reading.device_id,
        "seq": reading.seq,
        "measured_at": reading.measured_at,
        "received_at": reading.received_at,
        "frame_version": reading.frame_version,
        "state": reading.state.value,
        "latched": reading.latched,
        "temp_c": reading.temp_c,
        "humidity_pct": reading.humidity_pct,
        "d_rh_dt": reading.d_rh_dt,
        "pressure_dev": reading.pressure_dev,
        "pressure_rate": reading.pressure_rate,
        "water": reading.water,
        "batt_mv": reading.batt_mv,
        "lat": reading.lat,
        "lon": reading.lon,
        "rssi": reading.rssi,
        "snr": reading.snr,
        "sig_rise": reading.signature.rise if reading.signature else None,
        "sig_hold": reading.signature.hold if reading.signature else None,
        "sig_no_recover": reading.signature.no_recover if reading.signature else None,
        "sig_hold_s": reading.signature.hold_s if reading.signature else None,
        "voc_dev": None,
        "voc_slope": None,
        "h2_dev": None,
        "h2_slope": None,
        "co_dev": None,
        "co_slope": None,
    }
    for measurement in reading.channels:
        prefix = measurement.channel.value.lower()
        values[f"{prefix}_dev"] = measurement.deviation
        values[f"{prefix}_slope"] = measurement.slope
    return values


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
