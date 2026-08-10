from __future__ import annotations

import hashlib
import re
import secrets

from app.domain.exceptions import InvalidMac

_NON_HEX = re.compile(r"[^0-9A-Fa-f]")
_MAC_HEX_LENGTH = 12
_OCTET = 2
_TOKEN_PREFIX = "dtk_"
_PUBLIC_ID_PREFIX = "dev_"


def normalize_mac(raw: str) -> str:
    cleaned = _NON_HEX.sub("", raw).upper()
    if len(cleaned) != _MAC_HEX_LENGTH:
        raise InvalidMac(f"MAC 형식이 아니다: {raw!r}")
    return ":".join(cleaned[i : i + _OCTET] for i in range(0, _MAC_HEX_LENGTH, _OCTET))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_device_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(24)


def new_public_id() -> str:
    return _PUBLIC_ID_PREFIX + secrets.token_hex(6)


def default_label(mac: str) -> str:
    return f"킥보드 {mac[-5:].replace(':', '')}"
