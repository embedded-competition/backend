"""FrameSource 구현체 — 프레임을 언제 방출할지만 담당한다.

프레임 내용은 scenario.py가, 바이트 인코딩은 frame.py가 만든다.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.domain.ports.frame_source import RawFrame
from app.infrastructure.lora.frame import build_frame
from app.infrastructure.lora.scenario import ScenarioFrameFactory


class FakeFrameSource:
    """시나리오를 주기적으로 방출한다.

    실제 바이트를 만들어 파서를 그대로 태운다 — 파서를 우회하면 fake로 통과한
    코드가 실기기에서 깨진다.
    """

    def __init__(
        self,
        factory: ScenarioFrameFactory,
        *,
        interval_s: float = 2.0,
        loop_scenario: bool = True,
    ) -> None:
        self._factory = factory
        self._interval_s = interval_s
        self._loop = loop_scenario
        self._closed = False

    async def frames(self) -> AsyncIterator[RawFrame]:
        seq = 0
        while not self._closed:
            yield RawFrame(
                payload=build_frame(self._factory.build(seq)),
                received_at=datetime.now(UTC),
                # 거리에 따른 변동을 흉내낸다 — 화면에서 통신 품질 표시를 볼 수 있게
                rssi=-70 - int(6 * math.sin(seq / 3)),
                snr=7.5,
            )
            seq += 1
            if not self._loop and seq >= len(self._factory):
                return
            await asyncio.sleep(self._interval_s)

    async def close(self) -> None:
        self._closed = True


class ReplayFrameSource:
    """미리 만들어둔 프레임을 순서대로 방출한다. 테스트 전용."""

    def __init__(self, frames: list[RawFrame]) -> None:
        self._frames = frames

    async def frames(self) -> AsyncIterator[RawFrame]:
        for frame in self._frames:
            yield frame

    async def close(self) -> None:
        return None
