"""프레임 1건 처리 유스케이스.

수신 → 기기 확인 → 멱등 저장 → 전이 감지 → 알람·이벤트 기록.
푸시 발송은 **하지 않는다** — 커밋 이후에 보내야 하므로 호출자에게 넘긴다
(conventions/backend/architecture/service.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core import identity
from app.core.descriptions import describe_transition
from app.domain.exceptions import DeviceInactive, DeviceNotRegistered
from app.domain.frames import TelemetryFrame
from app.domain.models import Alert, Device, Event, Reading
from app.domain.ports import Clock, RawFrame
from app.domain.repository import (
    AlertRepository,
    DeviceRepository,
    EventRepository,
    ReadingRepository,
)
from app.domain.value_objects import DeviceId, EventKind


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    """처리 결과. `alert`가 있으면 호출자가 커밋 후 푸시를 보낸다."""

    device: Device
    reading: Reading
    duplicate: bool
    missed_frames: int
    alert: Alert | None = None

    @property
    def needs_dispatch(self) -> bool:
        return self.alert is not None and self.alert.to_state.needs_dispatch


class IngestService:
    def __init__(
        self,
        *,
        devices: DeviceRepository,
        readings: ReadingRepository,
        alerts: AlertRepository,
        events: EventRepository,
        clock: Clock,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._alerts = alerts
        self._events = events
        self._clock = clock

    def ingest(self, frame: TelemetryFrame, raw: RawFrame) -> IngestOutcome:
        device = self._resolve_device(frame.hw_id)
        reading = _to_reading(device, frame, raw)

        stored = self._readings.add_if_absent(reading)
        if not stored:
            # LoRa 재전송. 중복은 정상 동작이므로 예외로 다루지 않는다.
            return IngestOutcome(device=device, reading=reading, duplicate=True, missed_frames=0)

        missed = device.missed_frames_since(frame.seq)
        alert = self._record_transition(device, frame, reading)
        device.observe(seq=frame.seq, at=frame.measured_at, state=frame.state)
        device.frame_version = frame.version
        self._devices.save(device)

        return IngestOutcome(
            device=device,
            reading=reading,
            duplicate=False,
            missed_frames=missed,
            alert=alert,
        )

    def _resolve_device(self, hw_id: DeviceId) -> Device:
        """미등록 노드는 자동 등록하지 않는다 — 무선은 위조 가능한 경로다.

        앱이 MAC으로 먼저 등록하므로, 첫 프레임에서 MAC↔hw_id를 연결해준다.
        """
        device = self._devices.get_by_hw_id(hw_id)
        if device is None:
            device = self._devices.get_by_mac(_mac_from_hw_id(str(hw_id)))
            if device is None:
                raise DeviceNotRegistered(f"미등록 노드: {hw_id}")
            device.hw_id = hw_id
            device = self._devices.save(device)
        if not device.is_active:
            raise DeviceInactive(f"비활성 기기: {device.public_id}")
        return device

    def _record_transition(
        self, device: Device, frame: TelemetryFrame, reading: Reading
    ) -> Alert | None:
        """상태가 그대로면 알람을 만들지 않는다 — heartbeat마다 통지가 나간다."""
        previous = device.last_state
        if previous is None or previous is frame.state:
            return None

        alert = self._alerts.add(
            Alert(
                device_id=device.id or 0,
                reading_id=reading.id,
                from_state=previous,
                to_state=frame.state,
                occurred_at=frame.measured_at,
                detected_at=self._clock.now(),
            )
        )
        self._events.add(
            Event(
                device_id=device.id or 0,
                alert_id=alert.id,
                kind=EventKind.STATE_CHANGE,
                occurred_at=frame.measured_at,
                description=describe_transition(previous, frame.state),
            )
        )
        return alert


def _mac_from_hw_id(hw_id_hex: str) -> str:
    return identity.normalize_mac(hw_id_hex)


def _to_reading(device: Device, frame: TelemetryFrame, raw: RawFrame) -> Reading:
    return Reading(
        device_id=device.id or 0,
        seq=frame.seq,
        measured_at=frame.measured_at,
        received_at=raw.received_at,
        frame_version=frame.version,
        state=frame.state,
        latched=frame.latched,
        channels=frame.channels,
        signature=frame.signature,
        temp_c=frame.temp_c,
        humidity_pct=frame.humidity_pct,
        d_rh_dt=frame.d_rh_dt,
        pressure_dev=frame.pressure_dev,
        pressure_rate=frame.pressure_rate,
        water=frame.water,
        batt_mv=frame.batt_mv,
        lat=frame.lat,
        lon=frame.lon,
        rssi=raw.rssi,
        snr=raw.snr,
    )
