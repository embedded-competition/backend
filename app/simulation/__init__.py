"""임베디드 노드 대신 서는 스케줄러와 그 제어 표면.

실측값이 아직 없어도 앱이 봐야 하는 화면(주의·경보·센서 점검·침수)을 만들 수
있게 한다. 제품 경로는 이 묶음을 알지 못한다 — 조립부(runtime)와 main만 안다.

여기서 밝히는 것은 엔진뿐이다. HTTP 제어 표면은 `app.simulation.routes`가 따로
내놓는다 — 조립부가 엔진을 만들려고 라우터까지 끌고 오면 runtime이 api를 아는
꼴이 된다.
"""

from __future__ import annotations

from app.simulation.channels import LEVEL_MAX, LEVEL_MIN, Level, NodeChannel
from app.simulation.flow import Direction, FlowCommand
from app.simulation.node import (
    TEST_MAC_PREFIX,
    TEST_NODE_COUNT,
    SimulatedNode,
    simulated_macs,
)
from app.simulation.payload import decode as decode_simulated_payload
from app.simulation.simulator import NodeSimulator

__all__ = [
    "LEVEL_MAX",
    "LEVEL_MIN",
    "TEST_MAC_PREFIX",
    "TEST_NODE_COUNT",
    "Direction",
    "FlowCommand",
    "Level",
    "NodeChannel",
    "NodeSimulator",
    "SimulatedNode",
    "decode_simulated_payload",
    "simulated_macs",
]
