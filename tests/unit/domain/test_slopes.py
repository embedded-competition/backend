"""서버가 유도하는 변화율 — 노드가 기울기를 보내지 않는 동안의 대역이다."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, DeviceId
from tests.builders import a_frame

WITHIN = timedelta(minutes=15)


class TestSlopeDerivation:
    def test_first_ever_frame_has_nothing_to_compare(self, now: datetime) -> None:
        frame = a_frame(now, values={Measure.CO_DEV: 100.0})

        filled = frame.with_slopes_since(None, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) is None

    def test_rate_is_per_minute(self, now: datetime) -> None:
        before = a_frame(now, values={Measure.CO_DEV: 100.0})
        after = a_frame(now + timedelta(seconds=30), values={Measure.CO_DEV: 160.0})

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) == pytest.approx(120.0)

    def test_falling_value_gives_a_negative_rate(self, now: datetime) -> None:
        before = a_frame(now, values={Measure.CO_DEV: 160.0})
        after = a_frame(now + timedelta(minutes=1), values={Measure.CO_DEV: 100.0})

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) == pytest.approx(-60.0)

    def test_every_channel_with_a_slope_slot_is_filled(self, now: datetime) -> None:
        values = {
            Measure.CO_DEV: 100.0,
            Measure.H2_DEV: 100.0,
            Measure.VOC_DEV: 100.0,
            Measure.PRESSURE_DEV: 100.0,
            Measure.WATER_LEVEL: 100.0,
        }
        before = a_frame(now, values=values)
        after = a_frame(now + timedelta(minutes=1), values={k: v + 10 for k, v in values.items()})

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) == pytest.approx(10.0)
        assert filled.value(Measure.H2_SLOPE) == pytest.approx(10.0)
        assert filled.value(Measure.VOC_SLOPE) == pytest.approx(10.0)
        assert filled.value(Measure.PRESSURE_RATE) == pytest.approx(10.0)

    def test_a_channel_missing_on_either_side_gets_no_rate(self, now: datetime) -> None:
        before = a_frame(now, values={Measure.CO_DEV: 100.0})
        after = a_frame(
            now + timedelta(minutes=1),
            values={Measure.CO_DEV: 110.0, Measure.H2_DEV: 200.0},
        )

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) == pytest.approx(10.0)
        assert filled.value(Measure.H2_SLOPE) is None


class TestSlopeRefusal:
    def test_a_gap_wider_than_the_window_is_not_a_rate(self, now: datetime) -> None:
        """그 침묵 동안 값이 무엇을 했는지 모른다 — 두 점을 이으면 거짓말이 된다."""
        before = a_frame(now, values={Measure.CO_DEV: 100.0})
        after = a_frame(now + WITHIN + timedelta(seconds=1), values={Measure.CO_DEV: 900.0})

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) is None

    def test_out_of_order_frames_produce_no_rate(self, now: datetime) -> None:
        newer = a_frame(now + timedelta(minutes=1), values={Measure.CO_DEV: 100.0})
        older = a_frame(now, values={Measure.CO_DEV: 160.0})

        filled = older.with_slopes_since(newer, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) is None

    def test_a_slope_the_node_sent_is_left_alone(self, now: datetime) -> None:
        """프레임 v2가 signature를 실어 오면 노드 쪽이 더 나은 값이다."""
        before = a_frame(now, values={Measure.CO_DEV: 100.0})
        after = a_frame(
            now + timedelta(minutes=1),
            values={Measure.CO_DEV: 160.0, Measure.CO_SLOPE: 2.4},
        )

        filled = after.with_slopes_since(before, within=WITHIN)

        assert filled.value(Measure.CO_SLOPE) == pytest.approx(2.4)


def test_frame_identity_is_kept(now: datetime) -> None:
    """유도한 값을 얹느라 판정이나 신원이 바뀌면 안 된다."""
    before = a_frame(now, values={Measure.CO_DEV: 100.0})
    after = a_frame(
        now + timedelta(minutes=1),
        state=AlertState.WATCH,
        values={Measure.CO_DEV: 160.0},
    )

    filled = after.with_slopes_since(before, within=WITHIN)

    assert filled.state is AlertState.WATCH
    assert filled.hw_id == DeviceId("44bd8d239c28")
    assert filled.measured_at == after.measured_at
