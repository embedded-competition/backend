"""도메인 시각 규약.

naive datetime을 경계에서 막는다 — 한 번 저장되면 로컬시간과 섞여 복구할 수 없다.
"""

from __future__ import annotations

from datetime import UTC, datetime


def require_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name}은 timezone-aware여야 한다")
    return value.astimezone(UTC)
