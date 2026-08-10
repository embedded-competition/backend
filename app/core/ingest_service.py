from __future__ import annotations

from dataclasses import dataclass

from app.core import identity
from app.core.descriptions import describe_transition
from app.domain.alerting import Alert, Event
from app.domain.device import Device
from app.domain.exceptions import DeviceInactive, DeviceNotRegistered
from app.domain.frames import TelemetryFrame
from app.domain.ports.clock import Clock
from app.domain.ports.frame_source import RawFrame
from app.domain.readings import RadioQuality, Reading
from app.domain.value_objects import DeviceId, EventKind
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    device: Device
    reading: Reading
    duplicate: bool
    missed_frames: int
    alert: Alert | None = None

    @property
    def needs_dispatch(self) -> bool:
        return self.alert is not None and self.alert.to_state.needs_dispatch


@dataclass(frozen=True, slots=True)
class IngestService:
    devices: SqlAlchemyDeviceRepository
    readings: SqlAlchemyReadingRepository
    alerts: SqlAlchemyAlertRepository
    events: SqlAlchemyEventRepository
    clock: Clock

    def ingest(self, frame: TelemetryFrame, raw: RawFrame) -> IngestOutcome:
        if frame.hw_id is None:
            raise DeviceNotRegistered("hw_id 없는 프레임은 소유 기기를 특정할 수 없다")
        device = self._resolve_device(frame.hw_id)
        received = _to_reading(device, frame, raw)

        stored = self.readings.add_if_absent(received)
        if stored is None:
            return IngestOutcome(device=device, reading=received, duplicate=True, missed_frames=0)

        missed = device.missed_frames_since(frame.seq)
        alert = self._record_transition(device, frame, stored)
        device.observe(seq=frame.seq, at=frame.measured_at, state=frame.state)
        device.frame_version = frame.version
        self.devices.save(device)

        return IngestOutcome(
            device=device,
            reading=stored,
            duplicate=False,
            missed_frames=missed,
            alert=alert,
        )

    def _resolve_device(self, hw_id: DeviceId) -> Device:
        device = self.devices.get_by_hw_id(hw_id)
        if device is None:
            device = self.devices.get_by_mac(_mac_from_hw_id(str(hw_id)))
            if device is None:
                raise DeviceNotRegistered(f"미등록 노드: {hw_id}")
            device.hw_id = hw_id
            device = self.devices.save(device)
        if not device.is_active:
            raise DeviceInactive(f"비활성 기기: {device.public_id}")
        return device

    def _record_transition(
        self, device: Device, frame: TelemetryFrame, reading: Reading
    ) -> Alert | None:
        previous = device.last_state
        if previous is None or previous is frame.state:
            return None

        alert = self.alerts.add(
            Alert(
                device_id=device.key,
                reading_id=reading.key,
                from_state=previous,
                to_state=frame.state,
                occurred_at=frame.measured_at,
                detected_at=self.clock.now(),
            )
        )
        self.events.add(
            Event(
                device_id=device.key,
                alert_id=alert.key,
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
        device_id=device.key,
        frame=frame,
        received_at=raw.received_at,
        radio=RadioQuality(rssi=raw.rssi, snr=raw.snr),
    )
