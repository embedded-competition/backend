"""식별자·토큰 생성과 정규화. 유스케이스를 모른다."""

from __future__ import annotations

import hashlib
import re
import secrets

from app.domain.exceptions import InvalidMac

_NON_HEX = re.compile(r"[^0-9A-Fa-f]")
_MAC_HEX_LENGTH = 12
_OCTET = 2
# S105 noqa 근거: 비밀값이 아니라 토큰 문자열의 종류 식별 prefix다.
_TOKEN_PREFIX = "dtk_"  # noqa: S105
_PUBLIC_ID_PREFIX = "dev_"


def normalize_mac(raw: str) -> str:
    """앱의 services/deviceRegistry.ts normalizeMac과 같은 형식으로 맞춘다."""
    cleaned = _NON_HEX.sub("", raw).upper()
    if len(cleaned) != _MAC_HEX_LENGTH:
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    return ":".join(cleaned[i : i + _OCTET] for i in range(0, _MAC_HEX_LENGTH, _OCTET))


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
