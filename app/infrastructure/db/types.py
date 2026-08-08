"""SQLite 전용 컬럼 타입.

SQLAlchemy DateTime(timezone=True)은 SQLite에서 타임존을 보존하지 못한다
(SQLite에 tz 타입이 없음). aware datetime을 넣고 꺼내면 naive로 돌아온다.
→ UTC ISO8601 TEXT로 저장하고 복원 시 aware로 되돌린다 (docs/db-schema.md D5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Dialect, String, TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    """'2026-08-08T12:34:56.789Z' 형식 TEXT. 사전순 정렬 = 시간순 정렬."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime은 저장할 수 없다 — aware로 넘겨야 한다")
        utc = value.astimezone(UTC)
        return utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
