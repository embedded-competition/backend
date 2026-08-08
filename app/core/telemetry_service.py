"""텔레메트리 조회 유스케이스. 집계·비교 계산은 aggregation·fleet에 위임한다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from app.core import fleet
from app.core.aggregation import HourlySample, aggregate_hourly
from app.core.fleet import FleetComparison
from app.domain.models import Device, Event, Reading
from app.domain.repository import DeviceRepository, EventRepository, ReadingRepository

# 하루치 원본 상한. 5분 주기면 288행이므로 여유를 두되 무제한은 두지 않는다.
_DAY_SCAN_LIMIT = 2_000
_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class DailyHistory:
    day: date
    samples: list[HourlySample] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


class TelemetryService:
    def __init__(
        self,
        *,
        devices: DeviceRepository,
        readings: ReadingRepository,
        events: EventRepository,
    ) -> None:
        self._devices = devices
        self._readings = readings
        self._events = events

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
            samples=aggregate_hourly(rows),
            events=self._events.list_in_range(
                device.id or 0, start=start, end=end, limit=_EVENT_LIMIT
            ),
        )

    def events_since(self, device: Device, since: datetime) -> list[Event]:
        return self._events.list_since(device.id or 0, since=since, limit=_EVENT_LIMIT)

    def fleet_comparison(self, device: Device) -> FleetComparison:
        return fleet.compare(device, self._devices.list_active())
