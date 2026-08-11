from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class ChannelResponse(ApiModel):
    value: Annotated[
        float | None,
        Field(description="기준선 대비 상대 편차. 평소와 같으면 0", examples=[3.1]),
    ] = None
    slope: Annotated[float | None, Field(description="value의 분당 변화량", examples=[2.4])] = None
