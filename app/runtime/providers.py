from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.alert_service import AlertService
from app.core.device_service import DeviceService
from app.core.telemetry_service import TelemetryService
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories.access_tokens import SqlAlchemyAccessTokenRepository
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.runtime.deps import SessionDep, SettingsDep


def device_service_dep(session: SessionDep, settings: SettingsDep) -> DeviceService:
    return DeviceService(
        devices=SqlAlchemyDeviceRepository(session),
        access_tokens=SqlAlchemyAccessTokenRepository(session),
        push_tokens=SqlAlchemyPushTokenRepository(session),
        clock=SystemClock(),
        default_management_phone=settings.management_phone,
    )


def telemetry_service_dep(session: SessionDep) -> TelemetryService:
    return TelemetryService(
        devices=SqlAlchemyDeviceRepository(session),
        readings=SqlAlchemyReadingRepository(session),
        events=SqlAlchemyEventRepository(session),
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
