from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class GasChannelResponse(ApiModel):
    dev_z: Annotated[
        float | None,
        Field(description="baseline 대비 z-score. 가스 방향이 양수", examples=[3.1]),
    ] = None
    slope: Annotated[float | None, Field(description="dev 변화율 (z/min)", examples=[2.4])] = None
