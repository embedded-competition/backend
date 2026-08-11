from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.base import ApiModel


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
