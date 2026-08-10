from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AccessToken:
    device_id: int
    token_hash: str
    created_at: datetime
    last_used_at: datetime | None = None
    id: int | None = None
