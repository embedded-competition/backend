from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.period_summary import PeriodSummary


class SummaryRangeResponse(ApiModel):
    from_: Annotated[datetime, Field(alias="from", description="조회 시작 (UTC, 포함)")]
    to: Annotated[datetime, Field(description="조회 끝 (UTC, 미포함)")]
    live: Annotated[
        bool,
        Field(
            description=(
                "구간이 현재를 포함하는지. true면 current가 채워지고 화면은 실시간 값을, "
                "false면 current가 null이고 화면은 peaks(기간 중 최고치)를 쓴다"
            )
        ),
    ]

    @classmethod
    def from_domain(cls, summary: PeriodSummary) -> SummaryRangeResponse:
        return cls(from_=summary.period.start, to=summary.period.end, live=summary.live)
