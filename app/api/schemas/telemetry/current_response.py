from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import ChannelResponse
from app.api.schemas.telemetry.conditions import ordered_conditions
from app.core.device_current import DeviceCurrent
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition


class DeviceCurrentResponse(ApiModel):
    status: Annotated[
        AlertState | None, Field(description="지금 취해야 하는 상태. 관측이 없으면 null")
    ] = None
    conditions: Annotated[
        list[Condition],
        Field(description="지금 기기에 일어나고 있는 현상들 — 여러 개가 동시에 성립할 수 있다"),
    ]
    at: Annotated[
        datetime | None, Field(description="이 응답이 근거로 삼은 마지막 관측 시각 (UTC)")
    ] = None
    latched: Annotated[bool, Field(description="ALARM latch 유지 여부. 자동 해제 없음")] = False
    water: Annotated[bool, Field(description="침수·누액 감지 여부")] = False
    management_phone: Annotated[
        str | None,
        Field(description="관리실 전화번호. 경보 화면 버튼에 사용", examples=["01029015899"]),
    ] = None
    gas: ChannelResponse | None = None
    h2: ChannelResponse | None = None
    co: ChannelResponse | None = None
    pressure: ChannelResponse | None = None
    temp_c: Annotated[float | None, Field(examples=[26.1])] = None
    rh: Annotated[float | None, Field(description="상대습도 %", examples=[43.4])] = None

    @classmethod
    def from_domain(cls, current: DeviceCurrent) -> DeviceCurrentResponse:
        return cls(
            status=current.status,
            conditions=ordered_conditions(current.conditions),
            at=current.at,
            latched=current.latched,
            water=current.water,
            management_phone=current.management_phone,
            gas=_channel(current, Measure.VOC_DEV, Measure.VOC_SLOPE),
            h2=_channel(current, Measure.H2_DEV, Measure.H2_SLOPE),
            co=_channel(current, Measure.CO_DEV, Measure.CO_SLOPE),
            pressure=_channel(current, Measure.PRESSURE_DEV, Measure.PRESSURE_RATE),
            temp_c=current.value(Measure.TEMP_C),
            rh=current.value(Measure.HUMIDITY_PCT),
        )


def _channel(current: DeviceCurrent, deviation: Measure, slope: Measure) -> ChannelResponse | None:
    value, rate = current.value(deviation), current.value(slope)
    if value is None and rate is None:
        return None
    return ChannelResponse(value=value, slope=rate)
