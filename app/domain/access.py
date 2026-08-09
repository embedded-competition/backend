"""API 인증. 발급 원문은 저장하지 않는다 (docs/db-schema.md D9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AccessToken:
    """deviceToken. 원문은 발급 순간에만 존재하고 해시만 남는다."""

    device_id: int
    token_hash: str
    created_at: datetime
    last_used_at: datetime | None = None
    id: int | None = None
