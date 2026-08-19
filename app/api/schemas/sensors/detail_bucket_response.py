from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.sensors.bucket_level import BucketLevel
from app.core.sensor_detail import DetailBucket


class DetailBucketResponse(ApiModel):
    start: Annotated[datetime, Field(description="눈금 구간의 시작 시각 (UTC, 끝은 미포함)")]
    level: Annotated[
        BucketLevel | None,
        Field(
            description=(
                "이 칸의 정도(평소·주의·위험). 판정 기준이 아직 없어 지금은 항상 null이다 — "
                "프레임 v2의 편차값이 와야 임계를 말할 수 있다"
            )
        ),
    ] = None
    value: Annotated[float | None, Field(description="이 칸의 최고치", examples=[3.1])] = None
    slope: Annotated[float | None, Field(description="value의 분당 변화량", examples=[2.4])] = None

    @classmethod
    def from_domain(cls, bucket: DetailBucket) -> DetailBucketResponse:
        return cls(start=bucket.start, level=None, value=bucket.value, slope=bucket.slope)
