"""집계 눈금 파싱.

앱이 보내는 문자열이 그대로 질의 폭이 된다 — 형식이 새면 버킷 경계가 샌다.
"""

from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidInterval
from app.domain.value_objects import Interval


class TestParse:
    @pytest.mark.parametrize(
        ("text", "seconds"),
        [("1m", 60), ("30m", 1_800), ("2h", 7_200), ("1d", 86_400), ("7d", 604_800)],
    )
    def test_accepts_minute_hour_day(self, text: str, seconds: int) -> None:
        assert Interval.parse(text).seconds == seconds

    @pytest.mark.parametrize("text", ["", "2", "h", "0h", "-2h", "2주", "2H", "1.5h", " 2h"])
    def test_rejects_anything_else(self, text: str) -> None:
        with pytest.raises(InvalidInterval):
            Interval.parse(text)

    def test_rejects_below_one_minute(self) -> None:
        with pytest.raises(InvalidInterval):
            Interval(30)

    def test_rejects_beyond_thirty_one_days(self) -> None:
        with pytest.raises(InvalidInterval):
            Interval(32 * 86_400)


class TestRoundTrip:
    @pytest.mark.parametrize("text", ["30m", "2h", "1d", "7d"])
    def test_renders_back_to_what_was_parsed(self, text: str) -> None:
        """응답의 range.interval이 요청과 달라 보이면 앱이 캐시 키를 잘못 잡는다."""
        assert str(Interval.parse(text)) == text

    def test_prefers_the_widest_unit(self) -> None:
        assert str(Interval(86_400)) == "1d"
        assert str(Interval(7_200)) == "2h"
