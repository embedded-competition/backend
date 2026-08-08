"""식별자·토큰 생성과 정규화. 유스케이스를 모른다."""

from __future__ import annotations

import hashlib
import re
import secrets

from app.domain.exceptions import InvalidMac

_MAC_PATTERN = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
_NON_HEX = re.compile(r"[^0-9A-Fa-f]")
_TOKEN_PREFIX = "dtk_"
_PUBLIC_ID_PREFIX = "dev_"


def normalize_mac(raw: str) -> str:
    """앱의 services/deviceRegistry.ts normalizeMac과 같은 형식으로 맞춘다."""
    cleaned = _NON_HEX.sub("", raw).upper()
    if len(cleaned) != 12:
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    mac = ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    if not _MAC_PATTERN.match(mac):
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    return mac


def hw_id_from_mac(mac: str) -> str:
    """노드가 프레임에 싣는 형태 — 구분자 없는 소문자 hex."""
    return mac.replace(":", "").lower()


def hash_token(token: str) -> str:
    """SHA-256. 원문은 저장하지 않는다 (db-schema.md D9)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_device_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(24)


def new_public_id() -> str:
    """순번을 노출하지 않는다 — /devices/1 순회를 막는다 (D8)."""
    return _PUBLIC_ID_PREFIX + secrets.token_hex(6)


def default_label(mac: str) -> str:
    return f"킥보드 {mac[-5:].replace(':', '')}"
