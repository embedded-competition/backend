"""시뮬레이터 payload — 판정을 실어 나르고, 읽을 수 없으면 프레임 오류로 드러난다."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.exceptions import FrameFieldError
from app.domain.value_objects import AlertState, Condition
from app.simulation.channels import NodeChannel
from app.simulation.flow import Direction, FlowCommand
from app.simulation.node import SimulatedNode
from app.simulation.payload import decode, encode

MAC = "00:00:00:00:00:07"


def test_round_trip_preserves_the_verdict(now: datetime) -> None:
    node = SimulatedNode.at_baseline(MAC)
    node.steer(
        NodeChannel.CO,
        FlowCommand(direction=Direction.RISE, amount=800.0, over_seconds=0.0),
        at=now,
    )
    original = node.emit(now)

    restored = decode(encode(original), now)

    assert restored.state is AlertState.ALARM
    assert restored.conditions == frozenset({Condition.CO_RISE})
    assert restored.latched
    assert restored.values == original.values
    assert restored.location == original.location
    assert str(restored.hw_id) == "000000000007"


def test_measured_at_comes_from_reception(now: datetime) -> None:
    """노드에 시계가 없다 — payload에 측정 시각을 싣지 않는다."""
    frame = SimulatedNode.at_baseline(MAC).emit(now)

    assert b"measured_at" not in encode(frame)
    assert decode(encode(frame), now).measured_at == now


@pytest.mark.parametrize(
    "payload",
    [b"", b"not json", b"{}", b'{"hw_id":"000000000007"}'],
)
def test_unreadable_payload_is_a_frame_error(payload: bytes, now: datetime) -> None:
    with pytest.raises(FrameFieldError):
        decode(payload, now)
