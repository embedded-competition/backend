"""경보 해제 라우터.

앱은 해제 **요청**만 보낸다. 승인 판단은 서버 내부 규칙이고 사유는 내려주지 않는다
(앱 spec O8).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.auth import AuthenticatedDevice
from app.api.providers import AlertServiceDep
from app.api.schemas.alarm import AlarmReleaseRequest, AlarmReleaseResponse
from app.api.schemas.base import ErrorResponse

router = APIRouter(prefix="/devices/{device_id}", tags=["alerts"])


@router.post(
    "/alarm/release",
    response_model=AlarmReleaseResponse,
    summary="경보 해제 요청",
    responses={403: {"model": ErrorResponse, "description": "해제 거부 (사유 비공개)"}},
)
async def release_alarm(
    body: AlarmReleaseRequest, device: AuthenticatedDevice, alerts: AlertServiceDep
) -> AlarmReleaseResponse:
    alerts.request_release(device, body.note)
    return AlarmReleaseResponse(released=True)
