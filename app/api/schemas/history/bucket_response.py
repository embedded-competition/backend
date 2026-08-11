from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.channels import MeasuredValuesResponse
from app.domain.readings import Bucket
from app.domain.value_objects import AlertState


class BucketResponse(MeasuredValuesResponse):
    start: Annotated[datetime, Field(description="눈금 구간의 시작 시각 (UTC, 끝은 미포함)")]
    state: Annotated[AlertState, Field(description="이 구간에서 가장 심각했던 상태")]
    samples: Annotated[int, Field(description="이 구간에 들어온 프레임 수", examples=[24])]

    @classmethod
    def from_domain(cls, bucket: Bucket) -> BucketResponse:
        return cls(
            start=bucket.start,
            state=bucket.state,
            samples=bucket.samples,
            **MeasuredValuesResponse.fields_of(bucket),
        )
