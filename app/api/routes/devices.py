from __future__ import annotations

from fastapi import APIRouter

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.device import PushTokenRequest, PushTokenResponse
from app.runtime.providers import DeviceServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["devices"])


@router.post(
    "/push-token",
    response_model=PushTokenResponse,
    summary="Expo 푸시 토큰 등록 (멱등)",
    responses={404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}},
)
async def register_push_token(
    body: PushTokenRequest, device: ResolvedDevice, devices: DeviceServiceDep
) -> PushTokenResponse:
    devices.register_push_token(device, body.token)
    return PushTokenResponse(registered=True)
