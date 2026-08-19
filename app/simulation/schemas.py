from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.api.schemas.base import ApiModel
from app.domain.value_objects import AlertState, Condition
from app.simulation.channels import LEVEL_MAX, NodeChannel
from app.simulation.flow import Direction, FlowCommand, SensorFlow
from app.simulation.node import SimulatedNode
from app.simulation.simulator import NodeSimulator

_DIGITS = 1


class SimulationRequest(BaseModel):
    """제어 요청의 몸체.

    응답과 달리 strict를 걸지 않는다 — 사람이 손으로 치는 도구라 `400`과 `400.0`을
    구별해 거절하면 도구가 사람을 막는다. 대신 모르는 키는 거절해 오타가 조용히
    무시되지 않게 한다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class FlowCommandRequest(SimulationRequest):
    direction: Annotated[Direction, Field(description="오르는 흐름인지 내리는 흐름인지")]
    amount: Annotated[
        float,
        Field(gt=0, le=LEVEL_MAX, description="옮길 눈금 폭. 0~1000 스케일이고 범위 밖은 잘린다"),
    ]
    over_seconds: Annotated[
        float,
        Field(ge=0, le=3600, description="이 시간에 걸쳐 옮긴다. 0이면 다음 틱에 즉시"),
    ]

    def to_command(self) -> FlowCommand:
        return FlowCommand(
            direction=self.direction,
            amount=self.amount,
            over_seconds=self.over_seconds,
        )


class SimulatorTuneRequest(SimulationRequest):
    running: Annotated[
        bool | None, Field(description="틱 발신 여부. null이면 지금 값을 유지한다")
    ] = None
    tick_seconds: Annotated[
        float | None,
        Field(default=None, gt=0.1, le=600, description="틱 간격. null이면 지금 값을 유지한다"),
    ] = None


class ChannelFlowResponse(ApiModel):
    channel: NodeChannel
    level: Annotated[float, Field(description="지금 눈금 (0~1000)")]
    target: Annotated[float | None, Field(description="진행 중인 흐름의 목표 눈금")] = None
    seconds_left: Annotated[float | None, Field(description="목표까지 남은 시간")] = None
    condition: Annotated[
        Condition | None, Field(description="이 눈금에서 이 채널이 세우는 조건")
    ] = None
    watch_at: Annotated[float, Field(description="이 눈금부터 조건이 선다")]
    alarm_at: Annotated[
        float | None, Field(description="이 눈금부터 경보로 latch된다. 침수 채널은 null")
    ] = None

    @classmethod
    def from_flow(cls, flow: SensorFlow, at: datetime) -> ChannelFlowResponse:
        spec = flow.channel.spec
        level = flow.level_at(at)
        target = flow.target
        remaining = flow.remaining_seconds(at)
        return cls(
            channel=flow.channel,
            level=round(level.value, _DIGITS),
            target=None if target is None else round(target.value, _DIGITS),
            seconds_left=None if remaining is None else round(remaining, _DIGITS),
            condition=spec.condition_of(level),
            watch_at=spec.watch_at.value,
            alarm_at=None if spec.alarm_at is None else spec.alarm_at.value,
        )


class NodeResponse(ApiModel):
    mac: str
    state: AlertState
    conditions: list[Condition]
    latched: Annotated[
        bool,
        Field(description="경보 latch. 틱에서 한 번 걸리면 값을 내려도 풀리지 않고 리셋만 푼다"),
    ]
    water: bool
    channels: list[ChannelFlowResponse]

    @classmethod
    def from_node(cls, node: SimulatedNode, at: datetime) -> NodeResponse:
        verdict = node.verdict_at(at)
        return cls(
            mac=node.mac,
            state=verdict.state,
            conditions=sorted(verdict.conditions),
            latched=verdict.latched,
            water=verdict.water,
            channels=[ChannelFlowResponse.from_flow(flow, at) for flow in node.flows.values()],
        )


class SimulatorResponse(ApiModel):
    running: bool
    tick_seconds: Annotated[float, Field(description="틱 간격. 바꾸면 다음 틱부터 반영된다")]
    saturated_at: Annotated[
        float, Field(description="이 눈금에 닿으면 포화로 보고 센서 점검(FAULT)이 된다")
    ]
    nodes: list[NodeResponse]

    @classmethod
    def from_simulator(cls, simulator: NodeSimulator) -> SimulatorResponse:
        at = simulator.now
        return cls(
            running=simulator.running,
            tick_seconds=simulator.tick_seconds,
            saturated_at=LEVEL_MAX,
            nodes=[NodeResponse.from_node(node, at) for node in simulator.nodes],
        )
