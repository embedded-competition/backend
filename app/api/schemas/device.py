from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.base import ApiModel
from app.domain.value_objects import SensorCheck


class PushTokenRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    token: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            description="Expo 푸시 토큰",
            examples=["ExponentPushToken[xxxxxxx]"],
        ),
    ]


class PushTokenResponse(ApiModel):
    registered: bool


class SensorCheckResponse(ApiModel):
    sensor_check: Annotated[
        SensorCheck | None,
        Field(description="센서를 믿을 수 있는가. 관측이 없으면 null"),
    ] = None

    @classmethod
    def from_domain(cls, check: SensorCheck | None) -> SensorCheckResponse:
        return cls(sensor_check=check)
