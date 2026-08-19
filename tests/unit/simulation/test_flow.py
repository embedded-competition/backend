"""흐름 제어의 규칙 — 눈금 범위, 선형 진행, 지시를 겹쳐 줬을 때의 출발점."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.simulation.channels import LEVEL_MAX, Level, NodeChannel
from app.simulation.flow import Direction, FlowCommand, Ramp, SensorFlow


class TestLevel:
    def test_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="레벨이"):
            Level(LEVEL_MAX + 1)

    def test_clamps_only_where_asked(self) -> None:
        assert Level.clamped(-50.0) == Level(0.0)
        assert Level.clamped(5_000.0) == Level(LEVEL_MAX)

    def test_saturation_is_the_top_of_the_scale(self) -> None:
        assert Level(LEVEL_MAX).is_saturated
        assert not Level(LEVEL_MAX - 0.1).is_saturated


class TestDirection:
    def test_rise_and_fall_are_opposites(self) -> None:
        origin = Level(200.0)
        assert Direction.RISE.applied(origin, 100.0) == Level(300.0)
        assert Direction.FALL.applied(origin, 100.0) == Level(100.0)

    def test_fall_below_zero_stops_at_zero(self) -> None:
        assert Direction.FALL.applied(Level(30.0), 500.0) == Level(0.0)


class TestFlowCommand:
    def test_rejects_non_positive_amount(self) -> None:
        with pytest.raises(ValueError, match="변화량"):
            FlowCommand(direction=Direction.RISE, amount=0.0, over_seconds=10.0)

    def test_rejects_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="소요 시간"):
            FlowCommand(direction=Direction.RISE, amount=10.0, over_seconds=-1.0)

    def test_zero_seconds_is_immediate(self) -> None:
        command = FlowCommand(direction=Direction.RISE, amount=10.0, over_seconds=0.0)
        assert command.is_immediate


class TestRamp:
    def test_rejects_zero_length(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="램프 길이"):
            Ramp(origin=Level(0.0), target=Level(100.0), started_at=now, seconds=0.0)

    def test_interpolates_linearly(self, now: datetime) -> None:
        ramp = Ramp(origin=Level(100.0), target=Level(500.0), started_at=now, seconds=40.0)

        assert ramp.level_at(now) == Level(100.0)
        assert ramp.level_at(now + timedelta(seconds=10)) == Level(200.0)
        assert ramp.level_at(now + timedelta(seconds=40)) == Level(500.0)

    def test_holds_the_target_after_it_ends(self, now: datetime) -> None:
        ramp = Ramp(origin=Level(100.0), target=Level(500.0), started_at=now, seconds=40.0)
        late = now + timedelta(minutes=5)

        assert ramp.level_at(late) == Level(500.0)
        assert ramp.finished_by(late)
        assert ramp.remaining_seconds(late) == 0.0


class TestSensorFlow:
    def test_starts_at_the_channel_baseline(self) -> None:
        flow = SensorFlow.at_baseline(NodeChannel.CO)

        assert flow.level == NodeChannel.CO.spec.baseline
        assert flow.target is None

    def test_immediate_command_skips_the_ramp(self, now: datetime) -> None:
        flow = SensorFlow.at_baseline(NodeChannel.CO)

        flow.steer(FlowCommand(direction=Direction.RISE, amount=300.0, over_seconds=0.0), at=now)

        assert flow.level == Level(380.0)
        assert flow.remaining_seconds(now) is None

    def test_new_command_departs_from_where_the_flow_is_now(self, now: datetime) -> None:
        """진행 중인 흐름을 덮어쓸 때 원래 출발점으로 되돌아가면 값이 튄다."""
        flow = SensorFlow.at_baseline(NodeChannel.CO)
        flow.steer(FlowCommand(direction=Direction.RISE, amount=400.0, over_seconds=40.0), at=now)
        halfway = now + timedelta(seconds=20)

        flow.steer(
            FlowCommand(direction=Direction.FALL, amount=80.0, over_seconds=10.0), at=halfway
        )

        assert flow.level_at(halfway) == Level(280.0)
        assert flow.target == Level(200.0)

    def test_settle_drops_the_ramp_once_it_lands(self, now: datetime) -> None:
        flow = SensorFlow.at_baseline(NodeChannel.CO)
        flow.steer(FlowCommand(direction=Direction.RISE, amount=400.0, over_seconds=10.0), at=now)

        assert flow.settle(now + timedelta(seconds=5)) == Level(280.0)
        assert flow.target == Level(480.0)

        assert flow.settle(now + timedelta(seconds=10)) == Level(480.0)
        assert flow.target is None

    def test_reset_returns_to_baseline(self, now: datetime) -> None:
        flow = SensorFlow.at_baseline(NodeChannel.CO)
        flow.steer(FlowCommand(direction=Direction.RISE, amount=400.0, over_seconds=40.0), at=now)

        flow.reset()

        assert flow.level == NodeChannel.CO.spec.baseline
        assert flow.target is None
