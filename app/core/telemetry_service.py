from __future__ import annotations

from dataclasses import dataclass

from app.core import fleet
from app.core.fleet import FleetComparison
from app.core.period_history import PeriodHistory
from app.core.period_summary import PeriodSummary
from app.domain.alerting import Event
from app.domain.device import Device
from app.domain.ports.clock import Clock
from app.domain.readings import ChannelPeak, Reading
from app.domain.value_objects import AlertState, GasChannel, Interval, Period
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository

_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class TelemetryService:
    devices: SqlAlchemyDeviceRepository
    readings: SqlAlchemyReadingRepository
    events: SqlAlchemyEventRepository
    clock: Clock

    def latest(self, device: Device) -> Reading | None:
        return self.readings.latest(device.key)

    def summary(self, device: Device, period: Period) -> PeriodSummary:
        live = period.includes(self.clock.now())
        return PeriodSummary(
            period=period,
            live=live,
            state=self._state_in(device, period),
            event_count=self.events.count_in_period(device.key, period),
            current=self.readings.latest(device.key) if live else None,
            peaks=self._peaks_in(device, period),
        )

    def history(self, device: Device, period: Period, interval: Interval) -> PeriodHistory:
        return PeriodHistory(
            period=period,
            interval=interval,
            bucket_count=period.bucket_count(interval),
            buckets=self.readings.bucket_maxima(device.key, period, interval),
            events=self.events.list_in_period(device.key, period, limit=_EVENT_LIMIT),
        )

    def events_in(self, device: Device, period: Period) -> list[Event]:
        return self.events.list_in_period(device.key, period, limit=_EVENT_LIMIT)

    def fleet_comparison(self, device: Device) -> FleetComparison:
        return fleet.compare(device, self.devices.list_active())

    def _state_in(self, device: Device, period: Period) -> AlertState:
        observed = self.readings.worst_state(device.key, period)
        if observed is not None:
            return observed
        return device.last_state or AlertState.WARMUP

    def _peaks_in(self, device: Device, period: Period) -> dict[GasChannel, ChannelPeak]:
        found = (
            (channel, self.readings.channel_peak(device.key, period, channel))
            for channel in GasChannel
        )
        return {channel: peak for channel, peak in found if peak is not None}
