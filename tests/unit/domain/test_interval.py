"""집계 눈금. 허용값을 닫힌 집합으로 좁혀 정규화·에코백 필요를 없앤다."""

from __future__ import annotations

import pytest

from app.domain.value_objects import Interval


class TestSeconds:
    @pytest.mark.parametrize(
        ("interval", "seconds"),
        [
            (Interval.M5, 300),
            (Interval.M15, 900),
            (Interval.M30, 1_800),
            (Interval.H1, 3_600),
            (Interval.H2, 7_200),
            (Interval.H6, 21_600),
            (Interval.H12, 43_200),
            (Interval.D1, 86_400),
        ],
    )
    def test_each_member_knows_its_length(self, interval: Interval, seconds: int) -> None:
        assert interval.seconds == seconds
        assert interval.delta.total_seconds() == seconds


class TestClosedSet:
    def test_unknown_value_is_rejected(self) -> None:
        """형식 검증은 닫힌 집합이라는 사실 자체가 한다 — API 경계는 pydantic이 막는다."""
        with pytest.raises(ValueError, match="120m"):
            Interval("120m")
