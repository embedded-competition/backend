"""Bearer deviceToken 검증 + 경로 소유권 확인."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.device import Device
from app.domain.exceptions import DeviceNotFound, Unauthorized
from app.runtime.providers import DeviceServiceDep

# auto_error=False — 헤더 없음도 우리 에러 형식(401 unauthorized)으로 응답한다.
_bearer = HTTPBearer(auto_error=False)


def authenticated_device_dep(
    device_id: Annotated[str, Path(description="POST /devices가 발급한 식별자")],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    devices: DeviceServiceDep,
) -> Device:
    """토큰이 가리키는 기기와 경로의 기기가 다르면 404다.

    403을 주면 "그 기기는 존재한다"는 정보가 새어나간다.
    """
    if credentials is None or not credentials.credentials:
        raise Unauthorized("Authorization 헤더 없음")
    device = devices.authenticate(credentials.credentials)
    if device.public_id != device_id:
        raise DeviceNotFound(f"기기 없음: {device_id}")
    return device


AuthenticatedDevice = Annotated[Device, Depends(authenticated_device_dep)]
