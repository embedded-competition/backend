from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.domain.alerting import Event


class EventResponse(ApiModel):
    id: Annotated[str, Field(examples=["evt_1"])]
    timestamp: datetime
    kind: Annotated[str, Field(examples=["state_change", "action", "suppressed"])]
    description: Annotated[str, Field(description="서버가 생성한 문장 (앱 C5)")]

    @classmethod
    def from_domain(cls, event: Event) -> EventResponse:
        return cls(
            id=f"evt_{event.id}",
            timestamp=event.occurred_at,
            kind=event.kind.value,
            description=event.description,
        )


class EventListResponse(ApiModel):
    items: list[EventResponse]
