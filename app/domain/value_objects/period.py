from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.exceptions.invalid_interval import InvalidInterval
from app.domain.exceptions.invalid_period import InvalidPeriod
from app.domain.timestamps import require_aware
from app.domain.value_objects.interval import Interval

_MAXIMUM_SPAN = timedelta(days=366)
_MAXIMUM_BUCKETS = 1_000


@dataclass(frozen=True, slots=True)
class Period:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", require_aware(self.start, "start"))
        object.__setattr__(self, "end", require_aware(self.end, "end"))
        if self.end <= self.start:
            raise InvalidPeriod(f"끝은 시작보다 뒤여야 한다: {self.start} ~ {self.end}")
        if self.span > _MAXIMUM_SPAN:
            raise InvalidPeriod(f"구간은 366일을 넘을 수 없다: {self.span.days}일")

    @property
    def span(self) -> timedelta:
        return self.end - self.start

    def includes(self, moment: datetime) -> bool:
        return self.start <= require_aware(moment, "moment") < self.end

    def bucket_count(self, interval: Interval) -> int:
        count = -(-int(self.span.total_seconds()) // interval.seconds)
        if count > _MAXIMUM_BUCKETS:
            raise InvalidInterval(
                f"버킷이 너무 많다: {count}개 (상한 {_MAXIMUM_BUCKETS}). 눈금을 키워라"
            )
        return count

    def bucket_start(self, index: int, interval: Interval) -> datetime:
        return self.start + interval.delta * index
