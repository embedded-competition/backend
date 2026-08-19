from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from app.domain.exceptions import FrameError
from app.infrastructure.lora.rylr.config import PayloadEncoding

RECEIVE_PREFIX = "+RCV="
_FIELDS_AFTER_PAYLOAD = 2
_TEXT_ENCODINGS = ("text", "node_csv")
_URLSAFE_TO_STANDARD = str.maketrans("-_", "+/")
_STANDARD_ONLY = "+/"
_BASE64_GROUP = 4


@dataclass(frozen=True, slots=True)
class ReceivedPacket:
    address: int
    payload: bytes
    rssi: int | None = None
    snr: float | None = None


def parse_packet(line: str, encoding: PayloadEncoding) -> ReceivedPacket:
    body = line[len(RECEIVE_PREFIX) :]
    head, _, rest = body.partition(",")
    length_text, _, rest = rest.partition(",")
    address, length = _numbers(head, length_text, line)

    data = rest[:length]
    tail = rest[length + 1 :].split(",")
    if len(data) != length or len(tail) != _FIELDS_AFTER_PAYLOAD:
        raise FrameError(f"+RCV 형식이 아니다: {line!r}")

    return ReceivedPacket(
        address=address,
        payload=_decode(data, encoding, line),
        rssi=_optional_int(tail[0]),
        snr=_optional_float(tail[1]),
    )


def _numbers(address_text: str, length_text: str, line: str) -> tuple[int, int]:
    try:
        return int(address_text), int(length_text)
    except ValueError as exc:
        raise FrameError(f"+RCV 헤더를 읽을 수 없다: {line!r}") from exc


def _decode(data: str, encoding: PayloadEncoding, line: str) -> bytes:
    if encoding in _TEXT_ENCODINGS:
        return data.encode()
    if encoding == "base64url":
        return _from_base64url(data, line)
    try:
        return bytes.fromhex(data)
    except ValueError as exc:
        raise FrameError(f"hex 페이로드가 아니다: {line!r}") from exc


def _from_base64url(data: str, line: str) -> bytes:
    """노드는 패딩을 떼고 보낸다. 길이는 프레임 자신이 안다."""
    if any(char in data for char in _STANDARD_ONLY):
        raise FrameError(f"base64url이 아니라 표준 base64다: {line!r}")
    padding = "=" * (-len(data) % _BASE64_GROUP)
    try:
        return base64.b64decode(data.translate(_URLSAFE_TO_STANDARD) + padding, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FrameError(f"base64url 페이로드가 아니다: {line!r}") from exc


def _optional_int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def _optional_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None
