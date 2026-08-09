"""값 객체 단위 테스트. 외부 의존 0."""

from __future__ import annotations

import pytest

from app.domain.frames import Coordinates
from app.domain.value_objects import AlertState, DeviceId, GasChannel, SignatureFlags


class TestDeviceId:
    def test_empty_hw_id_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어 있을 수 없다"):
            DeviceId("")


class TestAlertState:
    def test_alarm_is_not_auto_clearable(self) -> None:
        assert AlertState.ALARM.is_auto_clearable is False
        assert AlertState.WATCH.is_auto_clearable is True

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


class TestGasChannel:
    def test_co_has_no_solo_promotion_path(self) -> None:
        assert GasChannel.CO.can_promote_alone is False
        assert GasChannel.VOC.can_promote_alone is True
        assert GasChannel.H2.can_promote_alone is True


class TestSignatureFlags:
    def test_all_three_required_for_completeness(self) -> None:
        """크기 단독 판정 금지 (gas-detection-algorithm-design.md P5)."""
        assert SignatureFlags(rise=True, hold=True, no_recover=True, hold_s=30).is_complete
        assert not SignatureFlags(rise=True, hold=False, no_recover=True, hold_s=30).is_complete


class TestCoordinates:
    @pytest.mark.parametrize(("lat", "lon"), [(91.0, 0.0), (-91.0, 0.0)])
    def test_out_of_range_latitude_rejected(self, lat: float, lon: float) -> None:
        with pytest.raises(ValueError, match="lat 범위"):
            Coordinates(lat=lat, lon=lon)

    def test_out_of_range_longitude_rejected(self) -> None:
        with pytest.raises(ValueError, match="lon 범위"):
            Coordinates(lat=0.0, lon=181.0)
