from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.period_history import PeriodHistory


class HistoryRangeResponse(ApiModel):
    from_: Annotated[datetime, Field(alias="from", description="조회 시작 (UTC, 포함)")]
    to: Annotated[datetime, Field(description="조회 끝 (UTC, 미포함)")]
    interval: Annotated[str, Field(description="집계 눈금", examples=["2h"])]
    bucket_count: Annotated[
        int,
        Field(
            description=(
                "이 구간을 눈금으로 잘랐을 때 나오는 칸 수. buckets는 데이터가 있는 칸만 "
                "담으므로 이 값보다 짧을 수 있다 — 차이가 곧 관측 공백이다"
            ),
            examples=[84],
        ),
    ]

    @classmethod
    def from_domain(cls, history: PeriodHistory) -> HistoryRangeResponse:
        return cls(
            from_=history.period.start,
            to=history.period.end,
            interval=str(history.interval),
            bucket_count=history.bucket_count,
        )
