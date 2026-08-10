from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.core.severity import severity_of
from app.domain.measurements import Measure
from app.domain.readings import Reading
from app.domain.value_objects import AlertState


@dataclass(frozen=True, slots=True)
class HourlySample:
    hour: str
    state: AlertState
    values: dict[Measure, float] = field(default_factory=dict)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)


def aggregate_hourly(rows: list[Reading]) -> list[HourlySample]:
    buckets: dict[int, list[Reading]] = defaultdict(list)
    for row in rows:
        buckets[row.measured_at.hour].append(row)

    return [
        HourlySample(
            hour=f"{hour:02d}:00",
            state=max(bucket, key=lambda r: severity_of(r.state)).state,
            values=_mean_values(bucket),
        )
        for hour, bucket in sorted(buckets.items())
    ]


def _mean_values(bucket: list[Reading]) -> dict[Measure, float]:
    totals: dict[Measure, list[float]] = defaultdict(list)
    for reading in bucket:
        for measure, value in reading.frame.values.items():
            totals[measure].append(value)
    return {measure: round(sum(values) / len(values), 3) for measure, values in totals.items()}
