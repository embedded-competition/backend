"""수신 기록 저장소 + ORM↔domain 변환.

센서 값은 Measure enum이 곧 컬럼명이라(measurements.py) 항목별 대입이 없다 —
센서를 추가해도 이 파일은 안 바뀐다.
"""

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
        """멱등 삽입. 조회 후 분기(check-then-act)는 경쟁 조건이라 upsert를 쓴다.

        저장된 기록을 식별자와 함께 돌려준다 — 성공 여부만 돌려주면 방금 만든 행의
        PK를 호출부가 알 수 없어 이 기록을 가리키는 FK가 전부 비게 된다.
        이미 있으면 None이다. 중복은 실패가 아니라 LoRa 재전송의 정상 결과다.
        """
        statement = (
            sqlite_insert(ReadingOrm)
            .values(**_to_columns(reading))
            .on_conflict_do_nothing(
                index_elements=["device_id", "measured_at", "seq"],
            )
            # RETURNING이 비면 충돌로 건너뛴 것 — rowcount보다 타입이 명확하다.
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
        # 시간 범위와 상한을 항상 요구한다 — 무제한 조회는 RPi에서 OOM 경로.
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
    """플래그가 하나도 없으면 노드가 signature를 안 보낸 것 — None으로 구분한다."""
    if row.sig_rise is None and row.sig_hold is None and row.sig_no_recover is None:
        return None
    return SignatureFlags(
        rise=bool(row.sig_rise),
        hold=bool(row.sig_hold),
        no_recover=bool(row.sig_no_recover),
        hold_s=row.sig_hold_s or 0,
    )


def _to_columns(reading: Reading) -> dict[str, object]:
    """멱등 삽입(ON CONFLICT)에 쓰려고 dict로 낸다."""
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
    # Measure.value == 컬럼명이라 항목 추가 시 이 함수는 안 바뀐다.
    columns.update({measure.value: frame.values.get(measure) for measure in Measure})
    return columns
