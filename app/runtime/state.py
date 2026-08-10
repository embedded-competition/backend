from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

STATE_ATTRIBUTE = "runtime"


@dataclass(slots=True)
class ReceiverLiveness:
    enabled: bool

    last_frame_at: datetime | None = None
    task: asyncio.Task[None] | None = None

    def observe(self, at: datetime) -> None:
        self.last_frame_at = at

    def silence_s(self, now: datetime) -> float | None:
        if self.last_frame_at is None:
            return None
        return (now - self.last_frame_at).total_seconds()

    async def stop(self) -> None:
        self.enabled = False
        if self.task is None:
            return
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)
        self.task = None


@dataclass(slots=True)
class RuntimeState:
    session_factory: sessionmaker[Session]
    settings: Settings
    schema_revision: str | None = None
    lora: ReceiverLiveness = field(default_factory=lambda: ReceiverLiveness(enabled=False))
