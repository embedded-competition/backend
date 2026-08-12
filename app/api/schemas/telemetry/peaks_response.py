from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.telemetry.conditions import ordered_conditions
from app.api.schemas.telemetry.peak_channel_response import PeakChannelResponse
from app.core.period_peaks import PeriodPeaks
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition


class PeriodPeaksResponse(ApiModel):
    status: Annotated[
        AlertState | None, Field(description="기간 중 가장 심각했던 상태. 관측이 없으면 null")
    ] = None
    conditions: Annotated[list[Condition], Field(description="기간 중 나타난 원인들의 합집합")]
    gas: PeakChannelResponse | None = None
    h2: PeakChannelResponse | None = None
    co: PeakChannelResponse | None = None
    pressure: PeakChannelResponse | None = None
    temp_c: Annotated[float | None, Field(examples=[26.1])] = None
    rh: Annotated[float | None, Field(description="상대습도 %", examples=[43.4])] = None

    @classmethod
    def from_domain(cls, peaks: PeriodPeaks) -> PeriodPeaksResponse:
        return cls(
            status=peaks.status,
            conditions=ordered_conditions(peaks.conditions),
            gas=_channel(peaks, Measure.VOC_DEV),
            h2=_channel(peaks, Measure.H2_DEV),
            co=_channel(peaks, Measure.CO_DEV),
            pressure=_channel(peaks, Measure.PRESSURE_DEV),
            temp_c=peaks.value(Measure.TEMP_C),
            rh=peaks.value(Measure.HUMIDITY_PCT),
        )


def _channel(peaks: PeriodPeaks, deviation: Measure) -> PeakChannelResponse | None:
    peak = peaks.channel(deviation)
    return PeakChannelResponse.from_domain(peak) if peak else None
