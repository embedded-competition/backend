"""모듈 자기 진단의 임계. 앱이 dBm을 받아 스스로 판정하면 서버와 어긋난다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.module_health import BatteryLevel, LinkQuality, SensorCheck
from app.domain.value_objects import Condition

_NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
_OFFLINE_AFTER = timedelta(minutes=15)


def _link(rssi: int | None, *, silent_for: timedelta | None) -> LinkQuality | None:
    return LinkQuality.of(
        rssi=rssi,
        last_seen_at=None if silent_for is None else _NOW - silent_for,
        now=_NOW,
        offline_after=_OFFLINE_AFTER,
    )


class TestLinkQuality:
    def test_never_heard_from_is_unknown_not_offline(self) -> None:
        """끊긴 것과 아직 안 온 것은 다른 사건이다."""
        assert _link(-50, silent_for=None) is None

    def test_silence_beats_signal_strength(self) -> None:
        """마지막 프레임이 아무리 강했어도 지금 안 오면 끊긴 것이다."""
        assert _link(-30, silent_for=timedelta(hours=1)) is LinkQuality.OFFLINE

    @pytest.mark.parametrize(
        ("rssi", "expected"),
        [
            (-22, LinkQuality.GOOD),
            (-100, LinkQuality.GOOD),
            (-101, LinkQuality.FAIR),
            (-115, LinkQuality.FAIR),
            (-116, LinkQuality.POOR),
            (-128, LinkQuality.POOR),
        ],
    )
    def test_thresholds(self, rssi: int, expected: LinkQuality) -> None:
        assert _link(rssi, silent_for=timedelta(minutes=1)) is expected

    def test_missing_rssi_while_alive_is_fair(self) -> None:
        """닿고는 있다. 얼마나 좋은지만 모른다."""
        assert _link(None, silent_for=timedelta(minutes=1)) is LinkQuality.FAIR


class TestSensorCheck:
    def test_no_observation_is_unknown(self) -> None:
        assert SensorCheck.of(None) is None

    def test_saturated_sensor_needs_service(self) -> None:
        assert SensorCheck.of(frozenset({Condition.SENSOR_FAULT})) is SensorCheck.FAULT

    def test_other_conditions_do_not_blame_the_sensor(self) -> None:
        """가스가 오르는 것은 센서가 멀쩡하다는 뜻이지 고장이 아니다."""
        assert SensorCheck.of(frozenset({Condition.CO_RISE, Condition.WATER})) is SensorCheck.OK

    def test_no_conditions_is_ok(self) -> None:
        assert SensorCheck.of(frozenset()) is SensorCheck.OK


class TestBatteryLevel:
    @pytest.mark.parametrize("percent", [-1, 101])
    def test_percent_out_of_range_is_rejected(self, percent: int) -> None:
        with pytest.raises(ValueError, match="percent"):
            BatteryLevel(percent=percent)

    def test_negative_days_left_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="days_left"):
            BatteryLevel(percent=50, days_left=-1)

    def test_days_left_may_be_unknown(self) -> None:
        assert BatteryLevel(percent=78).days_left is None
