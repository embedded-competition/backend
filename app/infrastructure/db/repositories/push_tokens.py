"""푸시 토큰 저장소 + ORM↔domain 변환."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.push import PushToken
from app.infrastructure.db.orm import PushTokenOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyPushTokenRepository:
    session: Session

    def upsert(self, token: PushToken) -> PushToken:
        """같은 토큰 재등록은 소유 기기만 갱신한다 — 중복 행을 만들지 않는다."""
        row = self.session.scalar(select(PushTokenOrm).where(PushTokenOrm.token == token.token))
        if row is None:
            row = PushTokenOrm()
            self.session.add(row)
        _apply(row, token)
        self.session.flush()
        return _to_domain(row)

    def list_active(self, device_id: int) -> list[PushToken]:
        rows = self.session.scalars(
            select(PushTokenOrm).where(
                PushTokenOrm.device_id == device_id,
                PushTokenOrm.is_active.is_(True),
            )
        )
        return [_to_domain(row) for row in rows]

    def save(self, token: PushToken) -> PushToken:
        row = self.session.get(PushTokenOrm, token.id) if token.id else None
        if row is None:
            return self.upsert(token)
        _apply(row, token)
        self.session.flush()
        return _to_domain(row)


def _to_domain(row: PushTokenOrm) -> PushToken:
    return PushToken(
        id=row.id,
        device_id=row.device_id,
        token=row.token,
        platform=row.platform,
        registered_at=row.registered_at,
        last_used_at=row.last_used_at,
        is_active=row.is_active,
        deactivated_reason=row.deactivated_reason,
    )


def _apply(row: PushTokenOrm, token: PushToken) -> PushTokenOrm:
    row.device_id = token.device_id
    row.token = token.token
    row.platform = token.platform
    row.registered_at = token.registered_at
    row.last_used_at = token.last_used_at
    row.is_active = token.is_active
    row.deactivated_reason = token.deactivated_reason
    return row
