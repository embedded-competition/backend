"""값 객체 단위 테스트. 외부 의존 0."""

from __future__ import annotations

import pytest

from app.domain.frames import Coordinates
from app.domain.value_objects import AlertState, Condition, DeviceId, Stage


class TestDeviceId:
    def test_empty_hw_id_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어 있을 수 없다"):
            DeviceId("")


class TestAlertState:
    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            (AlertState.NORMAL, False),
            (AlertState.WARMUP, False),
            (AlertState.WATCH, True),
            (AlertState.ALARM, True),
            (AlertState.FAULT, True),
        ],
    )
    def test_dispatch_targets(self, state: AlertState, expected: bool) -> None:
        assert state.needs_dispatch is expected

    @pytest.mark.parametrize(
        ("conditions", "expected"),
        [
            (frozenset(), AlertState.NORMAL),
            (frozenset({Condition.CO_RISE}), AlertState.WATCH),
            (frozenset({Condition.SENSOR_FAULT}), AlertState.FAULT),
            (frozenset({Condition.SENSOR_FAULT, Condition.SENSOR_FAULT}), AlertState.FAULT),
            (frozenset({Condition.SENSOR_FAULT, Condition.WATER}), AlertState.WATCH),
            (
                frozenset({Condition.CO_RISE, Condition.H2_RISE, Condition.WATER}),
                AlertState.WATCH,
            ),
            (frozenset({Condition.UNKNOWN}), AlertState.WATCH),
            (frozenset({Condition.UNKNOWN, Condition.SENSOR_FAULT}), AlertState.WATCH),
        ],
    )
    def test_from_conditions(self, conditions: frozenset[Condition], expected: AlertState) -> None:
        assert AlertState.from_conditions(conditions) is expected


class TestStage:
    """단계는 화면 진행 바의 SSOT다. 앱이 집합에서 역산하면 서버와 어긋난다."""

    @pytest.mark.parametrize(
        ("conditions", "expected"),
        [
            (frozenset(), Stage.NONE),
            (frozenset({Condition.CO_RISE}), Stage.GAS_LEAK),
            (frozenset({Condition.H2_RISE}), Stage.GAS_LEAK),
            (frozenset({Condition.VOC_RISE}), Stage.GAS_LEAK),
            (frozenset({Condition.CO_RISE, Condition.PRESSURE_RISE}), Stage.GAS_LEAK),
            (frozenset({Condition.WATER}), Stage.NONE),
            (frozenset({Condition.SENSOR_FAULT}), Stage.NONE),
        ],
    )
    def test_decidable_conditions(self, conditions: frozenset[Condition], expected: Stage) -> None:
        assert Stage.from_conditions(conditions) is expected

    @pytest.mark.parametrize(
        "conditions",
        [
            frozenset({Condition.PRESSURE_RISE}),
            frozenset({Condition.UNKNOWN}),
            frozenset({Condition.PRESSURE_RISE, Condition.SENSOR_FAULT}),
        ],
    )
    def test_undecidable_is_none_not_stage_none(self, conditions: frozenset[Condition]) -> None:
        """'모른다'와 '이상 없음'은 다른 사건이다."""
        assert Stage.from_conditions(conditions) is None

    def test_water_and_fault_are_not_on_the_fire_axis(self) -> None:
        """침수·센서고장은 화재 진행이 아니라 status가 답할 몫이다."""
        assert Stage.from_conditions(frozenset({Condition.WATER, Condition.SENSOR_FAULT})) is (
            Stage.NONE
        )


class TestCoordinates:
    @pytest.mark.parametrize(("lat", "lon"), [(91.0, 0.0), (-91.0, 0.0)])
    def test_out_of_range_latitude_rejected(self, lat: float, lon: float) -> None:
        with pytest.raises(ValueError, match="lat 범위"):
            Coordinates(lat=lat, lon=lon)

    def test_out_of_range_longitude_rejected(self) -> None:
        with pytest.raises(ValueError, match="lon 범위"):
            Coordinates(lat=0.0, lon=181.0)
