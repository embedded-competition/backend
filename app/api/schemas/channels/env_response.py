from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class EnvResponse(ApiModel):
    temp_c: float | None = None
    rh: Annotated[float | None, Field(description="상대습도 %")] = None
    d_rh_dt: Annotated[float | None, Field(description="습도 변화율 %RH/min. 습도 게이트 근거")] = (
        None
    )
