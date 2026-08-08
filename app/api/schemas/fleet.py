"""같은 모델 비교 응답 DTO."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.fleet import FleetComparison
from app.domain.value_objects import AlertState


class FleetComparisonResponse(ApiModel):
    fleet_size: int
    fleet_avg_level: AlertState
    my_level: AlertState
    my_multiplier: Annotated[
        float, Field(description="전체 평균 심각도 대비 내 배수", examples=[8.0])
    ]

    @classmethod
    def from_domain(cls, comparison: FleetComparison) -> FleetComparisonResponse:
        return cls(
            fleet_size=comparison.fleet_size,
            fleet_avg_level=comparison.fleet_avg_level,
            my_level=comparison.my_level,
            my_multiplier=comparison.my_multiplier,
        )
