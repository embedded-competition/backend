"""텔레메트리 조회 유스케이스. 시간당 집계는 원본 스캔으로 계산한다."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from app.domain.models import Device, Event, Reading
from app.domain.ports import Clock
from app.domain.repository import (
    DeviceRepository,
    EventRepository,
    ReadingRepository,
)
from app.domain.value_objects import AlertState, GasChannel

# 하루치 원본 상한. 5분 주기면 288행이므로 여유를 두되 무제한은 두지 않는다.
_DAY_SCAN_LIMIT = 2_000
_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class HourlySample:
    """시간당 집계 1건. 앱 통계 탭이 하루 24개를 받는다."""

    hour: str
    state: AlertState
    channels: dict[GasChannel, float | None]
    temp_c: float | None
    humidity_pct: float | None
    pressure_dev: float | None


@dataclass(frozen=True, slots=True)
class DailyHistory:
    day: date
    samples: list[HourlySample] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FleetComparison:
    fleet_size: int
    fleet_avg_level: AlertState
    my_level: AlertState
    my_multiplier: float


class TelemetryService:
    def __init__(
        self,
        *,
        devices: DeviceRepository,
        readings: ReadingRepository,
        events: EventRepository,
        clock: Clock,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._events = events
        self._clock = clock

    def latest(self, device: Device) -> Reading | None:
        return self._readings.latest(device.id or 0)

    def history(self, device: Device, day: date) -> DailyHistory:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        rows = self._readings.list_in_range(
            device.id or 0, start=start, end=end, limit=_DAY_SCAN_LIMIT
        )
        return DailyHistory(
            day=day,
            samples=_aggregate_hourly(rows),
            events=self._events.list_in_range(
                device.id or 0, start=start, end=end, limit=_EVENT_LIMIT
            ),
        )

    def events_since(self, device: Device, since: datetime) -> list[Event]:
        return self._events.list_since(device.id or 0, since=since, limit=_EVENT_LIMIT)

    def fleet_comparison(self, device: Device) -> FleetComparison:
        """등록된 전체 기기 대비 내 위치.

        1계정=1기기(O4)라 '내 기기 여러 대' 개념은 없다. 비교 모집단은
        서버에 등록된 활성 기기 전체다.
        """
        fleet = self._devices.list_active()
        my_level = device.last_state or AlertState.NORMAL
        severities = [_severity(d.last_state or AlertState.NORMAL) for d in fleet]
        avg_severity = sum(severities) / len(severities) if severities else 0.0
        my_severity = _severity(my_level)
        return FleetComparison(
            fleet_size=len(fleet),
            fleet_avg_level=_level_for(avg_severity),
            my_level=my_level,
            # 평균이 0(전부 정상)이면 배수가 정의되지 않는다 — 1.0으로 둔다.
            my_multiplier=round(my_severity / avg_severity, 1) if avg_severity > 0 else 1.0,
        )


_SEVERITY: dict[AlertState, int] = {
    AlertState.WARMUP: 0,
    AlertState.NORMAL: 0,
    AlertState.FAULT: 1,
    AlertState.WATCH: 2,
    AlertState.ALARM: 3,
}


def _severity(state: AlertState) -> int:
    return _SEVERITY[state]


def _level_for(severity: float) -> AlertState:
    if severity >= 2.5:
        return AlertState.ALARM
    if severity >= 1.5:
        return AlertState.WATCH
    if severity >= 0.5:
        return AlertState.FAULT
    return AlertState.NORMAL


def _aggregate_hourly(rows: list[Reading]) -> list[HourlySample]:
    """시간 버킷별 평균. 상태는 그 시간의 최악값 — 평균 내면 경보가 묻힌다."""
    buckets: dict[int, list[Reading]] = defaultdict(list)
    for row in rows:
        buckets[row.measured_at.hour].append(row)

    samples: list[HourlySample] = []
    for hour in sorted(buckets):
        bucket = buckets[hour]
        samples.append(
            HourlySample(
                hour=f"{hour:02d}:00",
                state=max(bucket, key=lambda r: _severity(r.state)).state,
                channels={
                    channel: _mean(
                        [
                            reading.channel(channel).deviation  # type: ignore[union-attr]
                            for reading in bucket
                            if reading.channel(channel) is not None
                        ]
                    )
                    for channel in GasChannel
                },
                temp_c=_mean([r.temp_c for r in bucket]),
                humidity_pct=_mean([r.humidity_pct for r in bucket]),
                pressure_dev=_mean([r.pressure_dev for r in bucket]),
            )
        )
    return samples


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 3)
