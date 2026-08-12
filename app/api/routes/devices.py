from __future__ import annotations

from fastapi import APIRouter

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.device import DeviceResponse, PushTokenRequest, PushTokenResponse
from app.runtime.providers import DeviceServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["devices"])


@router.get(
    "",
    response_model=DeviceResponse,
    summary="기기 정보 + 모듈 상태 (설정 화면)",
    description=(
        "텔레메트리와 주기가 다르다 — 여기 담긴 것은 거의 바뀌지 않는다. "
        "배터리·연결·센서 점검은 서버가 판정한 결과이고, 문장으로 만드는 것은 앱 몫이다."
    ),
    responses={404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}},
)
async def get_device(device: ResolvedDevice, devices: DeviceServiceDep) -> DeviceResponse:
    return DeviceResponse.from_domain(devices.profile(device))


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
