"""저장소 테스트 공용 fixture. 스키마는 Alembic으로 만든다 — 마이그레이션도 같이 검증된다."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.domain.device import Device
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_device


@pytest.fixture
def devices(session: Session) -> SqlAlchemyDeviceRepository:
    return SqlAlchemyDeviceRepository(session)


@pytest.fixture
def readings(session: Session) -> SqlAlchemyReadingRepository:
    return SqlAlchemyReadingRepository(session)


@pytest.fixture
def alerts(session: Session) -> SqlAlchemyAlertRepository:
    return SqlAlchemyAlertRepository(session)


@pytest.fixture
def saved_device(devices: SqlAlchemyDeviceRepository, now: datetime) -> Device:
    return devices.save(a_device(registered_at=now))


@pytest.fixture
def device_id(saved_device: Device) -> int:
    """FK로 쓸 PK. 저장 직후라 항상 채워져 있다."""
    assert saved_device.id is not None
    return saved_device.id
