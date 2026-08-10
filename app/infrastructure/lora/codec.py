from __future__ import annotations

import struct
from dataclasses import dataclass

from app.domain import measurements
from app.domain.exceptions import FrameCrcError, FrameFieldError, FrameTooShort
from app.domain.measurements import Measure
from app.infrastructure.lora.crc import crc16_ccitt

FRAME_VERSION = 1

_HEADER = "<BB6sHIBH"
_HEADER_SIZE = struct.calcsize(_HEADER)
_HOLD_S = "<H"
_GPS = "<2f"
_CRC = "<H"

ABSENT = -32768
SCALED_MIN = -32767
SCALED_MAX = 32767
_SCALE = 100.0

FLAG_HAS_GPS = 1 << 0
FLAG_LATCHED = 1 << 1
FLAG_SIG_RISE = 1 << 2
FLAG_SIG_HOLD = 1 << 3
FLAG_SIG_NO_RECOVER = 1 << 4
FLAG_WATER = 1 << 5
FLAG_HAS_SIGNATURE = 1 << 6

MEASURE_ORDER = measurements.ORDER
_SCALED = f"<{len(MEASURE_ORDER)}h"
_SCALED_SIZE = struct.calcsize(_SCALED)

BASE_SIZE = _HEADER_SIZE + _SCALED_SIZE + 2 + 2
GPS_SIZE = BASE_SIZE + 8


@dataclass(frozen=True, slots=True)
class WireFrame:
    version: int
    flags: int
    hw_id_hex: str
    seq: int
    measured_epoch: int
    state_code: int
    batt_mv: int
    values: dict[Measure, float]
    hold_s: int
    lat: float | None
    lon: float | None

    def has(self, flag: int) -> bool:
        return bool(self.flags & flag)


def decode(payload: bytes) -> WireFrame:
    if len(payload) < BASE_SIZE:
        raise FrameTooShort(f"프레임이 {len(payload)}B, 최소 {BASE_SIZE}B 필요")

    flags = payload[1]
    expected = GPS_SIZE if flags & FLAG_HAS_GPS else BASE_SIZE
    if len(payload) != expected:
        raise FrameTooShort(f"길이 불일치: {len(payload)}B, flags 기준 {expected}B 기대")

    body, crc_bytes = payload[:-2], payload[-2:]
    (received_crc,) = struct.unpack(_CRC, crc_bytes)
    if crc16_ccitt(body) != received_crc:
        raise FrameCrcError(f"CRC 불일치: payload={payload.hex()}")

    version, flags, hw_id, seq, epoch, state_code, batt_mv = struct.unpack_from(_HEADER, body, 0)
    scaled = struct.unpack_from(_SCALED, body, _HEADER_SIZE)
    (hold_s,) = struct.unpack_from(_HOLD_S, body, _HEADER_SIZE + _SCALED_SIZE)

    lat = lon = None
    if flags & FLAG_HAS_GPS:
        lat, lon = struct.unpack_from(_GPS, body, _HEADER_SIZE + _SCALED_SIZE + 2)

    return WireFrame(
        version=version,
        flags=flags,
        hw_id_hex=hw_id.hex(),
        seq=seq,
        measured_epoch=epoch,
        state_code=state_code,
        batt_mv=batt_mv,
        values={
            measure: value
            for measure, raw in zip(MEASURE_ORDER, scaled, strict=True)
            if (value := unscale(raw)) is not None
        },
        hold_s=hold_s,
        lat=lat,
        lon=lon,
    )


def encode(frame: WireFrame) -> bytes:
    body = struct.pack(
        _HEADER,
        frame.version,
        frame.flags,
        bytes.fromhex(frame.hw_id_hex),
        frame.seq,
        frame.measured_epoch,
        frame.state_code,
        frame.batt_mv,
    )
    body += struct.pack(_SCALED, *(scale(frame.values.get(measure)) for measure in MEASURE_ORDER))
    body += struct.pack(_HOLD_S, frame.hold_s)
    if frame.has(FLAG_HAS_GPS):
        body += struct.pack(_GPS, frame.lat, frame.lon)
    return body + struct.pack(_CRC, crc16_ccitt(body))


def unscale(raw: int) -> float | None:
    return None if raw == ABSENT else raw / _SCALE


def scale(value: float | None) -> int:
    if value is None:
        return ABSENT
    scaled = round(value * _SCALE)
    if not SCALED_MIN <= scaled <= SCALED_MAX:
        raise FrameFieldError(f"스케일 후 int16 범위 초과: {value}")
    return scaled
