from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.event import EventResponse
from app.api.schemas.history.bucket_response import BucketResponse
from app.api.schemas.history.history_range_response import HistoryRangeResponse
from app.core.period_history import PeriodHistory


class HistoryResponse(ApiModel):
    range: HistoryRangeResponse
    buckets: Annotated[
        list[BucketResponse],
        Field(description="데이터가 있는 눈금 칸만. 값은 평균이 아니라 그 칸의 최고치"),
    ]
    events: list[EventResponse]

    @classmethod
    def from_domain(cls, history: PeriodHistory) -> HistoryResponse:
        return cls(
            range=HistoryRangeResponse.from_domain(history),
            buckets=[BucketResponse.from_domain(bucket) for bucket in history.buckets],
            events=[EventResponse.from_domain(event) for event in history.events],
        )
