"""FrameSource fake. Protocol 구현이라 시그니처가 바뀌면 타입 체크로 잡힌다."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.domain.ports.frame_source import RawFrame


@dataclass(slots=True)
class ReplayFrameSource:
    """미리 만들어둔 프레임을 순서대로 방출하고 끝낸다."""

    # 필드명이 `frames`가 아닌 이유: FrameSource port의 `frames()` 메서드와 겹친다.
    queued: list[RawFrame]

    async def frames(self) -> AsyncIterator[RawFrame]:
        for frame in self.queued:
            yield frame

    async def close(self) -> None:
        return None
