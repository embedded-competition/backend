"""푸시 발송 이력 저장소.

도메인은 토큰 문자열로 말하고 테이블은 token_id FK로 저장한다 — 그 변환이
이 저장소의 존재 이유다.
"""

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
            # 토큰이 사라진 뒤 도착한 결과. 이력을 버리지 않되 조용히 넘긴다.
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

    def list_for_alert(self, alert_id: int) -> list[PushDelivery]:
        rows = self.session.scalars(
            select(PushDeliveryOrm, PushTokenOrm.token)
            .join(PushTokenOrm, PushDeliveryOrm.token_id == PushTokenOrm.id)
            .where(PushDeliveryOrm.alert_id == alert_id)
            .order_by(PushDeliveryOrm.id)
        )
        return [
            PushDelivery(
                id=row.id,
                alert_id=row.alert_id,
                token="",
                attempt=row.attempt,
                status=row.status,
                error_code=row.error_code,
                sent_at=row.sent_at,
            )
            for row in rows
        ]
