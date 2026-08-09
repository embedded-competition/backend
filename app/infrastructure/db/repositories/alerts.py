"""경보 저장소 + ORM↔domain 변환."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.alerting import Alert
from app.domain.value_objects import AlertState
from app.infrastructure.db.orm import AlertOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyAlertRepository:
    session: Session

    def add(self, alert: Alert) -> Alert:
        row = _apply(AlertOrm(), alert)
        self.session.add(row)
        self.session.flush()
        return _to_domain(row)

    def get(self, alert_id: int) -> Alert | None:
        row = self.session.get(AlertOrm, alert_id)
        return _to_domain(row) if row else None

    def list_active(self) -> list[Alert]:
        # 부분 인덱스 ix_alerts_active가 지원한다.
        rows = self.session.scalars(
            select(AlertOrm)
            .where(AlertOrm.acknowledged_at.is_(None))
            .order_by(AlertOrm.occurred_at.desc())
        )
        return [_to_domain(row) for row in rows]

    def list_for_device(self, device_id: int, *, limit: int) -> list[Alert]:
        rows = self.session.scalars(
            select(AlertOrm)
            .where(AlertOrm.device_id == device_id)
            .order_by(AlertOrm.occurred_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in rows]

    def save(self, alert: Alert) -> Alert:
        row = self.session.get(AlertOrm, alert.id) if alert.id else None
        if row is None:
            return self.add(alert)
        _apply(row, alert)
        self.session.flush()
        return _to_domain(row)


def _to_domain(row: AlertOrm) -> Alert:
    return Alert(
        id=row.id,
        device_id=row.device_id,
        reading_id=row.reading_id,
        from_state=AlertState(row.from_state),
        to_state=AlertState(row.to_state),
        occurred_at=row.occurred_at,
        detected_at=row.detected_at,
        acknowledged_at=row.acknowledged_at,
        acknowledged_note=row.acknowledged_note,
    )


def _apply(row: AlertOrm, alert: Alert) -> AlertOrm:
    row.device_id = alert.device_id
    row.reading_id = alert.reading_id
    row.from_state = alert.from_state.value
    row.to_state = alert.to_state.value
    row.occurred_at = alert.occurred_at
    row.detected_at = alert.detected_at
    row.acknowledged_at = alert.acknowledged_at
    row.acknowledged_note = alert.acknowledged_note
    return row
