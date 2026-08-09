"""와이어 포맷 속성 테스트.

무선 경로는 재현이 어렵다 — 예제 몇 개로는 오프셋·스케일·플래그 조합을 덮지
못한다. "어떤 프레임이든" 성립해야 하는 성질을 직접 적는다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.domain.exceptions import FrameCrcError, FrameError
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import SPECS, Measure
from app.domain.value_objects import AlertState, DeviceId, SignatureFlags
from app.infrastructure.lora.codec import BASE_SIZE, FRAME_VERSION, SCALED_MAX, SCALED_MIN
from app.infrastructure.lora.frame import build_frame, parse_frame

_UINT16_MAX = 65_535
_UINT32_MAX = 4_294_967_295
_SCALE = 100
_FLAGS_INDEX = 1


def _measure_values(measure: Measure) -> st.SearchStrategy[float]:
    """int16 스케일 범위와 항목별 물리 범위를 동시에 만족하는 값."""
    spec = SPECS[measure]
    low = SCALED_MIN if spec.minimum is None else max(SCALED_MIN, round(spec.minimum * _SCALE))
    high = SCALED_MAX if spec.maximum is None else min(SCALED_MAX, round(spec.maximum * _SCALE))
    return st.integers(min_value=low, max_value=high).map(lambda raw: raw / _SCALE)


@st.composite
def _values(draw: st.DrawFn) -> dict[Measure, float]:
    """결측은 키 자체가 없다 — 부분 집합을 뽑는다."""
    chosen = draw(st.lists(st.sampled_from(list(Measure)), unique=True))
    return {measure: draw(_measure_values(measure)) for measure in chosen}


@st.composite
def _signatures(draw: st.DrawFn) -> SignatureFlags:
    return SignatureFlags(
        rise=draw(st.booleans()),
        hold=draw(st.booleans()),
        no_recover=draw(st.booleans()),
        hold_s=draw(st.integers(min_value=0, max_value=_UINT16_MAX)),
    )


@st.composite
def _coordinates(draw: st.DrawFn) -> Coordinates:
    # 와이어가 float32라 float64 값은 애초에 왕복하지 않는다. width=32로 뽑는다.
    return Coordinates(
        lat=draw(st.floats(min_value=-90, max_value=90, allow_nan=False, width=32)),
        lon=draw(st.floats(min_value=-180, max_value=180, allow_nan=False, width=32)),
    )


@st.composite
def telemetry_frames(draw: st.DrawFn) -> TelemetryFrame:
    return TelemetryFrame(
        version=FRAME_VERSION,
        hw_id=DeviceId(draw(st.text(alphabet="0123456789abcdef", min_size=12, max_size=12))),
        seq=draw(st.integers(min_value=0, max_value=_UINT16_MAX)),
        measured_at=datetime.fromtimestamp(
            draw(st.integers(min_value=0, max_value=_UINT32_MAX)), tz=UTC
        ),
        state=draw(st.sampled_from(list(AlertState))),
        latched=draw(st.booleans()),
        values=draw(_values()),
        signature=draw(st.none() | _signatures()),
        # 0은 "미보고"로 인코딩된다 — 왕복 대상이 아니다.
        batt_mv=draw(st.none() | st.integers(min_value=1, max_value=_UINT16_MAX)),
        water=draw(st.booleans()),
        location=draw(st.none() | _coordinates()),
    )


_SETTINGS = settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])


@_SETTINGS
@given(frame=telemetry_frames())
def test_encode_then_decode_returns_the_same_frame(frame: TelemetryFrame) -> None:
    assert parse_frame(build_frame(frame)) == frame


@_SETTINGS
@given(frame=telemetry_frames())
def test_encoded_length_is_determined_by_gps_flag(frame: TelemetryFrame) -> None:
    payload = build_frame(frame)
    expected = BASE_SIZE + (8 if frame.location is not None else 0)
    assert len(payload) == expected


@_SETTINGS
@given(frame=telemetry_frames(), index=st.integers(min_value=0), bit=st.integers(0, 7))
def test_single_bit_flip_is_rejected_by_crc(frame: TelemetryFrame, index: int, bit: int) -> None:
    payload = bytearray(build_frame(frame))
    position = index % len(payload)
    # flags 바이트는 기대 길이를 바꾸므로 CRC보다 길이 검사가 먼저 걸린다.
    assume(position != _FLAGS_INDEX)
    payload[position] ^= 1 << bit
    with pytest.raises(FrameCrcError):
        parse_frame(bytes(payload))


@_SETTINGS
@given(payload=st.binary(max_size=BASE_SIZE * 2))
def test_arbitrary_bytes_raise_only_frame_error(payload: bytes) -> None:
    """수신 루프는 FrameError만 골라 센다. 다른 예외가 새면 통계가 거짓이 된다."""
    try:
        parse_frame(payload)
    except FrameError:
        return
    except Exception as exc:  # 계약 위반을 드러내는 것이 목적이라 넓게 잡는다
        pytest.fail(f"FrameError가 아닌 예외가 샜다: {type(exc).__name__}: {exc}")
