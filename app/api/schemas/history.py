from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import GasChannelResponse
from app.core.aggregation import HourlySample
from app.core.telemetry_service import DailyHistory
from app.domain.measurements import Aspect, Measure, channel_measures
from app.domain.value_objects import AlertState, GasChannel


class HourlySampleResponse(ApiModel):
    hour: Annotated[str, Field(examples=["14:00"])]
    state: AlertState
    gas: GasChannelResponse
    h2: GasChannelResponse
    co: GasChannelResponse
    temp_c: float | None = None
    rh: float | None = None
    pres_dev: float | None = None

    @classmethod
    def from_domain(cls, sample: HourlySample) -> HourlySampleResponse:
        return cls(
            hour=sample.hour,
            state=sample.state,
            gas=_channel(sample, GasChannel.VOC),
            h2=_channel(sample, GasChannel.H2),
            co=_channel(sample, GasChannel.CO),
            temp_c=sample.value(Measure.TEMP_C),
            rh=sample.value(Measure.HUMIDITY_PCT),
            pres_dev=sample.value(Measure.PRESSURE_DEV),
        )


def _channel(sample: HourlySample, channel: GasChannel) -> GasChannelResponse:
    slots = channel_measures(channel)
    return GasChannelResponse(
        dev_z=sample.value(slots[Aspect.DEVIATION]),
        slope=sample.value(slots[Aspect.SLOPE]),
    )


class HistoryEventResponse(ApiModel):
    time: Annotated[str, Field(examples=["14:32"])]
    description: str


class HistoryResponse(ApiModel):
    date: date
    samples: list[HourlySampleResponse]
    events: list[HistoryEventResponse]

    @classmethod
    def from_domain(cls, history: DailyHistory) -> HistoryResponse:
        return cls(
            date=history.day,
            samples=[HourlySampleResponse.from_domain(s) for s in history.samples],
            events=[
                HistoryEventResponse(
                    time=event.occurred_at.strftime("%H:%M"),
                    description=event.description,
                )
                for event in history.events
            ],
        )
