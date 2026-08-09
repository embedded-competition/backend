"""기기 저장소 + ORM↔domain 변환.

변환 함수는 비공개다 — 이 저장소 밖에서 쓰이면 ORM 타입이 계층을 넘는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.device import Device
from app.domain.value_objects import AlertState, DeviceId
from app.infrastructure.db.orm import DeviceOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyDeviceRepository:
    session: Session

    def get_by_hw_id(self, hw_id: DeviceId) -> Device | None:
        row = self.session.scalar(select(DeviceOrm).where(DeviceOrm.hw_id == str(hw_id)))
        return _to_domain(row) if row else None

    def get_by_mac(self, mac: str) -> Device | None:
        row = self.session.scalar(select(DeviceOrm).where(DeviceOrm.mac == mac))
        return _to_domain(row) if row else None

    def get_by_public_id(self, public_id: str) -> Device | None:
        row = self.session.scalar(select(DeviceOrm).where(DeviceOrm.public_id == public_id))
        return _to_domain(row) if row else None

    def get(self, device_id: int) -> Device | None:
        row = self.session.get(DeviceOrm, device_id)
        return _to_domain(row) if row else None

    def list_active(self) -> list[Device]:
        rows = self.session.scalars(
            select(DeviceOrm).where(DeviceOrm.is_active.is_(True)).order_by(DeviceOrm.id)
        )
        return [_to_domain(row) for row in rows]

    def save(self, device: Device) -> Device:
        row = self.session.get(DeviceOrm, device.id) if device.id else None
        if row is None:
            row = DeviceOrm()
            self.session.add(row)
        _apply(row, device)
        self.session.flush()
        return _to_domain(row)


def _to_domain(row: DeviceOrm) -> Device:
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


def _apply(row: DeviceOrm, device: Device) -> DeviceOrm:
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
