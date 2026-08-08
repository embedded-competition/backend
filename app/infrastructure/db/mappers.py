"""ORM ↔ domain 변환. repository 구현이 소유한다 — 계층 누수 차단 지점."""

from __future__ import annotations

from app.domain.models import Alert, Device, Reading
from app.domain.value_objects import AlertState, ChannelReading, DeviceId, GasChannel
from app.infrastructure.db.orm import AlertOrm, DeviceOrm, ReadingOrm


def device_to_domain(row: DeviceOrm) -> Device:
    return Device(
        id=row.id,
        hw_id=DeviceId(row.hw_id),
        label=row.label,
        parking_slot=row.parking_slot,
        firmware_version=row.firmware_version,
        frame_version=row.frame_version,
        is_active=row.is_active,
        registered_at=row.registered_at,
        last_seen_at=row.last_seen_at,
        last_seq=row.last_seq,
        last_state=AlertState(row.last_state) if row.last_state else None,
    )


def apply_device(row: DeviceOrm, device: Device) -> DeviceOrm:
    row.hw_id = str(device.hw_id)
    row.label = device.label
    row.parking_slot = device.parking_slot
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
        channels=channels,
        temp_c=row.temp_c,
        humidity_pct=row.humidity_pct,
        pressure_hpa=row.pressure_hpa,
        water_level_mm=row.water_level_mm,
        rssi=row.rssi,
        snr=row.snr,
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
        "temp_c": reading.temp_c,
        "humidity_pct": reading.humidity_pct,
        "pressure_hpa": reading.pressure_hpa,
        "water_level_mm": reading.water_level_mm,
        "rssi": reading.rssi,
        "snr": reading.snr,
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
