"""통계 탭 응답 DTO — 날짜별 시간당 집계."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import GasChannelResponse
from app.core.aggregation import HourlySample
from app.core.telemetry_service import DailyHistory
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
            gas=GasChannelResponse(dev_z=sample.channels.get(GasChannel.VOC)),
            h2=GasChannelResponse(dev_z=sample.channels.get(GasChannel.H2)),
            co=GasChannelResponse(dev_z=sample.channels.get(GasChannel.CO)),
            temp_c=sample.temp_c,
            rh=sample.humidity_pct,
            pres_dev=sample.pressure_dev,
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
