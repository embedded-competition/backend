from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.sensors.detail_bucket_response import DetailBucketResponse
from app.core.sensor_detail import SensorDetail


class SensorDetailResponse(ApiModel):
    buckets: Annotated[
        list[DetailBucketResponse],
        Field(description="데이터가 있는 눈금 칸만. 빠진 칸이 곧 관측 공백이다"),
    ]

    @classmethod
    def from_domain(cls, detail: SensorDetail) -> SensorDetailResponse:
        return cls(buckets=[DetailBucketResponse.from_domain(bucket) for bucket in detail.buckets])
