"""프레임 코덱 단위 테스트. 노드 펌웨어와 공유하는 계약이라 회귀가 치명적이다."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.exceptions import (
    FrameCrcError,
    FrameFieldError,
    FrameTooShort,
    UnsupportedFrameVersion,
)
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, GasChannel, SignatureFlags
from app.infrastructure.lora import codec
from app.infrastructure.lora.codec import BASE_SIZE, GPS_SIZE
from app.infrastructure.lora.crc import crc16_ccitt
from app.infrastructure.lora.frame import build_frame, parse_frame
from tests.builders import HW_ID, a_frame

NOW = datetime(2026, 8, 8, 12, 0, 0, tzinfo=UTC)


def _frame(**kwargs: Any) -> TelemetryFrame:
    """와이어 version은 코덱 계약이라 명시적으로 고정한다."""
    kwargs.setdefault("seq", 42)
    kwargs.setdefault("state", AlertState.WATCH)
    return a_frame(NOW, version=codec.FRAME_VERSION, **kwargs)


class TestCrc:
    def test_known_vector(self) -> None:
        """CRC-16/CCITT-FALSE 표준 검증 벡터."""
        assert crc16_ccitt(b"123456789") == 0x29B1

    def test_empty_returns_init(self) -> None:
        assert crc16_ccitt(b"") == 0xFFFF


class TestRoundTrip:
    def test_minimal_frame(self) -> None:
        original = _frame()

        restored = parse_frame(build_frame(original))

        assert restored.hw_id == HW_ID
        assert restored.seq == 42
        assert restored.state is AlertState.WATCH
        assert restored.measured_at == NOW

    def test_frame_without_gps_is_base_size(self) -> None:
        assert len(build_frame(_frame())) == BASE_SIZE

    def test_frame_with_gps_is_larger(self) -> None:
        payload = build_frame(_frame(location=Coordinates(lat=37.5573, lon=127.0329)))

        assert len(payload) == GPS_SIZE
        assert GPS_SIZE - BASE_SIZE == 8

    def test_channels_survive(self) -> None:
        original = _frame(
            values={
                Measure.VOC_DEV: 6.28,
                Measure.VOC_SLOPE: 7.15,
                Measure.H2_DEV: -1.5,
            }
        )

        restored = parse_frame(build_frame(original))

        voc = restored.channel(GasChannel.VOC)
        h2 = restored.channel(GasChannel.H2)
        assert voc is not None
        assert h2 is not None
        assert voc.deviation == pytest.approx(6.28)
        assert h2.slope is None
        # 미장착 채널은 아예 올라오지 않는다
        assert restored.channel(GasChannel.CO) is None

    def test_signature_absent_stays_none(self) -> None:
        """'전부 false'와 '안 보냄'을 구분해야 오경보 분석이 가능하다."""
        restored = parse_frame(build_frame(_frame(signature=None)))

        assert restored.signature is None

    def test_signature_all_false_is_not_none(self) -> None:
        original = _frame(
            signature=SignatureFlags(rise=False, hold=False, no_recover=False, hold_s=0)
        )

        restored = parse_frame(build_frame(original))

        assert restored.signature is not None
        assert restored.signature.rise is False
        assert restored.signature.hold is False
        assert restored.signature.no_recover is False

    def test_gps_precision_is_preserved_enough(self) -> None:
        original = _frame(location=Coordinates(lat=37.5573, lon=127.0329))

        restored = parse_frame(build_frame(original))

        assert restored.location is not None
        assert restored.location.lat == pytest.approx(37.5573, abs=1e-4)
        assert restored.location.lon == pytest.approx(127.0329, abs=1e-4)


class TestRejection:
    def test_short_payload(self) -> None:
        with pytest.raises(FrameTooShort):
            parse_frame(b"\x01\x00")

    def test_length_mismatch_with_gps_flag(self) -> None:
        payload = bytearray(build_frame(_frame()))
        payload[1] |= codec.FLAG_HAS_GPS  # GPS 있다고 주장하지만 길이가 안 맞음

        with pytest.raises(FrameTooShort):
            parse_frame(bytes(payload))

    def test_corrupted_byte_fails_crc(self) -> None:
        payload = bytearray(build_frame(_frame()))
        payload[10] ^= 0xFF

        with pytest.raises(FrameCrcError):
            parse_frame(bytes(payload))

    def test_unknown_version_is_rejected(self) -> None:
        payload = bytearray(build_frame(_frame()))
        payload[0] = 99
        payload[-2:] = crc16_ccitt(bytes(payload[:-2])).to_bytes(2, "little")

        with pytest.raises(UnsupportedFrameVersion):
            parse_frame(bytes(payload))

    def test_unknown_state_code_is_rejected(self) -> None:
        payload = bytearray(build_frame(_frame()))
        payload[14] = 9
        payload[-2:] = crc16_ccitt(bytes(payload[:-2])).to_bytes(2, "little")

        with pytest.raises(FrameFieldError):
            parse_frame(bytes(payload))

    def test_value_beyond_int16_scale_is_rejected(self) -> None:
        """±327.67을 넘는 z-score는 인코딩 불가 — 조용히 잘리지 않는다."""
        with pytest.raises(FrameFieldError):
            build_frame(_frame(values={Measure.VOC_DEV: 400.0}))

    def test_out_of_range_measure_is_rejected_on_parse(self) -> None:
        """범위는 measurements 표가 정한다 — 코덱이 따로 알지 않는다."""
        payload = bytearray(build_frame(_frame(values={Measure.HUMIDITY_PCT: 50.0})))
        slot = codec.MEASURE_ORDER.index(Measure.HUMIDITY_PCT)
        offset = 15 + slot * 2  # _HEADER_SIZE + 슬롯 오프셋
        payload[offset : offset + 2] = (200 * 100).to_bytes(2, "little", signed=True)
        payload[-2:] = crc16_ccitt(bytes(payload[:-2])).to_bytes(2, "little")

        with pytest.raises(FrameFieldError):
            parse_frame(bytes(payload))
