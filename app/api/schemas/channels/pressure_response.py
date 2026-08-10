from __future__ import annotations

from app.api.schemas.base import ApiModel


class PressureResponse(ApiModel):
    pres_dev: float | None = None
    pres_rate: float | None = None
