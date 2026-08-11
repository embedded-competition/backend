from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.channels import ChannelResponse
from app.domain.readings import ChannelPeak


class SummaryChannelResponse(ChannelResponse):
    at: Annotated[
        datetime,
        Field(
            description=(
                "이 값이 언제 것인지 (UTC). live=true면 측정 시각, "
                "false면 기간 중 최고치를 찍은 시각"
            )
        ),
    ]

    @classmethod
    def from_domain(cls, peak: ChannelPeak) -> SummaryChannelResponse:
        return cls(value=peak.value, slope=peak.slope, at=peak.at)
