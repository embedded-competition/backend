from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class SignatureResponse(ApiModel):
    rise: bool
    hold: bool
    no_recover: bool
    hold_s: Annotated[int, Field(description="시그니처 지속 초", examples=[18])]
