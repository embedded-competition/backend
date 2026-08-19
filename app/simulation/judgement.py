from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects import AlertState, Condition
from app.simulation.channels import Level, NodeChannel


@dataclass(frozen=True, slots=True)
class NodeVerdict:
    """노드가 내리는 판정. 서버는 값만으로 상태를 정하지 않는다 (docs/lora-frame.md)."""

    state: AlertState
    conditions: frozenset[Condition]
    water: bool
    latched: bool


def judge(levels: dict[NodeChannel, Level], *, latched: bool) -> NodeVerdict:
    """채널마다 자기 판정을 받아 하나의 상태로 접는다.

    latch는 값이 내려가도 풀리지 않는다 — 실기 노드가 경보를 자동 해제하지 않기
    때문이고, 푸는 방법은 리셋뿐이다.
    """
    conditions = frozenset(
        found
        for channel, level in levels.items()
        if (found := channel.spec.condition_of(level)) is not None
    )
    alarming = any(channel.spec.alarms(level) for channel, level in levels.items())
    still_latched = latched or alarming
    return NodeVerdict(
        state=AlertState.ALARM if still_latched else AlertState.from_conditions(conditions),
        conditions=conditions,
        water=Condition.WATER in conditions,
        latched=still_latched,
    )
