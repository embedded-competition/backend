from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings import Bucket, ChannelPeak, PeriodExtremes, RadioQuality, Reading
from app.domain.value_objects import AlertState, Condition, Interval, Period, SignatureFlags
from app.infrastructure.db.orm import ReadingOrm

_EPOCH_FORMAT = "%s"


@dataclass(frozen=True, slots=True)
class SqlAlchemyReadingRepository:
    session: Session

    def add_if_absent(self, reading: Reading) -> Reading | None:
        statement = (
            sqlite_insert(ReadingOrm)
            .values(**_to_columns(reading))
            .on_conflict_do_nothing(
                index_elements=["device_id", "measured_at", "seq"],
            )
            .returning(ReadingOrm.id)
        )
        stored_id = self.session.scalars(statement).one_or_none()
        if stored_id is None:
            return None
        return replace(reading, id=stored_id)

    def bucket_maxima(self, device_id: int, period: Period, interval: Interval) -> list[Bucket]:
        index = _bucket_index(period, interval)
        rows = self.session.execute(
            select(
                index.label("bucket"),
                func.count().label("samples"),
                _severity_of_row().label("severity"),
                *(func.max(_column_of(measure)).label(measure.value) for measure in Measure),
            )
            .where(*_within(device_id, period))
            .group_by(index)
            .order_by(index)
        ).all()
        return [
            Bucket(
                start=period.bucket_start(row.bucket, interval),
                state=AlertState.of_severity(row.severity),
                samples=row.samples,
                values=_maxima_of(row),
            )
            for row in rows
        ]

    def measure_peak(
        self, device_id: int, period: Period, deviation: Measure, slope: Measure
    ) -> ChannelPeak | None:
        column = _column_of(deviation)
        row = self.session.execute(
            select(
                ReadingOrm.measured_at,
                column.label("value"),
                _column_of(slope).label("slope"),
            )
            .where(*_within(device_id, period), column.is_not(None))
            .order_by(column.desc())
            .limit(1)
        ).one_or_none()
        if row is None:
            return None
        return ChannelPeak(at=row.measured_at, value=row.value, slope=row.slope)

    def period_extremes(self, device_id: int, period: Period) -> PeriodExtremes | None:
        row = self.session.execute(
            select(
                func.max(ReadingOrm.measured_at).label("at"),
                _severity_of_row().label("severity"),
                func.max(ReadingOrm.latched).label("latched"),
                func.max(ReadingOrm.water).label("water"),
                func.group_concat(ReadingOrm.conditions, ",").label("conditions"),
                *(func.max(_column_of(measure)).label(measure.value) for measure in Measure),
            ).where(*_within(device_id, period))
        ).one()
        if row.at is None:
            return None
        return PeriodExtremes(
            at=row.at,
            state=AlertState.of_severity(row.severity),
            latched=bool(row.latched),
            water=bool(row.water),
            conditions=_conditions_union(row.conditions),
            values=_maxima_of(row),
        )

    def latest(self, device_id: int) -> Reading | None:
        row = self.session.scalar(
            select(ReadingOrm)
            .where(ReadingOrm.device_id == device_id)
            .order_by(ReadingOrm.measured_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None

    def latest_located(self, device_id: int) -> Reading | None:
        row = self.session.scalar(
            select(ReadingOrm)
            .where(
                ReadingOrm.device_id == device_id,
                ReadingOrm.lat.is_not(None),
                ReadingOrm.lon.is_not(None),
            )
            .order_by(ReadingOrm.measured_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None


def _column_of(measure: Measure) -> ColumnElement[float | None]:
    column: ColumnElement[float | None] = getattr(ReadingOrm, measure.value)
    return column


def _within(device_id: int, period: Period) -> tuple[ColumnElement[bool], ...]:
    return (
        ReadingOrm.device_id == device_id,
        ReadingOrm.measured_at >= period.start,
        ReadingOrm.measured_at < period.end,
    )


def _bucket_index(period: Period, interval: Interval) -> ColumnElement[int]:
    epoch = cast(func.strftime(_EPOCH_FORMAT, ReadingOrm.measured_at), Integer)
    start_epoch = int(period.start.timestamp())
    return cast((epoch - start_epoch) / interval.seconds, Integer)


def _severity_of_row() -> ColumnElement[int]:
    return func.max(
        case(
            *((ReadingOrm.state == state.value, state.severity) for state in AlertState),
            else_=AlertState.WARMUP.severity,
        )
    )


def _maxima_of(row: Any) -> dict[Measure, float]:
    found = ((measure, getattr(row, measure.value)) for measure in Measure)
    return {measure: value for measure, value in found if value is not None}


def _conditions_union(concatenated: str | None) -> frozenset[Condition]:
    """각 행의 conditions를 ','로 이미 이어 뒀으니, group_concat 결과도 같은 구분자로 잇는다.

    빈 문자열(그 행에 원인 없음)과 NULL(마이그레이션 전 행)이 섞여 들어와도
    빈 조각은 걸러지므로 결과는 항상 실제로 관측된 원인들의 합집합이다.
    """
    if not concatenated:
        return frozenset()
    return frozenset(Condition(item) for item in concatenated.split(",") if item)


def _to_domain(row: ReadingOrm) -> Reading:
    return Reading(
        id=row.id,
        device_id=row.device_id,
        received_at=row.received_at,
        radio=RadioQuality(rssi=row.rssi, snr=row.snr),
        frame=TelemetryFrame(
            version=row.frame_version,
            seq=row.seq,
            measured_at=row.measured_at,
            state=AlertState(row.state),
            conditions=row.conditions or frozenset(),
            latched=bool(row.latched),
            values=_values_of(row),
            signature=_signature_of(row),
            batt_mv=row.batt_mv,
            water=row.water,
            location=Coordinates(lat=row.lat, lon=row.lon)
            if row.lat is not None and row.lon is not None
            else None,
        ),
    )


def _values_of(row: ReadingOrm) -> dict[Measure, float]:
    found = ((measure, getattr(row, measure.value)) for measure in Measure)
    return {measure: value for measure, value in found if value is not None}


def _signature_of(row: ReadingOrm) -> SignatureFlags | None:
    if row.sig_rise is None and row.sig_hold is None and row.sig_no_recover is None:
        return None
    return SignatureFlags(
        rise=bool(row.sig_rise),
        hold=bool(row.sig_hold),
        no_recover=bool(row.sig_no_recover),
        hold_s=row.sig_hold_s or 0,
    )


def _to_columns(reading: Reading) -> dict[str, object]:
    frame = reading.frame
    columns: dict[str, object] = {
        "device_id": reading.device_id,
        "seq": frame.seq,
        "measured_at": frame.measured_at,
        "received_at": reading.received_at,
        "frame_version": frame.version,
        "state": frame.state.value,
        "conditions": frame.conditions,
        "latched": frame.latched,
        "water": frame.water,
        "batt_mv": frame.batt_mv,
        "lat": frame.location.lat if frame.location else None,
        "lon": frame.location.lon if frame.location else None,
        "rssi": reading.radio.rssi,
        "snr": reading.radio.snr,
        "sig_rise": frame.signature.rise if frame.signature else None,
        "sig_hold": frame.signature.hold if frame.signature else None,
        "sig_no_recover": frame.signature.no_recover if frame.signature else None,
        "sig_hold_s": frame.signature.hold_s if frame.signature else None,
    }
    columns.update({measure.value: frame.values.get(measure) for measure in Measure})
    return columns
