from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.domain.alerting import Event
from app.domain.value_objects import EventKind, Period
from app.infrastructure.db.orm import EventOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyEventRepository:
    session: Session

    def add(self, event: Event) -> Event:
        row = _apply(EventOrm(), event)
        self.session.add(row)
        self.session.flush()
        return _to_domain(row)

    def list_in_period(self, device_id: int, period: Period, *, limit: int) -> list[Event]:
        rows = self.session.scalars(
            select(EventOrm)
            .where(*_within(device_id, period))
            .order_by(EventOrm.occurred_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in rows]


def _within(device_id: int, period: Period) -> tuple[ColumnElement[bool], ...]:
    return (
        EventOrm.device_id == device_id,
        EventOrm.occurred_at >= period.start,
        EventOrm.occurred_at < period.end,
    )


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
