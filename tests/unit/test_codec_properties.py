"""와이어 포맷 속성 테스트.

무선 경로는 재현이 어렵다 — 예제 몇 개로는 오프셋·레벨·좌표 조합을 덮지 못한다.
"어떤 프레임이든" 성립해야 하는 성질을 직접 적는다.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.domain.exceptions import FrameCrcError, FrameError
from app.infrastructure.lora import codec
from app.infrastructure.lora.codec import FRAME_SIZE, LEVEL_MAX, LEVEL_MIN, WireFrame
from app.infrastructure.lora.frame import parse_frame, to_domain

_RECEIVED_AT = datetime(2026, 8, 13, 9, 0, 0, tzinfo=UTC)


def _levels() -> st.SearchStrategy[int]:
    return st.integers(min_value=LEVEL_MIN, max_value=LEVEL_MAX)


@st.composite
def wire_frames(draw: st.DrawFn) -> WireFrame:
    # 와이어가 float32라 float64 좌표는 애초에 왕복하지 않는다. width=32로 뽑는다.
    fix = draw(st.booleans())
    return WireFrame(
        mac_hex=draw(st.text(alphabet="0123456789abcdef", min_size=12, max_size=12)),
        mq7=draw(_levels()),
        mq8=draw(_levels()),
        pressure=draw(_levels()),
        water=draw(_levels()),
        voc=draw(_levels()),
        lat=draw(st.floats(min_value=-90, max_value=90, allow_nan=False, width=32))
        if fix
        else math.nan,
        lon=draw(st.floats(min_value=-180, max_value=180, allow_nan=False, width=32))
        if fix
        else math.nan,
    )


_SETTINGS = settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])


@_SETTINGS
@given(frame=wire_frames())
def test_encode_then_decode_returns_the_same_frame(frame: WireFrame) -> None:
    restored = codec.decode(codec.encode(frame))

    assert restored.has_fix is frame.has_fix
    if frame.has_fix:
        assert restored == frame
    else:
        # NaN != NaN이라 좌표를 뺀 나머지로 비교한다.
        assert (restored.mac_hex, restored.mq7, restored.mq8) == (
            frame.mac_hex,
            frame.mq7,
            frame.mq8,
        )
        assert (restored.pressure, restored.water, restored.voc) == (
            frame.pressure,
            frame.water,
            frame.voc,
        )


@_SETTINGS
@given(frame=wire_frames())
def test_encoded_length_is_always_the_same(frame: WireFrame) -> None:
    """길이 필드가 없다. 길이 자체가 포맷의 서명이다."""
    assert len(codec.encode(frame)) == FRAME_SIZE


@_SETTINGS
@given(frame=wire_frames())
def test_location_exists_only_with_a_fix(frame: WireFrame) -> None:
    assert (to_domain(frame, _RECEIVED_AT).location is not None) is frame.has_fix


@_SETTINGS
@given(frame=wire_frames(), index=st.integers(min_value=0), bit=st.integers(0, 7))
def test_single_bit_flip_is_rejected_by_crc(frame: WireFrame, index: int, bit: int) -> None:
    payload = bytearray(codec.encode(frame))
    payload[index % len(payload)] ^= 1 << bit
    with pytest.raises(FrameCrcError):
        parse_frame(bytes(payload), _RECEIVED_AT)


@_SETTINGS
@given(payload=st.binary(max_size=FRAME_SIZE * 2))
def test_arbitrary_bytes_raise_only_frame_error(payload: bytes) -> None:
    """수신 루프는 FrameError만 골라 센다. 다른 예외가 새면 통계가 거짓이 된다."""
    try:
        parse_frame(payload, _RECEIVED_AT)
    except FrameError:
        return
    except Exception as exc:  # 계약 위반을 드러내는 것이 목적이라 넓게 잡는다
        pytest.fail(f"FrameError가 아닌 예외가 샜다: {type(exc).__name__}: {exc}")
