"""등록 기기 전체 대비 내 위치. 앱 비교 화면의 유일한 근거다."""

from __future__ import annotations

import pytest

from app.core.fleet import compare
from app.domain.device import Device
from app.domain.value_objects import AlertState
from tests.builders import a_device


def _fleet(*states: AlertState | None) -> list[Device]:
    return [
        a_device(public_id=f"dev_{index}", last_state=state) for index, state in enumerate(states)
    ]


class TestFleetSize:
    def test_counts_every_device_in_the_population(self) -> None:
        assert compare(a_device(), _fleet(AlertState.NORMAL, AlertState.WATCH)).fleet_size == 2

    def test_empty_fleet_is_reported_as_zero(self) -> None:
        assert compare(a_device(), []).fleet_size == 0


class TestMyLevel:
    def test_uses_the_device_last_state(self) -> None:
        device = a_device(last_state=AlertState.ALARM)

        assert compare(device, _fleet(AlertState.NORMAL)).my_level is AlertState.ALARM

    def test_never_seen_device_reads_as_normal(self) -> None:
        """상태를 지어내지 않는다 — 관측이 없으면 정상으로 둔다."""
        assert compare(a_device(last_state=None), _fleet(AlertState.NORMAL)).my_level is (
            AlertState.NORMAL
        )


class TestMultiplier:
    def test_is_my_severity_over_the_fleet_average(self) -> None:
        # 평균 = (0 + 0 + 2) / 3 = 0.666…, 내 심각도 = 3 → 4.5
        result = compare(
            a_device(last_state=AlertState.ALARM),
            _fleet(AlertState.NORMAL, AlertState.NORMAL, AlertState.WATCH),
        )

        assert result.my_multiplier == pytest.approx(4.5)

    def test_all_normal_fleet_yields_one(self) -> None:
        """평균이 0이면 배수가 정의되지 않는다 — 무한대 대신 1.0."""
        result = compare(a_device(last_state=AlertState.NORMAL), _fleet(AlertState.NORMAL))

        assert result.my_multiplier == pytest.approx(1.0)

    def test_empty_fleet_yields_one(self) -> None:
        assert compare(a_device(last_state=AlertState.ALARM), []).my_multiplier == pytest.approx(
            1.0
        )


class TestFleetAverageLevel:
    def test_average_severity_maps_back_to_a_state(self) -> None:
        # 평균 = (3 + 2) / 2 = 2.5 → ALARM 하한
        result = compare(a_device(), _fleet(AlertState.ALARM, AlertState.WATCH))

        assert result.fleet_avg_level is AlertState.ALARM

    def test_quiet_fleet_reads_as_normal(self) -> None:
        assert compare(
            a_device(), _fleet(AlertState.NORMAL, AlertState.NORMAL)
        ).fleet_avg_level is (AlertState.NORMAL)
