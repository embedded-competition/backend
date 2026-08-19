from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.access import AccessToken
from app.infrastructure.db.orm import AccessTokenOrm


@dataclass(frozen=True, slots=True)
class SqlAlchemyAccessTokenRepository:
    session: Session

    def add(self, token: AccessToken) -> AccessToken:
        row = AccessTokenOrm(
            device_id=token.device_id,
            token_hash=token.token_hash,
            created_at=token.created_at,
            last_used_at=token.last_used_at,
        )
        self.session.add(row)
        self.session.flush()
        token.id = row.id
        return token

    def find_device_id(self, token_hash: str) -> int | None:
        return self.session.scalar(
            select(AccessTokenOrm.device_id).where(AccessTokenOrm.token_hash == token_hash)
        )

    def touch(self, token_hash: str, *, at: datetime) -> None:
        self.session.execute(
            update(AccessTokenOrm)
            .where(AccessTokenOrm.token_hash == token_hash)
            .values(last_used_at=at)
        )
