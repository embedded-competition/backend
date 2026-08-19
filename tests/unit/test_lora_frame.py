"""프레임 코덱 단위 테스트. 노드 펌웨어와 공유하는 계약이라 회귀가 치명적이다."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from app.domain.exceptions import FrameCrcError, FrameFieldError, FrameTooShort
from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState
from app.infrastructure.lora import codec
from app.infrastructure.lora.codec import FRAME_SIZE, WireFrame
from app.infrastructure.lora.crc import crc16_ccitt
from app.infrastructure.lora.frame import ABSENT_SEQ, build_frame, parse_frame, to_domain
from tests.builders import a_frame

RECEIVED_AT = datetime(2026, 8, 13, 9, 0, 0, tzinfo=UTC)
MAC_HEX = "a4cf12345678"

_MQ7_OFFSET = 6
_SEOUL = Coordinates(lat=37.5573, lon=127.0329)


def _wire(**overrides: object) -> WireFrame:
    fields: dict[str, object] = {
        "mac_hex": MAC_HEX,
        "mq7": 80,
        "mq8": 90,
        "pressure": 110,
        "water": 30,
        "voc": 120,
        "lat": math.nan,
        "lon": math.nan,
    }
    fields.update(overrides)
    return WireFrame(**fields)  # type: ignore[arg-type]


def _resealed(payload: bytearray) -> bytes:
    """본문을 건드린 뒤 CRC를 다시 씌운다 — CRC가 아니라 다음 검사를 시험하려는 것."""
    payload[-2:] = crc16_ccitt(bytes(payload[:-2])).to_bytes(2, "little")
    return bytes(payload)


class TestCrc:
    def test_known_vector(self) -> None:
        """CRC-16/CCITT-FALSE 표준 검증 벡터."""
        assert crc16_ccitt(b"123456789") == 0x29B1

    def test_empty_returns_init(self) -> None:
        assert crc16_ccitt(b"") == 0xFFFF


class TestWire:
    def test_frame_is_twenty_six_bytes(self) -> None:
        """표가 약속한 26B. 늘어나면 전파 시간과 듀티가 함께 늘어난다."""
        assert len(codec.encode(_wire())) == FRAME_SIZE
        assert FRAME_SIZE == 26

    def test_round_trip_keeps_every_level(self) -> None:
        original = _wire(mq7=1000, mq8=0, pressure=555, water=1, voc=999, lat=0.0, lon=0.0)

        assert codec.decode(codec.encode(original)) == original

    def test_round_trip_keeps_coordinates(self) -> None:
        restored = codec.decode(codec.encode(_wire(lat=37.5573, lon=127.0329)))

        assert restored.lat == pytest.approx(37.5573, abs=1e-4)
        assert restored.lon == pytest.approx(127.0329, abs=1e-4)

    def test_level_beyond_scale_is_rejected(self) -> None:
        """노드는 0~1000으로 clamp해 보낸다. 넘어오면 계약이 깨진 것이다."""
        with pytest.raises(FrameFieldError):
            _wire(mq7=1001)

    def test_negative_level_is_rejected(self) -> None:
        with pytest.raises(FrameFieldError):
            _wire(voc=-1)


class TestRejection:
    def test_short_payload(self) -> None:
        with pytest.raises(FrameTooShort):
            parse_frame(b"\x00\x01", RECEIVED_AT)

    def test_long_payload(self) -> None:
        """길이가 고정이라 남는 바이트는 다른 포맷이라는 뜻이다."""
        with pytest.raises(FrameTooShort):
            parse_frame(codec.encode(_wire()) + b"\x00", RECEIVED_AT)

    def test_corrupted_byte_fails_crc(self) -> None:
        payload = bytearray(codec.encode(_wire()))
        payload[8] ^= 0xFF

        with pytest.raises(FrameCrcError):
            parse_frame(bytes(payload), RECEIVED_AT)

    def test_level_beyond_scale_is_rejected_on_parse(self) -> None:
        payload = bytearray(codec.encode(_wire()))
        payload[_MQ7_OFFSET : _MQ7_OFFSET + 2] = (1001).to_bytes(2, "little")

        with pytest.raises(FrameFieldError):
            parse_frame(_resealed(payload), RECEIVED_AT)


class TestDomainMapping:
    def test_levels_land_on_their_channels(self) -> None:
        frame = to_domain(_wire(mq7=80, mq8=90, pressure=110, water=30, voc=120), RECEIVED_AT)

        assert frame.value(Measure.CO_DEV) == 80
        assert frame.value(Measure.H2_DEV) == 90
        assert frame.value(Measure.PRESSURE_DEV) == 110
        assert frame.value(Measure.WATER_LEVEL) == 30
        assert frame.value(Measure.VOC_DEV) == 120

    def test_measured_at_is_receive_time(self) -> None:
        """노드에 시계가 없다. 서버가 수신 시각을 찍는다."""
        assert to_domain(_wire(), RECEIVED_AT).measured_at == RECEIVED_AT

    def test_seq_is_not_invented(self) -> None:
        """노드가 seq를 안 보낸다. 카운터를 지어내면 유실 통계가 거짓이 된다."""
        assert to_domain(_wire(), RECEIVED_AT).seq == ABSENT_SEQ

    def test_state_is_normal_because_the_node_sends_no_verdict(self) -> None:
        """프레임에 판정이 없다. 값만으로 위험을 단정하지 않는다."""
        assert to_domain(_wire(mq7=1000, voc=1000), RECEIVED_AT).state is AlertState.NORMAL

    def test_nan_fix_is_no_location(self) -> None:
        assert to_domain(_wire(lat=math.nan, lon=math.nan), RECEIVED_AT).location is None

    def test_fix_becomes_coordinates(self) -> None:
        location = to_domain(_wire(lat=37.5573, lon=127.0329), RECEIVED_AT).location

        assert location is not None
        assert location.lat == pytest.approx(37.5573, abs=1e-4)

    def test_domain_frame_survives_the_wire(self) -> None:
        original = a_frame(
            RECEIVED_AT,
            values={
                Measure.CO_DEV: 80.0,
                Measure.H2_DEV: 90.0,
                Measure.PRESSURE_DEV: 110.0,
                Measure.WATER_LEVEL: 30.0,
                Measure.VOC_DEV: 120.0,
            },
            location=_SEOUL,
        )

        restored = parse_frame(build_frame(original), RECEIVED_AT)

        assert restored.values == original.values
        assert restored.location is not None

    def test_zero_coordinates_are_no_location(self) -> None:
        """노드가 GPS 미장착 자리에 0.0f를 채운다 — 좌표로 믿으면 모든 킥보드가
        기니만 앞바다에 찍힌다."""
        assert to_domain(_wire(lat=0.0, lon=0.0), RECEIVED_AT).location is None
