from __future__ import annotations

from datetime import UTC, datetime


def require_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name}은 timezone-aware여야 한다")
    return value.astimezone(UTC)
