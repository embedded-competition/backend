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
    model_config = ConfigDict(strict=True)

    status: Annotated[ComponentStatus, Field(description="구성요소 중 최악값")]
    version: Annotated[
        str,
        Field(
            description="지금 돌고 있는 배포의 태그. 주입이 없으면 'dev'",
            examples=["v0.6.0"],
        ),
    ]
    revision: Annotated[
        str | None,
        Field(description="적용된 Alembic 리비전", examples=["a1b2c3d4e5f6"]),
    ] = None
    components: Annotated[
        dict[str, ComponentHealth],
        Field(description="process·database·lora_radio·push"),
    ]
