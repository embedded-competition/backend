from __future__ import annotations

from dataclasses import dataclass

from app.core import identity
from app.domain.access import AccessToken
from app.domain.device import Device
from app.domain.exceptions import DeviceAlreadyPaired, DeviceNotFound, Unauthorized
from app.domain.ports.clock import Clock
from app.domain.push import PushToken
from app.infrastructure.db.repositories.access_tokens import SqlAlchemyAccessTokenRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository


@dataclass(frozen=True, slots=True)
class DeviceRegistration:
    device: Device
    token: str


@dataclass(frozen=True, slots=True)
class DeviceService:
    devices: SqlAlchemyDeviceRepository
    access_tokens: SqlAlchemyAccessTokenRepository
    push_tokens: SqlAlchemyPushTokenRepository
    clock: Clock
    default_management_phone: str | None = None

    def register(self, raw_mac: str) -> DeviceRegistration:
        mac = identity.normalize_mac(raw_mac)
        if self.devices.get_by_mac(mac) is not None:
            raise DeviceAlreadyPaired(f"이미 등록된 MAC: {mac}")

        now = self.clock.now()
        device = self.devices.save(
            Device(
                public_id=identity.new_public_id(),
                mac=mac,
                label=identity.default_label(mac),
                management_phone=self.default_management_phone,
                registered_at=now,
            )
        )
        token = identity.new_device_token()
        self.access_tokens.add(
            AccessToken(
                device_id=device.key,
                token_hash=identity.hash_token(token),
                created_at=now,
            )
        )
        return DeviceRegistration(device=device, token=token)

    def authenticate(self, token: str) -> Device:
        token_hash = identity.hash_token(token)
        device_id = self.access_tokens.find_device_id(token_hash)
        if device_id is None:
            raise Unauthorized("유효하지 않은 deviceToken")
        device = self.devices.get(device_id)
        if device is None:
            raise Unauthorized("토큰이 가리키는 기기가 없다")
        self.access_tokens.touch(token_hash, at=self.clock.now())
        return device

    def get_by_public_id(self, public_id: str) -> Device:
        device = self.devices.get_by_public_id(public_id)
        if device is None:
            raise DeviceNotFound(f"기기 없음: {public_id}")
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
