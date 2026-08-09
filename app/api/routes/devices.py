"""기기 등록·푸시 토큰 라우터."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.auth import AuthenticatedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.device import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    PushTokenRequest,
    PushTokenResponse,
)
from app.runtime.providers import DeviceServiceDep

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="MAC으로 기기 등록 + deviceToken 발급",
    responses={
        409: {"model": ErrorResponse, "description": "이미 등록된 MAC"},
        422: {"model": ErrorResponse, "description": "MAC 형식 오류"},
    },
)
async def register_device(
    body: DeviceRegisterRequest, devices: DeviceServiceDep, response: Response
) -> DeviceRegisterResponse:
    registration = devices.register(body.mac)
    device = registration.device
    response.headers["Location"] = f"/devices/{device.public_id}"
    return DeviceRegisterResponse(
        device_id=device.public_id,
        device_token=registration.token,
        management_phone=device.management_phone,
    )


@router.post(
    "/{device_id}/push-token",
    response_model=PushTokenResponse,
    summary="Expo 푸시 토큰 등록 (멱등)",
)
async def register_push_token(
    body: PushTokenRequest, device: AuthenticatedDevice, devices: DeviceServiceDep
) -> PushTokenResponse:
    devices.register_push_token(device, body.token)
    return PushTokenResponse(registered=True)
