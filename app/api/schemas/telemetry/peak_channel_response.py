from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.channels import ChannelResponse
from app.domain.readings import ChannelPeak


class PeakChannelResponse(ChannelResponse):
    at: Annotated[datetime, Field(description="이 값이 기간 중 최고치를 찍은 시각 (UTC)")]

    @classmethod
    def from_domain(cls, peak: ChannelPeak) -> PeakChannelResponse:
        return cls(value=peak.value, slope=peak.slope, at=peak.at)
