"""헬스체크 응답 DTO."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class ComponentHealth(BaseModel):
    model_config = ConfigDict(strict=True)

    status: ComponentStatus
    detail: Annotated[
        str | None,
        Field(description="비정상일 때 원인 요약", examples=["last frame 22m ago"]),
    ] = None


class HealthResponse(BaseModel):
    """구성요소별로 나눠 반환한다 — 무선 두절이 200 OK로 보이면 안 된다."""

    model_config = ConfigDict(strict=True)

    status: Annotated[ComponentStatus, Field(description="구성요소 중 최악값")]
    version: Annotated[str, Field(description="앱 버전", examples=["0.1.0"])]
    revision: Annotated[
        str | None,
        Field(description="적용된 Alembic 리비전", examples=["a1b2c3d4e5f6"]),
    ] = None
    components: Annotated[
        dict[str, ComponentHealth],
        Field(description="process·database·lora_radio·push"),
    ]
