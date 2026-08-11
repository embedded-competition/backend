from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.summary.current_response import CurrentResponse
from app.api.schemas.summary.peaks_response import PeaksResponse
from app.api.schemas.summary.summary_range_response import SummaryRangeResponse
from app.core.period_summary import PeriodSummary
from app.domain.value_objects import AlertState


class SummaryResponse(ApiModel):
    range: SummaryRangeResponse
    state: Annotated[AlertState, Field(description="기간 중 가장 심각했던 상태")]
    peaks: Annotated[PeaksResponse, Field(description="채널별 기간 중 최고치와 그 시각")]
    event_count: Annotated[int, Field(description="기간 중 기록 수", examples=[3])]
    current: Annotated[
        CurrentResponse | None,
        Field(description="range.live가 true일 때만 채워진다"),
    ] = None

    @classmethod
    def from_domain(cls, summary: PeriodSummary) -> SummaryResponse:
        return cls(
            range=SummaryRangeResponse.from_domain(summary),
            state=summary.state,
            peaks=PeaksResponse.from_domain(summary),
            event_count=summary.event_count,
            current=CurrentResponse.from_domain(summary.current) if summary.current else None,
        )
