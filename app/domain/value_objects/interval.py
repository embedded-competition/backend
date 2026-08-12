from __future__ import annotations

from datetime import timedelta
from enum import StrEnum


class Interval(StrEnum):
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H6 = "6h"
    H12 = "12h"
    D1 = "1d"

    @property
    def seconds(self) -> int:
        return _SECONDS[self]

    @property
    def delta(self) -> timedelta:
        return timedelta(seconds=self.seconds)


_SECONDS: dict[Interval, int] = {
    Interval.M5: 5 * 60,
    Interval.M15: 15 * 60,
    Interval.M30: 30 * 60,
    Interval.H1: 3_600,
    Interval.H2: 2 * 3_600,
    Interval.H6: 6 * 3_600,
    Interval.H12: 12 * 3_600,
    Interval.D1: 86_400,
}
