from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import datetime

from app.core import identity
from app.domain.exceptions import DeviceNotFound
from app.domain.ports.clock import Clock
from app.domain.ports.frame_source import RawFrame
from app.infrastructure.clock import SystemClock
from app.simulation.channels import NodeChannel
from app.simulation.flow import FlowCommand
from app.simulation.node import TEST_NODE_COUNT, SimulatedNode, simulated_macs
from app.simulation.payload import encode

logger = logging.getLogger(__name__)

_RSSI = -70
_SNR = 7.5

DEFAULT_TICK_SECONDS = 3.0
"""기본 틱 간격. 설정으로 받지 않는다 — 시뮬레이터는 늘 떠 있고, 조절은 실행 중에
PATCH /v1/simulation으로 한다. 설정 키를 두면 배포마다 값이 굳어 조절이 재기동을 요구한다."""


class NodeSimulator:
    """임베디드 노드 자리에 서는 스케줄러.

    틱마다 노드 수만큼 프레임을 내보낸다. 수신·저장·알림은 실기 경로와 같은
    `FrameReceiver`가 처리한다 — 시뮬레이터는 프레임을 만드는 데까지만 관여한다.

    틱 간격을 바꾸거나 멈추라고 하면 대기가 즉시 깨진다 — 간격을 10분으로 뒀다가
    줄였을 때 10분을 기다리게 하면 조절 자체가 쓸모없어진다.
    """

    @classmethod
    def always_on(cls) -> NodeSimulator:
        """조립부가 조건 없이 부르는 생성자. 켜고 끄는 판단은 여기에 없다."""
        return cls(
            simulated_macs(TEST_NODE_COUNT),
            tick_seconds=DEFAULT_TICK_SECONDS,
            clock=SystemClock(),
        )

    def __init__(self, macs: Sequence[str], *, tick_seconds: float, clock: Clock) -> None:
        normalized = tuple(identity.normalize_mac(mac) for mac in macs)
        self._nodes = {mac: SimulatedNode.at_baseline(mac) for mac in normalized}
        self._tick_seconds = tick_seconds
        self._clock = clock
        self._running = True
        self._closed = False
        self._interrupted = asyncio.Event()

    async def frames(self) -> AsyncIterator[RawFrame]:
        while not self._closed:
            for raw in self._tick():
                yield raw
            await self._wait_for_next_tick()

    async def close(self) -> None:
        self._closed = True
        self._interrupted.set()

    @property
    def now(self) -> datetime:
        return self._clock.now()

    @property
    def running(self) -> bool:
        return self._running

    @property
    def tick_seconds(self) -> float:
        return self._tick_seconds

    @property
    def nodes(self) -> tuple[SimulatedNode, ...]:
        return tuple(self._nodes.values())

    def node(self, raw_mac: str) -> SimulatedNode:
        found = self._nodes.get(identity.normalize_mac(raw_mac))
        if found is None:
            raise DeviceNotFound(f"시뮬레이터가 흉내내지 않는 기기: {raw_mac}")
        return found

    def steer(self, raw_mac: str, channel: NodeChannel, command: FlowCommand) -> SimulatedNode:
        node = self.node(raw_mac)
        node.steer(channel, command, at=self.now)
        logger.info(
            "simulator flow steered",
            extra={
                "mac": node.mac,
                "channel": channel.value,
                "direction": command.direction.value,
                "amount": command.amount,
                "over_seconds": command.over_seconds,
            },
        )
        return node

    def reset(self, raw_mac: str) -> SimulatedNode:
        node = self.node(raw_mac)
        node.reset()
        logger.info("simulator node reset", extra={"mac": node.mac})
        return node

    def retune(self, *, running: bool | None = None, tick_seconds: float | None = None) -> None:
        if running is not None:
            self._running = running
        if tick_seconds is not None:
            self._tick_seconds = tick_seconds
        self._interrupted.set()
        logger.info(
            "simulator retuned",
            extra={"running": self._running, "tick_seconds": self._tick_seconds},
        )

    async def _wait_for_next_tick(self) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._interrupted.wait(), timeout=self._tick_seconds)
        self._interrupted.clear()

    def _tick(self) -> list[RawFrame]:
        if not self._running:
            return []
        at = self.now
        return [
            RawFrame(payload=encode(node.emit(at)), received_at=at, rssi=_RSSI, snr=_SNR)
            for node in self._nodes.values()
        ]
