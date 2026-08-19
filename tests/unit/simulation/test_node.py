"""노드가 내리는 판정 — 어느 눈금이 어떤 화면을 만드는가."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, Condition
from app.simulation.channels import LEVEL_MAX, Level, NodeChannel
from app.simulation.flow import Direction, FlowCommand
from app.simulation.judgement import judge
from app.simulation.node import (
    SIMULATED_FRAME_VERSION,
    TEST_MAC_PREFIX,
    SimulatedNode,
    simulated_macs,
)

MAC = "00:00:00:00:00:01"


def _immediately(direction: Direction, amount: float) -> FlowCommand:
    return FlowCommand(direction=direction, amount=amount, over_seconds=0.0)


def _raised_to(channel: NodeChannel, level: float, now: datetime) -> SimulatedNode:
    node = SimulatedNode.at_baseline(MAC)
    node.steer(channel, _immediately(Direction.RISE, level), at=now)
    return node


class TestSimulatedMacs:
    def test_numbers_from_one_under_the_test_prefix(self) -> None:
        assert simulated_macs(3) == (
            f"{TEST_MAC_PREFIX}01",
            f"{TEST_MAC_PREFIX}02",
            f"{TEST_MAC_PREFIX}03",
        )

    def test_hw_id_is_the_mac_without_separators(self) -> None:
        assert str(SimulatedNode.at_baseline(MAC).hw_id) == "000000000001"


class TestJudgement:
    def test_baseline_is_normal(self, now: datetime) -> None:
        verdict = SimulatedNode.at_baseline(MAC).verdict_at(now)

        assert verdict.state is AlertState.NORMAL
        assert verdict.conditions == frozenset()

    def test_crossing_watch_raises_that_channel_condition(self, now: datetime) -> None:
        verdict = _raised_to(NodeChannel.CO, 400.0, now).verdict_at(now)

        assert verdict.state is AlertState.WATCH
        assert verdict.conditions == frozenset({Condition.CO_RISE})

    def test_latch_survives_the_value_coming_back_down(self, now: datetime) -> None:
        """latch는 틱이 건다 — 노드가 경보를 실제로 보낸 순간부터 붙잡는다."""
        node = _raised_to(NodeChannel.H2, 800.0, now)
        assert node.emit(now).state is AlertState.ALARM

        node.steer(NodeChannel.H2, _immediately(Direction.FALL, 800.0), at=now)
        fallen = node.verdict_at(now)

        assert fallen.state is AlertState.ALARM
        assert fallen.latched
        assert fallen.conditions == frozenset()

    def test_a_level_that_never_ticked_does_not_latch(self, now: datetime) -> None:
        node = _raised_to(NodeChannel.H2, 800.0, now)

        node.steer(NodeChannel.H2, _immediately(Direction.FALL, 800.0), at=now)

        assert node.verdict_at(now).state is AlertState.NORMAL

    def test_reset_releases_the_latch(self, now: datetime) -> None:
        node = _raised_to(NodeChannel.H2, 800.0, now)
        node.emit(now)

        node.reset()

        assert node.verdict_at(now).state is AlertState.NORMAL

    def test_saturation_is_a_sensor_fault_not_an_alarm(self, now: datetime) -> None:
        verdict = _raised_to(NodeChannel.CO, LEVEL_MAX, now).verdict_at(now)

        assert verdict.state is AlertState.FAULT
        assert verdict.conditions == frozenset({Condition.SENSOR_FAULT})

    def test_water_never_reaches_alarm(self, now: datetime) -> None:
        verdict = _raised_to(NodeChannel.WATER, 900.0, now).verdict_at(now)

        assert verdict.state is AlertState.WATCH
        assert verdict.water
        assert verdict.conditions == frozenset({Condition.WATER})

    def test_fault_mixed_with_risk_is_not_swallowed(self, now: datetime) -> None:
        verdict = judge(
            {NodeChannel.CO: Level(LEVEL_MAX), NodeChannel.WATER: Level(400.0)},
            latched=False,
        )

        assert verdict.state is AlertState.WATCH
        assert verdict.conditions == frozenset({Condition.SENSOR_FAULT, Condition.WATER})


class TestEmit:
    def test_frame_carries_the_verdict_and_every_channel(self, now: datetime) -> None:
        node = _raised_to(NodeChannel.VOC, 500.0, now)

        frame = node.emit(now)

        assert frame.version == SIMULATED_FRAME_VERSION
        assert frame.state is AlertState.WATCH
        assert frame.conditions == frozenset({Condition.VOC_RISE})
        assert frame.value(Measure.VOC_DEV) == 620.0
        assert set(frame.values) == {channel.spec.measure for channel in NodeChannel}

    def test_emit_confirms_the_level_the_ramp_reached(self, now: datetime) -> None:
        node = SimulatedNode.at_baseline(MAC)
        node.steer(
            NodeChannel.CO,
            FlowCommand(direction=Direction.RISE, amount=400.0, over_seconds=10.0),
            at=now,
        )

        node.emit(now)

        assert node.flows[NodeChannel.CO].level == NodeChannel.CO.spec.baseline

    @pytest.mark.parametrize("channel", list(NodeChannel))
    def test_every_channel_stays_inside_the_wire_scale(
        self, channel: NodeChannel, now: datetime
    ) -> None:
        frame = _raised_to(channel, 5_000.0, now).emit(now)

        assert frame.values[channel.spec.measure] == LEVEL_MAX
