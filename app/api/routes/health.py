"""헬스체크 라우터."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, status
from sqlalchemy import text

from app.api.deps import SessionDep, SettingsDep
from app.api.schemas.health import ComponentHealth, ComponentStatus, HealthResponse

router = APIRouter(tags=["health"])

_SEVERITY = {
    ComponentStatus.OK: 0,
    ComponentStatus.DISABLED: 0,
    ComponentStatus.DEGRADED: 1,
    ComponentStatus.FAILED: 2,
}


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="구성요소별 서비스 상태",
)
async def health(request: Request, settings: SettingsDep, session: SessionDep) -> HealthResponse:
    components = {
        "process": ComponentHealth(status=ComponentStatus.OK),
        "database": _check_database(session),
        "lora_radio": _check_lora(request, settings.offline_threshold_s),
        "push": _check_push(settings.fcm_credentials_path is not None),
    }
    worst = max(components.values(), key=lambda c: _SEVERITY[c.status]).status
    return HealthResponse(
        status=worst,
        version=request.app.version,
        revision=getattr(request.app.state, "alembic_revision", None),
        components=components,
    )


def _check_database(session: SessionDep) -> ComponentHealth:
    try:
        session.execute(text("SELECT 1"))  # 가벼운 확인. 집계 쿼리 금지.
    except Exception as exc:
        return ComponentHealth(status=ComponentStatus.FAILED, detail=type(exc).__name__)
    return ComponentHealth(status=ComponentStatus.OK)


def _check_lora(request: Request, threshold_s: int) -> ComponentHealth:
    last_seen: datetime | None = getattr(request.app.state, "lora_last_frame_at", None)
    if not getattr(request.app.state, "lora_running", False):
        return ComponentHealth(status=ComponentStatus.DISABLED, detail="수신 task 미가동")
    if last_seen is None:
        return ComponentHealth(status=ComponentStatus.DEGRADED, detail="수신 이력 없음")
    elapsed = (datetime.now(UTC) - last_seen).total_seconds()
    if elapsed > threshold_s:
        return ComponentHealth(
            status=ComponentStatus.FAILED, detail=f"마지막 수신 {int(elapsed)}s 전"
        )
    return ComponentHealth(status=ComponentStatus.OK)


def _check_push(configured: bool) -> ComponentHealth:
    if not configured:
        return ComponentHealth(status=ComponentStatus.DISABLED, detail="FCM 자격증명 미설정")
    return ComponentHealth(status=ComponentStatus.OK)
