from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import DeviceId
from app.infrastructure.lora.frame import ABSENT_SEQ
from app.simulation.channels import Level, NodeChannel
from app.simulation.flow import FlowCommand, SensorFlow
from app.simulation.judgement import NodeVerdict, judge

SIMULATED_FRAME_VERSION = 100
"""저장된 판독이 실측이 아님을 남긴다.

와이어 포맷(1)·노드 CSV(0)와 겹치지 않는 값이라, 나중에 readings.frame_version만
보고 시뮬레이터가 만든 행을 골라낼 수 있다.
"""

TEST_MAC_PREFIX = "00:00:00:00:00:"
"""테스트 기기의 MAC 접두사. 제조사 OUI가 아니라 실기기와 절대 겹치지 않는다."""

TEST_NODE_COUNT = 5
"""흉내낼 기기 수. scripts/seed_demo.py의 시연 기기 다섯 대와 같은 MAC을 쓴다."""

_TEST_LOCATION = Coordinates(lat=37.5573, lon=127.0329)


def simulated_macs(count: int) -> tuple[str, ...]:
    return tuple(f"{TEST_MAC_PREFIX}{index:02X}" for index in range(1, count + 1))


@dataclass(slots=True)
class SimulatedNode:
    """임베디드 노드 한 대. 값을 흘리고, 자기 상태를 스스로 판정한다."""

    mac: str
    flows: dict[NodeChannel, SensorFlow]
    location: Coordinates | None = _TEST_LOCATION
    latched: bool = field(default=False)

    @classmethod
    def at_baseline(cls, mac: str) -> SimulatedNode:
        return cls(
            mac=mac, flows={channel: SensorFlow.at_baseline(channel) for channel in NodeChannel}
        )

    @property
    def hw_id(self) -> DeviceId:
        return DeviceId(self.mac.replace(":", "").lower())

    def steer(self, channel: NodeChannel, command: FlowCommand, *, at: datetime) -> None:
        self.flows[channel].steer(command, at=at)

    def reset(self) -> None:
        for flow in self.flows.values():
            flow.reset()
        self.latched = False

    def emit(self, at: datetime) -> TelemetryFrame:
        """틱 하나를 내보낸다. 레벨과 latch가 여기서 확정된다."""
        levels = {channel: flow.settle(at) for channel, flow in self.flows.items()}
        verdict = judge(levels, latched=self.latched)
        self.latched = verdict.latched
        return TelemetryFrame(
            version=SIMULATED_FRAME_VERSION,
            hw_id=self.hw_id,
            seq=ABSENT_SEQ,
            measured_at=at,
            state=verdict.state,
            conditions=verdict.conditions,
            latched=verdict.latched,
            water=verdict.water,
            values=_values_of(levels),
            location=self.location,
        )

    def verdict_at(self, now: datetime) -> NodeVerdict:
        """조회용 판정. 흐름도 latch도 건드리지 않는다."""
        levels = {channel: flow.level_at(now) for channel, flow in self.flows.items()}
        return judge(levels, latched=self.latched)


def _values_of(levels: dict[NodeChannel, Level]) -> dict[Measure, float]:
    return {channel.spec.measure: level.value for channel, level in levels.items()}
