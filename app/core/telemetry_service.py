from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.period_history import PeriodHistory
from app.core.period_summary import PeriodSummary
from app.domain.alerting import Event
from app.domain.device import Device
from app.domain.frames import Coordinates
from app.domain.measurements import SLOPE_BY_DEVIATION, Measure
from app.domain.ports.clock import Clock
from app.domain.readings import ChannelPeak, Reading
from app.domain.value_objects import Interval, Period
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository

_EVENT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class DeviceLocation:
    coordinates: Coordinates
    at: datetime


@dataclass(frozen=True, slots=True)
class TelemetryService:
    readings: SqlAlchemyReadingRepository
    events: SqlAlchemyEventRepository
    clock: Clock

    def summary(self, device: Device, period: Period) -> PeriodSummary:
        if period.includes(self.clock.now()):
            return self._live(device, period)
        return self._over(device, period)

    def history(self, device: Device, period: Period, interval: Interval) -> PeriodHistory:
        period.require_supported(interval)
        return PeriodHistory(
            period=period,
            interval=interval,
            buckets=self.readings.bucket_maxima(device.key, period, interval),
            events=self.events.list_in_period(device.key, period, limit=_EVENT_LIMIT),
        )

    def events_in(self, device: Device, period: Period) -> list[Event]:
        return self.events.list_in_period(device.key, period, limit=_EVENT_LIMIT)

    def location(self, device: Device) -> DeviceLocation | None:
        reading = self.readings.latest_located(device.key)
        if reading is None or reading.frame.location is None:
            return None
        return DeviceLocation(coordinates=reading.frame.location, at=reading.measured_at)

    def _live(self, device: Device, period: Period) -> PeriodSummary:
        reading = self.readings.latest(device.key)
        if reading is None:
            return PeriodSummary(period=period, live=True, management_phone=device.management_phone)
        return PeriodSummary(
            period=period,
            live=True,
            at=reading.measured_at,
            state=reading.state,
            latched=reading.frame.latched,
            water=bool(reading.frame.water),
            management_phone=device.management_phone,
            channels=_channels_of(reading),
            values=reading.frame.values,
        )

    def _over(self, device: Device, period: Period) -> PeriodSummary:
        extremes = self.readings.period_extremes(device.key, period)
        if extremes is None:
            return PeriodSummary(
                period=period, live=False, management_phone=device.management_phone
            )
        return PeriodSummary(
            period=period,
            live=False,
            at=extremes.at,
            state=extremes.state,
            latched=extremes.latched,
            water=extremes.water,
            management_phone=device.management_phone,
            channels=self._peaks_in(device, period),
            values=extremes.values,
        )

    def _peaks_in(self, device: Device, period: Period) -> dict[Measure, ChannelPeak]:
        found = (
            (deviation, self.readings.measure_peak(device.key, period, deviation, slope))
            for deviation, slope in SLOPE_BY_DEVIATION.items()
        )
        return {deviation: peak for deviation, peak in found if peak is not None}


def _channels_of(reading: Reading) -> dict[Measure, ChannelPeak]:
    found = (
        (deviation, reading.frame.value(deviation), reading.frame.value(slope))
        for deviation, slope in SLOPE_BY_DEVIATION.items()
    )
    return {
        deviation: ChannelPeak(at=reading.measured_at, value=value, slope=slope)
        for deviation, value, slope in found
        if value is not None or slope is not None
    }
