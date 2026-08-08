"""domain Repository Protocol 구현. commit은 하지 않는다 — 경계는 서비스 호출 단위."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.domain.models import AccessToken, Alert, Device, Event, PushToken, Reading
from app.domain.value_objects import DeviceId
from app.infrastructure.db.mappers import (
    alert_to_domain,
    apply_alert,
    apply_device,
    apply_event,
    apply_push_token,
    device_to_domain,
    event_to_domain,
    push_token_to_domain,
    reading_to_columns,
    reading_to_domain,
)
from app.infrastructure.db.orm import (
    AccessTokenOrm,
    AlertOrm,
    DeviceOrm,
    EventOrm,
    PushTokenOrm,
    ReadingOrm,
)


class SqlAlchemyDeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_hw_id(self, hw_id: DeviceId) -> Device | None:
        row = self._session.scalar(select(DeviceOrm).where(DeviceOrm.hw_id == str(hw_id)))
        return device_to_domain(row) if row else None

    def get_by_mac(self, mac: str) -> Device | None:
        row = self._session.scalar(select(DeviceOrm).where(DeviceOrm.mac == mac))
        return device_to_domain(row) if row else None

    def get_by_public_id(self, public_id: str) -> Device | None:
        row = self._session.scalar(select(DeviceOrm).where(DeviceOrm.public_id == public_id))
        return device_to_domain(row) if row else None

    def get(self, device_id: int) -> Device | None:
        row = self._session.get(DeviceOrm, device_id)
        return device_to_domain(row) if row else None

    def list_active(self) -> list[Device]:
        rows = self._session.scalars(
            select(DeviceOrm).where(DeviceOrm.is_active.is_(True)).order_by(DeviceOrm.id)
        )
        return [device_to_domain(row) for row in rows]

    def save(self, device: Device) -> Device:
        row = self._session.get(DeviceOrm, device.id) if device.id else None
        if row is None:
            row = DeviceOrm()
            self._session.add(row)
        apply_device(row, device)
        self._session.flush()
        return device_to_domain(row)


class SqlAlchemyReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_if_absent(self, reading: Reading) -> bool:
        """멱등 삽입. 조회 후 분기(check-then-act)는 경쟁 조건이라 upsert를 쓴다."""
        statement = (
            sqlite_insert(ReadingOrm)
            .values(**reading_to_columns(reading))
            .on_conflict_do_nothing(
                index_elements=["device_id", "measured_at", "seq"],
            )
            # RETURNING이 비면 충돌로 건너뛴 것 — rowcount보다 타입이 명확하다.
            .returning(ReadingOrm.id)
        )
        return self._session.scalars(statement).one_or_none() is not None

    def list_in_range(
        self,
        device_id: int,
        *,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Reading]:
        # 시간 범위와 상한을 항상 요구한다 — 무제한 조회는 RPi에서 OOM 경로.
        rows = self._session.scalars(
            select(ReadingOrm)
            .where(
                ReadingOrm.device_id == device_id,
                ReadingOrm.measured_at >= start,
                ReadingOrm.measured_at <= end,
            )
            .order_by(ReadingOrm.measured_at.desc())
            .limit(limit)
        )
        return [reading_to_domain(row) for row in rows]

    def latest(self, device_id: int) -> Reading | None:
        row = self._session.scalar(
            select(ReadingOrm)
            .where(ReadingOrm.device_id == device_id)
            .order_by(ReadingOrm.measured_at.desc())
            .limit(1)
        )
        return reading_to_domain(row) if row else None


class SqlAlchemyAlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, alert: Alert) -> Alert:
        row = apply_alert(AlertOrm(), alert)
        self._session.add(row)
        self._session.flush()
        return alert_to_domain(row)

    def get(self, alert_id: int) -> Alert | None:
        row = self._session.get(AlertOrm, alert_id)
        return alert_to_domain(row) if row else None

    def list_active(self) -> list[Alert]:
        # 부분 인덱스 ix_alerts_active가 지원한다.
        rows = self._session.scalars(
            select(AlertOrm)
            .where(AlertOrm.acknowledged_at.is_(None))
            .order_by(AlertOrm.occurred_at.desc())
        )
        return [alert_to_domain(row) for row in rows]

    def list_for_device(self, device_id: int, *, limit: int) -> list[Alert]:
        rows = self._session.scalars(
            select(AlertOrm)
            .where(AlertOrm.device_id == device_id)
            .order_by(AlertOrm.occurred_at.desc())
            .limit(limit)
        )
        return [alert_to_domain(row) for row in rows]

    def save(self, alert: Alert) -> Alert:
        row = self._session.get(AlertOrm, alert.id) if alert.id else None
        if row is None:
            return self.add(alert)
        apply_alert(row, alert)
        self._session.flush()
        return alert_to_domain(row)


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: Event) -> Event:
        row = apply_event(EventOrm(), event)
        self._session.add(row)
        self._session.flush()
        return event_to_domain(row)

    def list_since(self, device_id: int, *, since: datetime, limit: int) -> list[Event]:
        rows = self._session.scalars(
            select(EventOrm)
            .where(EventOrm.device_id == device_id, EventOrm.occurred_at >= since)
            .order_by(EventOrm.occurred_at.desc())
            .limit(limit)
        )
        return [event_to_domain(row) for row in rows]

    def list_in_range(
        self, device_id: int, *, start: datetime, end: datetime, limit: int
    ) -> list[Event]:
        rows = self._session.scalars(
            select(EventOrm)
            .where(
                EventOrm.device_id == device_id,
                EventOrm.occurred_at >= start,
                EventOrm.occurred_at <= end,
            )
            .order_by(EventOrm.occurred_at)
            .limit(limit)
        )
        return [event_to_domain(row) for row in rows]


class SqlAlchemyAccessTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: AccessToken) -> AccessToken:
        row = AccessTokenOrm(
            device_id=token.device_id,
            token_hash=token.token_hash,
            created_at=token.created_at,
            last_used_at=token.last_used_at,
        )
        self._session.add(row)
        self._session.flush()
        token.id = row.id
        return token

    def find_device_id(self, token_hash: str) -> int | None:
        return self._session.scalar(
            select(AccessTokenOrm.device_id).where(AccessTokenOrm.token_hash == token_hash)
        )

    def touch(self, token_hash: str, *, at: datetime) -> None:
        self._session.execute(
            update(AccessTokenOrm)
            .where(AccessTokenOrm.token_hash == token_hash)
            .values(last_used_at=at)
        )


class SqlAlchemyPushTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, token: PushToken) -> PushToken:
        """같은 토큰 재등록은 소유 기기만 갱신한다 — 중복 행을 만들지 않는다."""
        row = self._session.scalar(select(PushTokenOrm).where(PushTokenOrm.token == token.token))
        if row is None:
            row = PushTokenOrm()
            self._session.add(row)
        apply_push_token(row, token)
        self._session.flush()
        return push_token_to_domain(row)

    def list_active(self, device_id: int) -> list[PushToken]:
        rows = self._session.scalars(
            select(PushTokenOrm).where(
                PushTokenOrm.device_id == device_id,
                PushTokenOrm.is_active.is_(True),
            )
        )
        return [push_token_to_domain(row) for row in rows]

    def save(self, token: PushToken) -> PushToken:
        row = self._session.get(PushTokenOrm, token.id) if token.id else None
        if row is None:
            return self.upsert(token)
        apply_push_token(row, token)
        self._session.flush()
        return push_token_to_domain(row)
