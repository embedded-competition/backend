"""현재 상태 응답 DTO.

**raw 센서값(sraw·mv·baseline·rsKohm·mvAvg)은 포함하지 않는다.**
노드가 판정하고 정규화값만 전송하므로 서버가 채울 수 없다 (정합화 B2).
"""

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
from app.domain.models import Device, Reading
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
            batt_mv=reading.batt_mv,
            rssi=reading.rssi,
            snr=reading.snr,
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
            # 프레임을 한 번도 못 받았다. 상태를 지어내지 않는다.
            return cls(
                state=device.last_state or AlertState.WARMUP,
                gas=GasChannelResponse(),
                h2=GasChannelResponse(),
                module=ModuleResponse.from_device(device),
            )
        return cls(
            state=reading.state,
            latched=bool(reading.latched),
            gas=channel_of(reading, GasChannel.VOC),
            h2=channel_of(reading, GasChannel.H2),
            co=channel_of(reading, GasChannel.CO) if reading.channel(GasChannel.CO) else None,
            env=_env_of(reading),
            pressure=_pressure_of(reading),
            water=reading.water,
            signature=_signature_of(reading),
            location=_location_of(reading),
            module=ModuleResponse.from_reading(device, reading),
        )


def channel_of(reading: Reading, channel: GasChannel) -> GasChannelResponse:
    measurement = reading.channel(channel)
    if measurement is None:
        return GasChannelResponse()
    return GasChannelResponse(dev_z=measurement.deviation, slope=measurement.slope)


def _env_of(reading: Reading) -> EnvResponse | None:
    if reading.temp_c is None and reading.humidity_pct is None:
        return None
    return EnvResponse(temp_c=reading.temp_c, rh=reading.humidity_pct, d_rh_dt=reading.d_rh_dt)


def _pressure_of(reading: Reading) -> PressureResponse | None:
    if reading.pressure_dev is None and reading.pressure_rate is None:
        return None
    return PressureResponse(pres_dev=reading.pressure_dev, pres_rate=reading.pressure_rate)


def _signature_of(reading: Reading) -> SignatureResponse | None:
    if reading.signature is None:
        return None
    return SignatureResponse(
        rise=reading.signature.rise,
        hold=reading.signature.hold,
        no_recover=reading.signature.no_recover,
        hold_s=reading.signature.hold_s,
    )


def _location_of(reading: Reading) -> LocationResponse | None:
    if reading.lat is None or reading.lon is None:
        return None
    return LocationResponse(lat=reading.lat, lon=reading.lon)
