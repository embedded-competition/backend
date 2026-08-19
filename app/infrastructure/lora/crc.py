from __future__ import annotations

_POLY = 0x1021
_INIT = 0xFFFF


def crc16_ccitt(data: bytes) -> int:
    crc = _INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc
