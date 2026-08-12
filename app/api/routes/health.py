from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.schemas.health import ComponentHealth, ComponentStatus, HealthResponse
from app.core.config import PushDelivery
from app.runtime.deps import RuntimeStateDep, SessionDep, SettingsDep
from app.runtime.state import ReceiverLiveness

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
async def health(
    settings: SettingsDep, session: SessionDep, state: RuntimeStateDep
) -> HealthResponse:
    components = {
        "process": ComponentHealth(status=ComponentStatus.OK),
        "database": _check_database(session),
        "lora_radio": _check_lora(state.lora, settings.offline_threshold_s),
        "push": _check_push(settings.push_delivery),
    }
    worst = max(components.values(), key=lambda c: _SEVERITY[c.status]).status
    return HealthResponse(
        status=worst,
        version=settings.release,
        revision=state.schema_revision,
        components=components,
    )


def _check_database(session: SessionDep) -> ComponentHealth:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        return ComponentHealth(status=ComponentStatus.FAILED, detail=type(exc).__name__)
    return ComponentHealth(status=ComponentStatus.OK)


def _check_lora(lora: ReceiverLiveness, threshold_s: int) -> ComponentHealth:
    if not lora.enabled:
        return ComponentHealth(status=ComponentStatus.DISABLED, detail="수신 task 미가동")
    elapsed = lora.silence_s(datetime.now(UTC))
    if elapsed is None:
        return ComponentHealth(status=ComponentStatus.DEGRADED, detail="수신 이력 없음")
    if elapsed > threshold_s:
        return ComponentHealth(
            status=ComponentStatus.FAILED, detail=f"마지막 수신 {int(elapsed)}s 전"
        )
    return ComponentHealth(status=ComponentStatus.OK)


def _check_push(delivery: PushDelivery) -> ComponentHealth:
    if delivery == "log":
        return ComponentHealth(status=ComponentStatus.DISABLED, detail="로그 전용 발송")
    return ComponentHealth(status=ComponentStatus.OK)
