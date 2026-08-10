from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings import RadioQuality, Reading
from app.domain.value_objects import AlertState, SignatureFlags
from app.infrastructure.db.orm import ReadingOrm


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

    def list_in_range(
        self,
        device_id: int,
        *,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Reading]:
        rows = self.session.scalars(
            select(ReadingOrm)
            .where(
                ReadingOrm.device_id == device_id,
                ReadingOrm.measured_at >= start,
                ReadingOrm.measured_at <= end,
            )
            .order_by(ReadingOrm.measured_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in rows]

    def latest(self, device_id: int) -> Reading | None:
        row = self.session.scalar(
            select(ReadingOrm)
            .where(ReadingOrm.device_id == device_id)
            .order_by(ReadingOrm.measured_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None


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
