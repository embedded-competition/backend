"""시간당 집계. 저장소·서비스를 모르는 순수 계산."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.core.severity import severity_of
from app.domain.models import Reading
from app.domain.value_objects import AlertState, GasChannel


@dataclass(frozen=True, slots=True)
class HourlySample:
    """시간당 집계 1건. 앱 통계 탭이 하루 24개까지 받는다."""

    hour: str
    state: AlertState
    channels: dict[GasChannel, float | None]
    temp_c: float | None
    humidity_pct: float | None
    pressure_dev: float | None


def aggregate_hourly(rows: list[Reading]) -> list[HourlySample]:
    """시간 버킷별 평균. 상태는 그 시간의 최악값 — 평균 내면 경보가 묻힌다."""
    buckets: dict[int, list[Reading]] = defaultdict(list)
    for row in rows:
        buckets[row.measured_at.hour].append(row)

    return [
        HourlySample(
            hour=f"{hour:02d}:00",
            state=max(bucket, key=lambda r: severity_of(r.state)).state,
            channels={channel: _mean(_deviations(bucket, channel)) for channel in GasChannel},
            temp_c=_mean([r.temp_c for r in bucket]),
            humidity_pct=_mean([r.humidity_pct for r in bucket]),
            pressure_dev=_mean([r.pressure_dev for r in bucket]),
        )
        for hour, bucket in sorted(buckets.items())
    ]


def _deviations(bucket: list[Reading], channel: GasChannel) -> list[float | None]:
    measurements = [reading.channel(channel) for reading in bucket]
    return [m.deviation for m in measurements if m is not None]


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 3)
