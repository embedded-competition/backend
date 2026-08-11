from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from app.domain.exceptions.invalid_interval import InvalidInterval

_TEXT = re.compile(r"^([1-9][0-9]*)([mhd])$")
_UNIT_SECONDS = {"m": 60, "h": 3_600, "d": 86_400}
_SUFFIX_WIDEST_FIRST = ("d", "h", "m")

_MINIMUM_SECONDS = 60
_MAXIMUM_SECONDS = 31 * 86_400


@dataclass(frozen=True, slots=True)
class Interval:
    seconds: int

    def __post_init__(self) -> None:
        if not _MINIMUM_SECONDS <= self.seconds <= _MAXIMUM_SECONDS:
            raise InvalidInterval(f"눈금은 1분 이상 31일 이하여야 한다: {self.seconds}초")

    @classmethod
    def parse(cls, text: str) -> Interval:
        matched = _TEXT.match(text)
        if matched is None:
            raise InvalidInterval(f"눈금 형식이 아니다: {text!r} — 30m·2h·1d 처럼 적는다")
        amount, unit = matched.groups()
        return cls(int(amount) * _UNIT_SECONDS[unit])

    @property
    def delta(self) -> timedelta:
        return timedelta(seconds=self.seconds)

    def __str__(self) -> str:
        for suffix in _SUFFIX_WIDEST_FIRST:
            unit = _UNIT_SECONDS[suffix]
            if self.seconds % unit == 0:
                return f"{self.seconds // unit}{suffix}"
        return f"{self.seconds}s"
