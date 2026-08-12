from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.event_page import EventPage
from app.domain.alerting import Event


class EventResponse(ApiModel):
    id: Annotated[int, Field(description="기록의 식별자", examples=[1])]
    timestamp: datetime
    kind: Annotated[str, Field(examples=["state_change", "action", "suppressed"])]
    description: Annotated[str, Field(description="서버가 생성한 문장 (앱 C5)")]

    @classmethod
    def from_domain(cls, event: Event) -> EventResponse:
        if event.id is None:
            raise ValueError("저장되지 않은 이벤트는 응답에 실을 수 없다 — 가리킬 식별자가 없다")
        return cls(
            id=event.id,
            timestamp=event.occurred_at,
            kind=event.kind.value,
            description=event.description,
        )


class EventListResponse(ApiModel):
    items: list[EventResponse]
    truncated: Annotated[bool, Field(description="더 있지만 이 응답에 담기지 않은 이벤트가 있는지")]

    @classmethod
    def from_domain(cls, page: EventPage) -> EventListResponse:
        return cls(
            items=[EventResponse.from_domain(event) for event in page.items],
            truncated=page.truncated,
        )
