"""CRC-16/CCITT-FALSE. 프레임 포맷과 무관한 순수 알고리즘."""

from __future__ import annotations

_POLY = 0x1021
_INIT = 0xFFFF


def crc16_ccitt(data: bytes) -> int:
    """poly 0x1021, init 0xFFFF, no reflect, xorout 0x0000."""
    crc = _INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc
