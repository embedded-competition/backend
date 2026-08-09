"""기기 등록·인증 유스케이스. 조립만 한다 — 생성·정규화 규칙은 identity.py."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import identity
from app.domain.exceptions import DeviceAlreadyPaired, DeviceNotFound, Unauthorized
from app.domain.models import AccessToken, Device, PushToken
from app.domain.ports import Clock
from app.infrastructure.db.repositories import (
    SqlAlchemyAccessTokenRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemyPushTokenRepository,
)


@dataclass(frozen=True, slots=True)
class DeviceRegistration:
    """등록 결과. `token`은 이 순간에만 존재하고 어디에도 저장되지 않는다."""

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
        """MAC으로 기기를 등록하고 deviceToken을 발급한다.

        이미 등록된 MAC은 거절한다 — 앱 spec §② 409 already_paired.
        """
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
                device_id=device.id or 0,
                token_hash=identity.hash_token(token),
                created_at=now,
            )
        )
        return DeviceRegistration(device=device, token=token)

    def authenticate(self, token: str) -> Device:
        """Bearer 토큰 → 소유 기기. 실패 사유는 전부 unauthorized로 뭉갠다."""
        token_hash = identity.hash_token(token)
        device_id = self.access_tokens.find_device_id(token_hash)
        if device_id is None:
            raise Unauthorized("유효하지 않은 deviceToken")
        device = self.devices.get(device_id)
        if device is None:  # pragma: no cover - FK가 보장하지만 방어
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
        """멱등 — 같은 토큰 재등록이 중복 행을 만들지 않는다."""
        return self.push_tokens.upsert(
            PushToken(
                device_id=device.id or 0,
                token=token,
                platform=platform,
                registered_at=self.clock.now(),
            )
        )
