from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.telemetry_service import DeviceLocation


class LocationResponse(ApiModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    at: Annotated[datetime, Field(description="이 좌표를 받은 시각 (UTC)")]

    @classmethod
    def from_domain(cls, location: DeviceLocation) -> LocationResponse:
        return cls(
            lat=location.coordinates.lat,
            lon=location.coordinates.lon,
            at=location.at,
        )
