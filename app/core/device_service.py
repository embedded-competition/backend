"""기기 등록·인증 유스케이스. fastapi·sqlalchemy import 0."""

from __future__ import annotations

import hashlib
import re
import secrets

from app.domain.exceptions import (
    DeviceAlreadyPaired,
    DeviceNotFound,
    InvalidMac,
    Unauthorized,
)
from app.domain.models import AccessToken, Device, PushToken
from app.domain.ports import Clock
from app.domain.repository import (
    AccessTokenRepository,
    DeviceRepository,
    PushTokenRepository,
)

_MAC_PATTERN = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
_TOKEN_PREFIX = "dtk_"
_PUBLIC_ID_PREFIX = "dev_"


def normalize_mac(raw: str) -> str:
    """앱의 services/deviceRegistry.ts normalizeMac과 같은 형식으로 맞춘다."""
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", raw).upper()
    if len(cleaned) != 12:
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    mac = ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    if not _MAC_PATTERN.match(mac):
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    return mac


def hash_token(token: str) -> str:
    """SHA-256. 원문은 저장하지 않는다 (db-schema.md D9)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class DeviceRegistration:
    """등록 결과. `token`은 이 순간에만 존재하고 어디에도 저장되지 않는다."""

    __slots__ = ("device", "token")

    def __init__(self, device: Device, token: str) -> None:
        self.device = device
        self.token = token


class DeviceService:
    def __init__(
        self,
        *,
        devices: DeviceRepository,
        access_tokens: AccessTokenRepository,
        push_tokens: PushTokenRepository,
        clock: Clock,
        default_management_phone: str | None = None,
    ) -> None:
        self._devices = devices
        self._access_tokens = access_tokens
        self._push_tokens = push_tokens
        self._clock = clock
        self._default_management_phone = default_management_phone

    def register(self, raw_mac: str) -> DeviceRegistration:
        """MAC으로 기기를 등록하고 deviceToken을 발급한다.

        이미 등록된 MAC은 거절한다 — 앱 spec §② 409 already_paired.
        재발급이 필요하면 별도 흐름으로 다룬다(지금은 없음).
        """
        mac = normalize_mac(raw_mac)
        if self._devices.get_by_mac(mac) is not None:
            raise DeviceAlreadyPaired(f"이미 등록된 MAC: {mac}")

        now = self._clock.now()
        device = self._devices.save(
            Device(
                public_id=_PUBLIC_ID_PREFIX + secrets.token_hex(6),
                mac=mac,
                label=f"킥보드 {mac[-5:].replace(':', '')}",
                management_phone=self._default_management_phone,
                registered_at=now,
            )
        )
        token = _TOKEN_PREFIX + secrets.token_urlsafe(24)
        self._access_tokens.add(
            AccessToken(device_id=device.id or 0, token_hash=hash_token(token), created_at=now)
        )
        return DeviceRegistration(device=device, token=token)

    def authenticate(self, token: str) -> Device:
        """Bearer 토큰 → 소유 기기. 실패는 전부 unauthorized로 뭉갠다."""
        device_id = self._access_tokens.find_device_id(hash_token(token))
        if device_id is None:
            raise Unauthorized("유효하지 않은 deviceToken")
        device = self._devices.get(device_id)
        if device is None:  # pragma: no cover - FK가 보장하지만 방어
            raise Unauthorized("토큰이 가리키는 기기가 없다")
        self._access_tokens.touch(hash_token(token), at=self._clock.now())
        return device

    def get_by_public_id(self, public_id: str) -> Device:
        device = self._devices.get_by_public_id(public_id)
        if device is None:
            raise DeviceNotFound(f"기기 없음: {public_id}")
        return device

    def register_push_token(
        self, device: Device, token: str, platform: str | None = None
    ) -> PushToken:
        """멱등 — 같은 토큰 재등록이 중복 행을 만들지 않는다."""
        return self._push_tokens.upsert(
            PushToken(
                device_id=device.id or 0,
                token=token,
                platform=platform,
                registered_at=self._clock.now(),
            )
        )
