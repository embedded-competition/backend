from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.sensor_detail import DetailBucket


class DetailBucketResponse(ApiModel):
    start: Annotated[datetime, Field(description="눈금 구간의 시작 시각 (UTC, 끝은 미포함)")]
    value: Annotated[float | None, Field(description="이 칸의 최고치", examples=[3.1])] = None
    slope: Annotated[float | None, Field(description="value의 분당 변화량", examples=[2.4])] = None

    @classmethod
    def from_domain(cls, bucket: DetailBucket) -> DetailBucketResponse:
        return cls(start=bucket.start, value=bucket.value, slope=bucket.slope)
