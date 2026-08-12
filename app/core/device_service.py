from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core import identity
from app.core.device_profile import DeviceProfile
from app.domain.device import Device
from app.domain.exceptions import DeviceNotFound
from app.domain.module_health import LinkQuality, SensorCheck
from app.domain.ports.clock import Clock
from app.domain.push import PushToken
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository


@dataclass(frozen=True, slots=True)
class DeviceService:
    devices: SqlAlchemyDeviceRepository
    push_tokens: SqlAlchemyPushTokenRepository
    readings: SqlAlchemyReadingRepository
    clock: Clock
    offline_after_s: int

    def profile(self, device: Device) -> DeviceProfile:
        reading = self.readings.latest(device.key)
        return DeviceProfile(
            mac=device.mac,
            label=device.label,
            parking_slot=device.parking_slot,
            battery=None,
            link=LinkQuality.of(
                rssi=reading.radio.rssi if reading else None,
                last_seen_at=device.last_seen_at,
                now=self.clock.now(),
                offline_after=timedelta(seconds=self.offline_after_s),
            ),
            sensor_check=SensorCheck.of(reading.conditions if reading else None),
            last_seen_at=device.last_seen_at,
        )

    def get_by_mac(self, raw_mac: str) -> Device:
        mac = identity.normalize_mac(raw_mac)
        device = self.devices.get_by_mac(mac)
        if device is None:
            raise DeviceNotFound(f"기기 없음: {mac}")
        return device

    def register_push_token(
        self, device: Device, token: str, platform: str | None = None
    ) -> PushToken:
        return self.push_tokens.upsert(
            PushToken(
                device_id=device.key,
                token=token,
                platform=platform,
                registered_at=self.clock.now(),
            )
        )
