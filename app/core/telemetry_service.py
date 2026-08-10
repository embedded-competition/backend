from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from app.core import fleet
from app.core.aggregation import HourlySample, aggregate_hourly
from app.core.fleet import FleetComparison
from app.domain.alerting import Event
from app.domain.device import Device
from app.domain.readings import Reading
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository

_DAY_SCAN_LIMIT = 2_000
_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class DailyHistory:
    day: date
    samples: list[HourlySample] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TelemetryService:
    devices: SqlAlchemyDeviceRepository
    readings: SqlAlchemyReadingRepository
    events: SqlAlchemyEventRepository

    def latest(self, device: Device) -> Reading | None:
        return self.readings.latest(device.key)

    def history(self, device: Device, day: date) -> DailyHistory:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        rows = self.readings.list_in_range(device.key, start=start, end=end, limit=_DAY_SCAN_LIMIT)
        return DailyHistory(
            day=day,
            samples=aggregate_hourly(rows),
            events=self.events.list_in_range(device.key, start=start, end=end, limit=_EVENT_LIMIT),
        )

    def events_since(self, device: Device, since: datetime) -> list[Event]:
        return self.events.list_since(device.key, since=since, limit=_EVENT_LIMIT)

    def fleet_comparison(self, device: Device) -> FleetComparison:
        return fleet.compare(device, self.devices.list_active())
