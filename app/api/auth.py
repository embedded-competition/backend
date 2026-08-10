from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.device import Device
from app.domain.exceptions import DeviceNotFound, Unauthorized
from app.runtime.providers import DeviceServiceDep

_bearer = HTTPBearer(auto_error=False)


def authenticated_device_dep(
    device_id: Annotated[str, Path(description="POST /devices가 발급한 식별자")],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    devices: DeviceServiceDep,
) -> Device:
    if credentials is None or not credentials.credentials:
        raise Unauthorized("Authorization 헤더 없음")
    device = devices.authenticate(credentials.credentials)
    if device.public_id != device_id:
        raise DeviceNotFound(f"기기 없음: {device_id}")
    return device


AuthenticatedDevice = Annotated[Device, Depends(authenticated_device_dep)]
