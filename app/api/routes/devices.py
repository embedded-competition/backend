from __future__ import annotations

from fastapi import APIRouter

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.device import (
    ModuleStatusResponse,
    PushTokenRequest,
    PushTokenResponse,
)
from app.runtime.providers import DeviceServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["devices"])


@router.get(
    "",
    response_model=ModuleStatusResponse,
    summary="감지 모듈 자기진단 (설정 화면)",
    description=(
        "텔레메트리와 주기가 다르다 — 여기 담긴 것은 거의 바뀌지 않는다. "
        "셋 다 서버가 판정한 결과이고, 문장으로 만드는 것은 앱 몫이다."
    ),
    responses={404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}},
)
async def get_module_status(
    device: ResolvedDevice, devices: DeviceServiceDep
) -> ModuleStatusResponse:
    return ModuleStatusResponse.from_domain(devices.module_status(device))


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
