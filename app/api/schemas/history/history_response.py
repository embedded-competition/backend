from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.event import EventResponse
from app.api.schemas.history.bucket_response import BucketResponse
from app.core.period_history import PeriodHistory


class HistoryResponse(ApiModel):
    from_: Annotated[datetime, Field(alias="from", description="조회 시작 (UTC, 포함)")]
    to: Annotated[datetime, Field(description="조회 끝 (UTC, 미포함)")]
    interval: Annotated[str, Field(description="집계 눈금", examples=["2h"])]
    buckets: Annotated[
        list[BucketResponse],
        Field(
            description=(
                "데이터가 있는 눈금 칸만. 값은 평균이 아니라 그 칸의 최고치다. "
                "빠진 칸이 곧 관측 공백이다"
            )
        ),
    ]
    events: Annotated[list[EventResponse], Field(description="최근 순으로 최대 200개")]

    @classmethod
    def from_domain(cls, history: PeriodHistory) -> HistoryResponse:
        return cls(
            from_=history.period.start,
            to=history.period.end,
            interval=str(history.interval),
            buckets=[BucketResponse.from_domain(bucket) for bucket in history.buckets],
            events=[EventResponse.from_domain(event) for event in history.events],
        )
