from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.alert_service import AlertService
from app.core.device_service import DeviceService
from app.core.telemetry_service import TelemetryService
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.runtime.deps import SessionDep


def device_service_dep(session: SessionDep) -> DeviceService:
    return DeviceService(
        devices=SqlAlchemyDeviceRepository(session),
        push_tokens=SqlAlchemyPushTokenRepository(session),
        readings=SqlAlchemyReadingRepository(session),
        clock=SystemClock(),
    )


def telemetry_service_dep(session: SessionDep) -> TelemetryService:
    return TelemetryService(
        readings=SqlAlchemyReadingRepository(session),
        events=SqlAlchemyEventRepository(session),
        clock=SystemClock(),
    )


def alert_service_dep(session: SessionDep) -> AlertService:
    return AlertService(
        alerts=SqlAlchemyAlertRepository(session),
        events=SqlAlchemyEventRepository(session),
        clock=SystemClock(),
    )


DeviceServiceDep = Annotated[DeviceService, Depends(device_service_dep)]
TelemetryServiceDep = Annotated[TelemetryService, Depends(telemetry_service_dep)]
AlertServiceDep = Annotated[AlertService, Depends(alert_service_dep)]
