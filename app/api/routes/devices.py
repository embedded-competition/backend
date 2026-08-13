from __future__ import annotations

from fastapi import APIRouter

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.device import PushTokenRequest, PushTokenResponse, SensorCheckResponse
from app.runtime.providers import DeviceServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["devices"])


@router.get(
    "",
    response_model=SensorCheckResponse,
    summary="센서 점검 결과 (설정 화면)",
    description="포화된 센서가 하나라도 있으면 FAULT다. 관측이 없으면 null.",
    responses={404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}},
)
async def get_sensor_check(
    device: ResolvedDevice, devices: DeviceServiceDep
) -> SensorCheckResponse:
    return SensorCheckResponse.from_domain(devices.sensor_check(device))


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
