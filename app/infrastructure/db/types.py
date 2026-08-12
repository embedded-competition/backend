from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Dialect, String, TypeDecorator

from app.domain.value_objects import Condition


class UtcDateTime(TypeDecorator[datetime]):
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime은 저장할 수 없다 — aware로 넘겨야 한다")
        utc = value.astimezone(UTC)
        return utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def process_result_value(self, value: Any, _dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class ConditionSet(TypeDecorator[frozenset[Condition]]):
    impl = String(64)
    cache_ok = True

    def process_bind_param(
        self, value: frozenset[Condition] | None, _dialect: Dialect
    ) -> str | None:
        if value is None:
            return None
        return ",".join(sorted(condition.value for condition in value))

    def process_result_value(self, value: Any, _dialect: Dialect) -> frozenset[Condition] | None:
        if value is None:
            return None
        if not value:
            return frozenset()
        return frozenset(Condition(item) for item in str(value).split(","))
