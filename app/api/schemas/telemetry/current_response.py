from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import ChannelResponse
from app.api.schemas.telemetry.conditions import ordered_conditions
from app.api.schemas.telemetry.device_status import DeviceStatus
from app.core.device_current import DeviceCurrent
from app.domain.measurements import Measure
from app.domain.value_objects import Condition, Stage


class DeviceCurrentResponse(ApiModel):
    status: Annotated[
        DeviceStatus | None,
        Field(description="지금 취해야 하는 행동. 관측이 없거나 예열 중이면 null"),
    ] = None
    stage: Annotated[
        Stage | None,
        Field(
            description=(
                "화재로 가는 진행 단계. 앱은 이 단계까지 칸을 채운다. "
                "판정할 규칙이 아직 없으면 null — NONE('이상 없음')과 다르다"
            )
        ),
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
    gas: ChannelResponse | None = None
    h2: ChannelResponse | None = None
    co: ChannelResponse | None = None
    pressure: ChannelResponse | None = None

    @classmethod
    def from_domain(cls, current: DeviceCurrent) -> DeviceCurrentResponse:
        return cls(
            status=DeviceStatus.of(current.status),
            stage=Stage.from_conditions(current.conditions),
            conditions=ordered_conditions(current.conditions),
            at=current.at,
            latched=current.latched,
            water=current.water,
            gas=_channel(current, Measure.VOC_DEV, Measure.VOC_SLOPE),
            h2=_channel(current, Measure.H2_DEV, Measure.H2_SLOPE),
            co=_channel(current, Measure.CO_DEV, Measure.CO_SLOPE),
            pressure=_channel(current, Measure.PRESSURE_DEV, Measure.PRESSURE_RATE),
        )


def _channel(current: DeviceCurrent, deviation: Measure, slope: Measure) -> ChannelResponse | None:
    value, rate = current.value(deviation), current.value(slope)
    if value is None and rate is None:
        return None
    return ChannelResponse(value=value, slope=rate)
