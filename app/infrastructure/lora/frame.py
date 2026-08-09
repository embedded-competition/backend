"""원시 필드 ↔ domain 변환.

와이어 포맷(오프셋·스케일·CRC)은 codec.py가, 이 모듈은 의미 해석만 담당한다.
센서 값은 measurements dict로 통째 넘어가므로 항목별 대입이 없다.
파서는 순수 함수다 — DB·로그·네트워크 접근 없음.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.exceptions import FrameFieldError, UnsupportedFrameVersion
from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.value_objects import AlertState, DeviceId, SignatureFlags
from app.infrastructure.lora import codec
from app.infrastructure.lora.codec import FRAME_VERSION, WireFrame

_STATE_BY_CODE = {
    0: AlertState.WARMUP,
    1: AlertState.NORMAL,
    2: AlertState.WATCH,
    3: AlertState.ALARM,
    4: AlertState.FAULT,
}
_CODE_BY_STATE = {state: code for code, state in _STATE_BY_CODE.items()}


def parse_frame(payload: bytes) -> TelemetryFrame:
    return to_domain(codec.decode(payload))


def build_frame(frame: TelemetryFrame) -> bytes:
    return codec.encode(to_wire(frame))


def to_domain(wire: WireFrame) -> TelemetryFrame:
    if wire.version != FRAME_VERSION:
        raise UnsupportedFrameVersion(f"지원하지 않는 프레임 version: {wire.version}")

    state = _STATE_BY_CODE.get(wire.state_code)
    if state is None:
        raise FrameFieldError(f"알 수 없는 state 코드: {wire.state_code}")

    try:
        return TelemetryFrame(
            version=wire.version,
            hw_id=DeviceId(wire.hw_id_hex),
            seq=wire.seq,
            measured_at=datetime.fromtimestamp(wire.measured_epoch, tz=UTC),
            state=state,
            latched=wire.has(codec.FLAG_LATCHED),
            values=wire.values,
            signature=_signature_of(wire),
            batt_mv=wire.batt_mv or None,
            water=wire.has(codec.FLAG_WATER),
            location=_location_of(wire),
        )
    except ValueError as exc:
        # 도메인 범위 검증 실패를 프레임 오류로 승격 — 수신 루프가 구분해 센다.
        raise FrameFieldError(str(exc)) from exc


def to_wire(frame: TelemetryFrame) -> WireFrame:
    return WireFrame(
        version=frame.version,
        flags=_flags_of(frame),
        hw_id_hex=str(frame.hw_id),
        seq=frame.seq,
        measured_epoch=int(frame.measured_at.timestamp()),
        state_code=_CODE_BY_STATE[frame.state],
        batt_mv=frame.batt_mv or 0,
        values=frame.values,
        hold_s=frame.signature.hold_s if frame.signature else 0,
        lat=frame.location.lat if frame.location else None,
        lon=frame.location.lon if frame.location else None,
    )


def _location_of(wire: WireFrame) -> Coordinates | None:
    if wire.lat is None or wire.lon is None:
        return None
    return Coordinates(lat=wire.lat, lon=wire.lon)


def _signature_of(wire: WireFrame) -> SignatureFlags | None:
    """`has_signature`가 0이면 None — '전부 false'와 '안 보냄'은 다르다."""
    if not wire.has(codec.FLAG_HAS_SIGNATURE):
        return None
    return SignatureFlags(
        rise=wire.has(codec.FLAG_SIG_RISE),
        hold=wire.has(codec.FLAG_SIG_HOLD),
        no_recover=wire.has(codec.FLAG_SIG_NO_RECOVER),
        hold_s=wire.hold_s,
    )


def _flags_of(frame: TelemetryFrame) -> int:
    flags = 0
    if frame.location is not None:
        flags |= codec.FLAG_HAS_GPS
    if frame.latched:
        flags |= codec.FLAG_LATCHED
    if frame.water:
        flags |= codec.FLAG_WATER
    if frame.signature is not None:
        flags |= codec.FLAG_HAS_SIGNATURE
        if frame.signature.rise:
            flags |= codec.FLAG_SIG_RISE
        if frame.signature.hold:
            flags |= codec.FLAG_SIG_HOLD
        if frame.signature.no_recover:
            flags |= codec.FLAG_SIG_NO_RECOVER
    return flags
