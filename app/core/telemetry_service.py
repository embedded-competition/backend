from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.device_current import DeviceCurrent
from app.core.event_page import EventPage
from app.core.period_peaks import PeriodPeaks
from app.core.sensor_detail import DetailBucket, SensorDetail
from app.domain.device import Device
from app.domain.frames import Coordinates
from app.domain.measurements import SLOPE_BY_DEVIATION, Measure, Sensor, sensor_measures
from app.domain.ports.clock import Clock
from app.domain.readings import ChannelPeak
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

    def current(self, device: Device) -> DeviceCurrent:
        reading = self.readings.latest(device.key)
        if reading is None:
            return DeviceCurrent()
        return DeviceCurrent(
            status=reading.state,
            conditions=reading.conditions,
            at=reading.measured_at,
            latched=reading.frame.latched,
            water=bool(reading.frame.water),
            values=reading.frame.values,
        )

    def peaks(self, device: Device, period: Period) -> PeriodPeaks:
        extremes = self.readings.period_extremes(device.key, period)
        if extremes is None:
            return PeriodPeaks()
        return PeriodPeaks(
            status=extremes.state,
            conditions=extremes.conditions,
            channels=self._peaks_in(device, period),
            values=extremes.values,
        )

    def detail(
        self, device: Device, sensor: Sensor, period: Period, interval: Interval
    ) -> SensorDetail:
        period.require_supported(interval)
        deviation, slope = sensor_measures(sensor)
        buckets = self.readings.bucket_maxima(device.key, period, interval)
        return SensorDetail(
            buckets=[
                DetailBucket(
                    start=bucket.start,
                    value=bucket.value(deviation),
                    slope=bucket.value(slope) if slope is not None else None,
                )
                for bucket in buckets
            ]
        )

    def events_in(self, device: Device, period: Period) -> EventPage:
        found = self.events.list_in_period(device.key, period, limit=_EVENT_LIMIT + 1)
        truncated = len(found) > _EVENT_LIMIT
        return EventPage(items=found[:_EVENT_LIMIT], truncated=truncated)

    def location(self, device: Device) -> DeviceLocation | None:
        reading = self.readings.latest_located(device.key)
        if reading is None or reading.frame.location is None:
            return None
        return DeviceLocation(coordinates=reading.frame.location, at=reading.measured_at)

    def _peaks_in(self, device: Device, period: Period) -> dict[Measure, ChannelPeak]:
        found = (
            (deviation, self.readings.measure_peak(device.key, period, deviation, slope))
            for deviation, slope in SLOPE_BY_DEVIATION.items()
        )
        return {deviation: peak for deviation, peak in found if peak is not None}
