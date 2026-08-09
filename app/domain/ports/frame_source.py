"""LoRa 수신 port. 하드웨어 없는 환경에서는 fake 구현을 주입한다."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawFrame:
    """수신 어댑터가 넘기는 원시 프레임. 파싱 전 상태."""

    payload: bytes
    received_at: datetime
    rssi: int | None = None
    snr: float | None = None


class FrameSource(Protocol):
    def frames(self) -> AsyncIterator[RawFrame]:
        """async generator라 호출 자체는 동기다 — await이 아니라 async for로 쓴다."""
        ...

    async def close(self) -> None: ...
