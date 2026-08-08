"""Depends provider 단일 지점. 라우터 파일마다 세션 팩토리를 만들지 않는다."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app.core.alert_service import AlertService
from app.core.config import Settings, get_settings
from app.core.device_service import DeviceService
from app.core.telemetry_service import TelemetryService
from app.domain.exceptions import DeviceNotFound, Unauthorized
from app.domain.models import Device
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories import (
    SqlAlchemyAccessTokenRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyPushTokenRepository,
    SqlAlchemyReadingRepository,
)

# auto_error=False — 헤더 없음도 우리 에러 형식(401 unauthorized)으로 응답한다.
_bearer = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


def session_factory_dep(request: Request) -> sessionmaker[Session]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:  # pragma: no cover - lifespan이 항상 채운다
        raise RuntimeError("session_factory가 lifespan에서 초기화되지 않았다")
    return factory  # type: ignore[no-any-return]


def session_dep(
    factory: Annotated[sessionmaker[Session], Depends(session_factory_dep)],
) -> Iterator[Session]:
    """요청 1개 = 트랜잭션 1개. commit/rollback 경계가 여기다."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
SessionDep = Annotated[Session, Depends(session_dep)]


def device_service_dep(
    session: SessionDep, settings: Annotated[Settings, Depends(settings_dep)]
) -> DeviceService:
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


def authenticated_device_dep(
    device_id: Annotated[str, Path(description="POST /devices가 발급한 식별자")],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    devices: DeviceServiceDep,
) -> Device:
    """Bearer 토큰 검증 + 경로의 deviceId 소유권 확인.

    토큰이 가리키는 기기와 경로의 기기가 다르면 404로 응답한다 — 403을 주면
    "그 기기는 존재한다"는 정보가 새어나간다.
    """
    if credentials is None or not credentials.credentials:
        raise Unauthorized("Authorization 헤더 없음")
    device = devices.authenticate(credentials.credentials)
    if device.public_id != device_id:
        raise DeviceNotFound(f"기기 없음: {device_id}")
    return device


AuthenticatedDevice = Annotated[Device, Depends(authenticated_device_dep)]
