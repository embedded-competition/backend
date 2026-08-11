from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.domain.readings import ChannelPeak
from app.domain.value_objects import AlertState


class ChannelPeakResponse(ApiModel):
    dev_z: Annotated[
        float | None,
        Field(description="기간 중 최고 편차. baseline 대비 z-score", examples=[8.1]),
    ] = None
    slope: Annotated[float | None, Field(description="기간 중 최고 변화율 (z/min)")] = None
    at: Annotated[datetime, Field(description="최고치를 찍은 시각 (UTC)")]
    state: Annotated[AlertState, Field(description="그 시각의 상태")]

    @classmethod
    def from_domain(cls, peak: ChannelPeak) -> ChannelPeakResponse:
        return cls(dev_z=peak.deviation, slope=peak.slope, at=peak.at, state=peak.state)
