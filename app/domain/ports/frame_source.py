from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawFrame:
    payload: bytes
    received_at: datetime
    rssi: int | None = None
    snr: float | None = None


class FrameSource(Protocol):
    def frames(self) -> AsyncIterator[RawFrame]: ...

    async def close(self) -> None: ...
