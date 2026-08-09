"""기록 저장소 + ORM↔domain 변환."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.alerting import Event
from app.domain.value_objects import EventKind
from app.infrastructure.db.orm import EventOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyEventRepository:
    session: Session

    def add(self, event: Event) -> Event:
        row = _apply(EventOrm(), event)
        self.session.add(row)
        self.session.flush()
        return _to_domain(row)

    def list_since(self, device_id: int, *, since: datetime, limit: int) -> list[Event]:
        rows = self.session.scalars(
            select(EventOrm)
            .where(EventOrm.device_id == device_id, EventOrm.occurred_at >= since)
            .order_by(EventOrm.occurred_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in rows]

    def list_in_range(
        self, device_id: int, *, start: datetime, end: datetime, limit: int
    ) -> list[Event]:
        rows = self.session.scalars(
            select(EventOrm)
            .where(
                EventOrm.device_id == device_id,
                EventOrm.occurred_at >= start,
                EventOrm.occurred_at <= end,
            )
            .order_by(EventOrm.occurred_at)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows]


def _to_domain(row: EventOrm) -> Event:
    return Event(
        id=row.id,
        device_id=row.device_id,
        alert_id=row.alert_id,
        kind=EventKind(row.kind),
        occurred_at=row.occurred_at,
        description=row.description,
    )


def _apply(row: EventOrm, event: Event) -> EventOrm:
    row.device_id = event.device_id
    row.alert_id = event.alert_id
    row.kind = event.kind.value
    row.occurred_at = event.occurred_at
    row.description = event.description
    return row
