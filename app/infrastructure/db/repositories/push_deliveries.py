from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.push import PushDelivery
from app.infrastructure.db.orm import PushDeliveryOrm, PushTokenOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyPushDeliveryRepository:
    session: Session

    def add(self, delivery: PushDelivery) -> PushDelivery:
        token_id = self.session.scalar(
            select(PushTokenOrm.id).where(PushTokenOrm.token == delivery.token)
        )
        if token_id is None:
            return delivery
        row = PushDeliveryOrm(
            alert_id=delivery.alert_id,
            token_id=token_id,
            attempt=delivery.attempt,
            status=delivery.status,
            error_code=delivery.error_code,
            sent_at=delivery.sent_at,
        )
        self.session.add(row)
        self.session.flush()
        delivery.id = row.id
        return delivery
