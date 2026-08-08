"""경보 해제 요청·응답 DTO."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class AlarmReleaseRequest(ApiModel):
    note: Annotated[str | None, Field(max_length=255, description="현장 확인 메모 (선택)")] = None


class AlarmReleaseResponse(ApiModel):
    released: bool
