from __future__ import annotations

from fastapi import APIRouter

from app.api.device_path import ResolvedDevice
from app.api.schemas.alarm import AlarmReleaseRequest, AlarmReleaseResponse
from app.api.schemas.base import ErrorResponse
from app.runtime.providers import AlertServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["alerts"])


@router.post(
    "/alarm/release",
    response_model=AlarmReleaseResponse,
    summary="경보 해제 요청",
    responses={
        403: {"model": ErrorResponse, "description": "해제 거부 (사유 비공개)"},
        404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"},
    },
)
async def release_alarm(
    body: AlarmReleaseRequest, device: ResolvedDevice, alerts: AlertServiceDep
) -> AlarmReleaseResponse:
    alerts.request_release(device, body.note)
    return AlarmReleaseResponse(released=True)
