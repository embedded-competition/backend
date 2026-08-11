from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels import ChannelResponse
from app.domain.measurements import SLOPE_BY_DEVIATION, Measure
from app.domain.readings import Bucket
from app.domain.value_objects import AlertState


class BucketResponse(ApiModel):
    start: Annotated[datetime, Field(description="눈금 구간의 시작 시각 (UTC, 끝은 미포함)")]
    state: Annotated[AlertState, Field(description="이 구간에서 가장 심각했던 상태")]
    samples: Annotated[int, Field(description="이 구간에 들어온 프레임 수", examples=[24])]
    gas: ChannelResponse | None = None
    h2: ChannelResponse | None = None
    co: ChannelResponse | None = None
    pressure: ChannelResponse | None = None
    temp_c: Annotated[float | None, Field(examples=[26.1])] = None
    rh: Annotated[float | None, Field(description="상대습도 %", examples=[43.4])] = None

    @classmethod
    def from_domain(cls, bucket: Bucket) -> BucketResponse:
        return cls(
            start=bucket.start,
            state=bucket.state,
            samples=bucket.samples,
            gas=_channel(bucket, Measure.VOC_DEV),
            h2=_channel(bucket, Measure.H2_DEV),
            co=_channel(bucket, Measure.CO_DEV),
            pressure=_channel(bucket, Measure.PRESSURE_DEV),
            temp_c=bucket.value(Measure.TEMP_C),
            rh=bucket.value(Measure.HUMIDITY_PCT),
        )


def _channel(bucket: Bucket, deviation: Measure) -> ChannelResponse | None:
    value = bucket.value(deviation)
    slope = bucket.value(SLOPE_BY_DEVIATION[deviation])
    if value is None and slope is None:
        return None
    return ChannelResponse(value=value, slope=slope)
