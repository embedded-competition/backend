"""조회 구간.

경계를 틀리면 화면이 조용히 빈 칸을 그린다 — 값이 없는 것과 구분되지 않는다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.exceptions import InvalidInterval, InvalidPeriod
from app.domain.value_objects import Interval, Period

NOW = datetime(2026, 8, 4, tzinfo=UTC)


class TestValidation:
    def test_rejects_reversed_bounds(self) -> None:
        with pytest.raises(InvalidPeriod):
            Period(NOW, NOW - timedelta(hours=1))

    def test_rejects_zero_length(self) -> None:
        with pytest.raises(InvalidPeriod):
            Period(NOW, NOW)

    def test_rejects_span_beyond_a_year(self) -> None:
        with pytest.raises(InvalidPeriod):
            Period(NOW, NOW + timedelta(days=400))

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            Period(datetime(2026, 8, 4), NOW + timedelta(days=1))  # noqa: DTZ001


class TestMembership:
    def test_start_is_included_and_end_is_not(self) -> None:
        period = Period(NOW, NOW + timedelta(hours=1))

        assert period.includes(NOW) is True
        assert period.includes(NOW + timedelta(minutes=59)) is True
        assert period.includes(NOW + timedelta(hours=1)) is False


class TestBuckets:
    def test_counts_whole_and_partial_slots(self) -> None:
        period = Period(NOW, NOW + timedelta(hours=7))

        assert period.bucket_count(Interval.parse("2h")) == 4

    def test_rejects_a_tick_that_explodes_the_response(self) -> None:
        period = Period(NOW, NOW + timedelta(days=90))

        with pytest.raises(InvalidInterval):
            period.bucket_count(Interval.parse("1m"))

    def test_bucket_start_walks_by_the_tick(self) -> None:
        period = Period(NOW, NOW + timedelta(days=1))
        interval = Interval.parse("2h")

        assert period.bucket_start(0, interval) == NOW
        assert period.bucket_start(3, interval) == NOW + timedelta(hours=6)
