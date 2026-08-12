from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.telemetry.conditions import ordered_conditions
from app.api.schemas.telemetry.device_status import DeviceStatus
from app.api.schemas.telemetry.peak_channel_response import PeakChannelResponse
from app.core.period_peaks import PeriodPeaks
from app.domain.measurements import Measure
from app.domain.value_objects import Condition, Stage


class PeriodPeaksResponse(ApiModel):
    status: Annotated[
        DeviceStatus | None,
        Field(description="기간 중 가장 심각했던 행동 단계. 관측이 없으면 null"),
    ] = None
    stage: Annotated[
        Stage | None, Field(description="기간 중 도달한 가장 깊은 진행 단계. 판정 불가면 null")
    ] = None
    conditions: Annotated[list[Condition], Field(description="기간 중 나타난 원인들의 합집합")]
    gas: PeakChannelResponse | None = None
    h2: PeakChannelResponse | None = None
    co: PeakChannelResponse | None = None
    pressure: PeakChannelResponse | None = None

    @classmethod
    def from_domain(cls, peaks: PeriodPeaks) -> PeriodPeaksResponse:
        return cls(
            status=DeviceStatus.of(peaks.status),
            stage=Stage.from_conditions(peaks.conditions),
            conditions=ordered_conditions(peaks.conditions),
            gas=_channel(peaks, Measure.VOC_DEV),
            h2=_channel(peaks, Measure.H2_DEV),
            co=_channel(peaks, Measure.CO_DEV),
            pressure=_channel(peaks, Measure.PRESSURE_DEV),
        )


def _channel(peaks: PeriodPeaks, deviation: Measure) -> PeakChannelResponse | None:
    peak = peaks.channel(deviation)
    return PeakChannelResponse.from_domain(peak) if peak else None
