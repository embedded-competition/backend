"""값 객체 단위 테스트. 외부 의존 0."""

from __future__ import annotations

import pytest

from app.domain.frames import Coordinates
from app.domain.value_objects import AlertState, DeviceId


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


class TestCoordinates:
    @pytest.mark.parametrize(("lat", "lon"), [(91.0, 0.0), (-91.0, 0.0)])
    def test_out_of_range_latitude_rejected(self, lat: float, lon: float) -> None:
        with pytest.raises(ValueError, match="lat 범위"):
            Coordinates(lat=lat, lon=lon)

    def test_out_of_range_longitude_rejected(self) -> None:
        with pytest.raises(ValueError, match="lon 범위"):
            Coordinates(lat=0.0, lon=181.0)
