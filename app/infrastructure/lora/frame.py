"""원시 필드 ↔ domain 변환.

와이어 포맷(오프셋·스케일·CRC)은 codec.py가, 이 모듈은 의미 해석만 담당한다.
파서는 순수 함수다 — DB·로그·네트워크 접근 없음.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.exceptions import FrameFieldError, UnsupportedFrameVersion
from app.domain.frames import TelemetryFrame
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    GasChannel,
    SignatureFlags,
)
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

_CHANNEL_SLOTS = (
    (GasChannel.VOC, codec.VOC_DEV, codec.VOC_SLOPE),
    (GasChannel.H2, codec.H2_DEV, codec.H2_SLOPE),
    (GasChannel.CO, codec.CO_DEV, codec.CO_SLOPE),
)


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

    if wire.lat is not None and wire.lon is not None:  # noqa: SIM102 - 조건 의미가 다름
        if not -90.0 <= wire.lat <= 90.0 or not -180.0 <= wire.lon <= 180.0:
            raise FrameFieldError(f"좌표 범위 이탈: lat={wire.lat}, lon={wire.lon}")

    return TelemetryFrame(
        version=wire.version,
        hw_id=DeviceId(wire.hw_id_hex),
        seq=wire.seq,
        measured_at=datetime.fromtimestamp(wire.measured_epoch, tz=UTC),
        state=state,
        latched=wire.has(codec.FLAG_LATCHED),
        batt_mv=wire.batt_mv or None,
        channels=_channels_of(wire),
        signature=_signature_of(wire),
        temp_c=wire.scaled[codec.TEMP_C],
        humidity_pct=wire.scaled[codec.HUMIDITY],
        d_rh_dt=wire.scaled[codec.D_RH_DT],
        pressure_dev=wire.scaled[codec.PRESSURE_DEV],
        pressure_rate=wire.scaled[codec.PRESSURE_RATE],
        water=wire.has(codec.FLAG_WATER),
        lat=wire.lat,
        lon=wire.lon,
    )


def to_wire(frame: TelemetryFrame) -> WireFrame:
    by_channel = {c.channel: c for c in frame.channels}
    scaled: list[float | None] = [None] * 11
    for channel, dev_slot, slope_slot in _CHANNEL_SLOTS:
        measurement = by_channel.get(channel)
        scaled[dev_slot] = measurement.deviation if measurement else None
        scaled[slope_slot] = measurement.slope if measurement else None
    scaled[codec.TEMP_C] = frame.temp_c
    scaled[codec.HUMIDITY] = frame.humidity_pct
    scaled[codec.D_RH_DT] = frame.d_rh_dt
    scaled[codec.PRESSURE_DEV] = frame.pressure_dev
    scaled[codec.PRESSURE_RATE] = frame.pressure_rate

    return WireFrame(
        version=frame.version,
        flags=_flags_of(frame),
        hw_id_hex=str(frame.hw_id),
        seq=frame.seq,
        measured_epoch=int(frame.measured_at.timestamp()),
        state_code=_CODE_BY_STATE[frame.state],
        batt_mv=frame.batt_mv or 0,
        scaled=tuple(scaled),
        hold_s=frame.signature.hold_s if frame.signature else 0,
        lat=frame.lat,
        lon=frame.lon,
    )


def _channels_of(wire: WireFrame) -> tuple[ChannelReading, ...]:
    return tuple(
        ChannelReading(
            channel=channel,
            deviation=wire.scaled[dev_slot],
            slope=wire.scaled[slope_slot],
        )
        for channel, dev_slot, slope_slot in _CHANNEL_SLOTS
        # 채널 전체가 결측이면 도메인에 올리지 않는다 (미장착 센서와 구분)
        if wire.scaled[dev_slot] is not None or wire.scaled[slope_slot] is not None
    )


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
    if frame.lat is not None and frame.lon is not None:
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
