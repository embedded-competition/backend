from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import (
    EnvResponse,
    GasChannelResponse,
    LocationResponse,
    PressureResponse,
    SignatureResponse,
)
from app.domain.device import Device
from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings import Reading
from app.domain.value_objects import AlertState, GasChannel


class ModuleResponse(ApiModel):
    node_id: Annotated[str | None, Field(examples=["44bd8d239c28"])] = None
    seq: int | None = None
    batt_mv: Annotated[int | None, Field(description="노드 배터리 전압 mV")] = None
    rssi: Annotated[int | None, Field(description="수신 세기 dBm", examples=[-74])] = None
    snr: float | None = None
    last_seen: Annotated[
        datetime | None,
        Field(
            description=(
                "마지막 프레임 수신 시각(UTC). 폴링 주기보다 갱신이 느리므로 "
                "앱은 이 값으로 데이터 나이를 표시해야 한다"
            )
        ),
    ] = None

    @classmethod
    def from_device(cls, device: Device) -> ModuleResponse:
        return cls(
            node_id=str(device.hw_id) if device.hw_id else None,
            seq=device.last_seq,
            last_seen=device.last_seen_at,
        )

    @classmethod
    def from_reading(cls, device: Device, reading: Reading) -> ModuleResponse:
        return cls(
            node_id=str(device.hw_id) if device.hw_id else None,
            seq=reading.seq,
            batt_mv=reading.frame.batt_mv,
            rssi=reading.radio.rssi,
            snr=reading.radio.snr,
            last_seen=reading.received_at,
        )


class TelemetryResponse(ApiModel):
    state: AlertState
    latched: Annotated[bool, Field(description="ALARM latch 유지 여부. 자동 해제 없음")] = False
    gas: GasChannelResponse
    h2: GasChannelResponse
    co: GasChannelResponse | None = None
    env: EnvResponse | None = None
    pressure: PressureResponse | None = None
    water: bool | None = None
    signature: SignatureResponse | None = None
    location: LocationResponse | None = None
    module: ModuleResponse

    @classmethod
    def from_domain(cls, device: Device, reading: Reading | None) -> TelemetryResponse:
        if reading is None:
            return cls(
                state=device.last_state or AlertState.WARMUP,
                gas=GasChannelResponse(),
                h2=GasChannelResponse(),
                module=ModuleResponse.from_device(device),
            )
        frame = reading.frame
        return cls(
            state=frame.state,
            latched=frame.latched,
            gas=channel_of(frame, GasChannel.VOC),
            h2=channel_of(frame, GasChannel.H2),
            co=channel_of(frame, GasChannel.CO) if frame.channel(GasChannel.CO) else None,
            env=_env_of(frame),
            pressure=_pressure_of(frame),
            water=frame.water,
            signature=_signature_of(frame),
            location=LocationResponse(lat=frame.location.lat, lon=frame.location.lon)
            if frame.location
            else None,
            module=ModuleResponse.from_reading(device, reading),
        )


def channel_of(frame: TelemetryFrame, channel: GasChannel) -> GasChannelResponse:
    measurement = frame.channel(channel)
    if measurement is None:
        return GasChannelResponse()
    return GasChannelResponse(dev_z=measurement.deviation, slope=measurement.slope)


def _env_of(frame: TelemetryFrame) -> EnvResponse | None:
    temp = frame.value(Measure.TEMP_C)
    rh = frame.value(Measure.HUMIDITY_PCT)
    if temp is None and rh is None:
        return None
    return EnvResponse(temp_c=temp, rh=rh, d_rh_dt=frame.value(Measure.D_RH_DT))


def _pressure_of(frame: TelemetryFrame) -> PressureResponse | None:
    dev = frame.value(Measure.PRESSURE_DEV)
    rate = frame.value(Measure.PRESSURE_RATE)
    if dev is None and rate is None:
        return None
    return PressureResponse(pres_dev=dev, pres_rate=rate)


def _signature_of(frame: TelemetryFrame) -> SignatureResponse | None:
    if frame.signature is None:
        return None
    return SignatureResponse(
        rise=frame.signature.rise,
        hold=frame.signature.hold,
        no_recover=frame.signature.no_recover,
        hold_s=frame.signature.hold_s,
    )
