from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from app.domain.exceptions import FrameCrcError, FrameFieldError, FrameTooShort
from app.infrastructure.lora.crc import crc16_ccitt

_BODY = "<6s5H2f"
_CRC = "<H"
_BODY_SIZE = struct.calcsize(_BODY)
_CRC_SIZE = struct.calcsize(_CRC)

FRAME_SIZE = _BODY_SIZE + _CRC_SIZE

LEVEL_MIN = 0
LEVEL_MAX = 1000

_LEVEL_FIELDS = ("mq7", "mq8", "pressure", "water", "voc")

# 노드가 GPS 미장착 상태에서 채우는 값. 좌표가 아니라 빈자리를 뜻한다.
_NO_FIX = (0.0, 0.0)


@dataclass(frozen=True, slots=True)
class WireFrame:
    """노드 어휘 그대로다. 도메인 이름으로 옮기는 일은 경계 한 곳에서만 한다.

    다섯 레벨은 모두 풀스케일 대비 0~1000 정규화 값이다. SGP40(`voc`)은 노드가 이미
    부호를 뒤집어 보내므로 다섯 채널 모두 "클수록 위험"이다.

    좌표가 없다는 표시는 NaN 또는 `(0, 0)`이다 — 아래 `has_fix`.
    """

    mac_hex: str
    mq7: int
    mq8: int
    pressure: int
    water: int
    voc: int
    lat: float
    lon: float

    def __post_init__(self) -> None:
        for name in _LEVEL_FIELDS:
            level = getattr(self, name)
            if not LEVEL_MIN <= level <= LEVEL_MAX:
                raise FrameFieldError(f"{name} 레벨이 0~1000 밖이다: {level}")

    @property
    def has_fix(self) -> bool:
        """`(0, 0)`도 측위 없음으로 본다 — 지금 노드가 GPS 자리에 0.0f를 채워 보낸다.

        그 좌표는 기니만 앞바다라 한국에서 운영하는 동안 진짜 판독일 수 없다. 대신
        정직한 대가를 치른다: 노드가 GPS를 달아도 적도·본초자오선 교점만은 영영
        보고하지 못한다.
        """
        if math.isnan(self.lat) or math.isnan(self.lon):
            return False
        return (self.lat, self.lon) != _NO_FIX


def decode(payload: bytes) -> WireFrame:
    if len(payload) != FRAME_SIZE:
        raise FrameTooShort(f"프레임이 {len(payload)}B, {FRAME_SIZE}B여야 한다")

    body, crc_bytes = payload[:_BODY_SIZE], payload[_BODY_SIZE:]
    (received_crc,) = struct.unpack(_CRC, crc_bytes)
    if crc16_ccitt(body) != received_crc:
        raise FrameCrcError(f"CRC 불일치: payload={payload.hex()}")

    mac, mq7, mq8, pressure, water, voc, lat, lon = struct.unpack(_BODY, body)
    return WireFrame(
        mac_hex=mac.hex(),
        mq7=mq7,
        mq8=mq8,
        pressure=pressure,
        water=water,
        voc=voc,
        lat=lat,
        lon=lon,
    )


def encode(frame: WireFrame) -> bytes:
    body = struct.pack(
        _BODY,
        bytes.fromhex(frame.mac_hex),
        frame.mq7,
        frame.mq8,
        frame.pressure,
        frame.water,
        frame.voc,
        frame.lat,
        frame.lon,
    )
    return body + struct.pack(_CRC, crc16_ccitt(body))
