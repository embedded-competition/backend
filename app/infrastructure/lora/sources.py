from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.domain.ports.frame_source import RawFrame
from app.infrastructure.lora.frame import build_frame
from app.infrastructure.lora.scenario import ScenarioFrameFactory


class FakeFrameSource:
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
                rssi=-70 - int(6 * math.sin(seq / 3)),
                snr=7.5,
            )
            seq += 1
            if not self._loop and seq >= len(self._factory):
                return
            await asyncio.sleep(self._interval_s)

    async def close(self) -> None:
        self._closed = True
