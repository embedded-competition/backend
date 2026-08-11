from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions import FrameError
from app.infrastructure.lora.rylr.config import PayloadEncoding

RECEIVE_PREFIX = "+RCV="
_FIELDS_AFTER_PAYLOAD = 2


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
    if encoding in ("text", "node_csv"):
        return data.encode()
    try:
        return bytes.fromhex(data)
    except ValueError as exc:
        raise FrameError(f"hex 페이로드가 아니다: {line!r}") from exc


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
