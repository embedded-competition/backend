from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request

from app.api.schemas.base import ErrorResponse
from app.simulation.channels import NodeChannel
from app.simulation.schemas import (
    FlowCommandRequest,
    NodeResponse,
    SimulatorResponse,
    SimulatorTuneRequest,
)
from app.simulation.simulator import NodeSimulator

STATE_ATTRIBUTE = "simulator"
"""lifespan이 시뮬레이터를 올려두는 자리. 라우터는 여기서만 시뮬레이터를 찾는다."""

router = APIRouter(prefix="/simulation", tags=["simulation"])


def simulator_dep(request: Request) -> NodeSimulator:
    simulator = getattr(request.app.state, STATE_ATTRIBUTE, None)
    if not isinstance(simulator, NodeSimulator):
        raise RuntimeError("lifespan이 시뮬레이터를 올리지 않았다")
    return simulator


SimulatorDep = Annotated[NodeSimulator, Depends(simulator_dep)]

MacPath = Annotated[
    str,
    Path(
        min_length=12,
        max_length=17,
        description="시뮬레이터가 흉내내는 테스트 기기의 MAC",
        examples=["00:00:00:00:00:01"],
    ),
]
ChannelPath = Annotated[NodeChannel, Path(description="노드가 보내는 측정 채널")]

_UNKNOWN_NODE: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "시뮬레이터가 흉내내지 않는 MAC"}
}


@router.get(
    "",
    response_model=SimulatorResponse,
    summary="스케줄러와 노드들의 지금 상태",
    description="채널마다 지금 눈금·목표·남은 시간과, 조건이 서는 눈금을 함께 준다.",
)
async def read_simulator(simulator: SimulatorDep) -> SimulatorResponse:
    return SimulatorResponse.from_simulator(simulator)


@router.patch(
    "",
    response_model=SimulatorResponse,
    summary="스케줄러 구동·틱 간격 조절",
    description="넘기지 않은 항목은 그대로 둔다. 틱 간격은 진행 중인 대기가 끝난 뒤 반영된다.",
)
async def tune_simulator(body: SimulatorTuneRequest, simulator: SimulatorDep) -> SimulatorResponse:
    simulator.retune(running=body.running, tick_seconds=body.tick_seconds)
    return SimulatorResponse.from_simulator(simulator)


@router.post(
    "/devices/{mac}/channels/{channel}/flow",
    response_model=NodeResponse,
    summary="센서 하나의 흐름을 지시",
    description=(
        "지금 눈금에서 지정한 폭만큼, 지정한 시간에 걸쳐 선형으로 옮긴다. "
        "진행 중인 흐름이 있으면 지금 위치에서 다시 출발한다."
    ),
    responses=_UNKNOWN_NODE,
)
async def steer_flow(
    body: FlowCommandRequest,
    mac: MacPath,
    channel: ChannelPath,
    simulator: SimulatorDep,
) -> NodeResponse:
    node = simulator.steer(mac, channel, body.to_command())
    return NodeResponse.from_node(node, simulator.now)


@router.post(
    "/devices/{mac}/reset",
    response_model=NodeResponse,
    summary="노드를 기준선으로 되돌린다",
    description="모든 채널을 기준 눈금으로 되돌리고 경보 latch를 푼다.",
    responses=_UNKNOWN_NODE,
)
async def reset_node(mac: MacPath, simulator: SimulatorDep) -> NodeResponse:
    node = simulator.reset(mac)
    return NodeResponse.from_node(node, simulator.now)
