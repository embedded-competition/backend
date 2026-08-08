"""텔레메트리 조회 라우터. 앱 폴링의 주 경로."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.auth import AuthenticatedDevice
from app.api.providers import TelemetryServiceDep
from app.api.schemas.event import EventListResponse, EventResponse
from app.api.schemas.fleet import FleetComparisonResponse
from app.api.schemas.history import HistoryResponse
from app.api.schemas.telemetry import TelemetryResponse

router = APIRouter(prefix="/devices/{device_id}", tags=["telemetry"])


@router.get(
    "/telemetry/latest",
    response_model=TelemetryResponse,
    summary="현재 상태 조회",
    description=(
        "raw 센서값(sraw·mv·baseline)은 포함하지 않는다 — 노드가 판정하고 "
        "정규화값만 전송한다. `module.lastSeen`으로 데이터 나이를 확인할 것."
    ),
)
async def latest_telemetry(
    device: AuthenticatedDevice, telemetry: TelemetryServiceDep
) -> TelemetryResponse:
    return TelemetryResponse.from_domain(device, telemetry.latest(device))


@router.get(
    "/telemetry/history",
    response_model=HistoryResponse,
    summary="날짜별 시간당 집계 (통계 탭)",
)
async def telemetry_history(
    device: AuthenticatedDevice,
    telemetry: TelemetryServiceDep,
    day: Annotated[date, Query(alias="date", description="조회 날짜 (UTC 기준)")],
) -> HistoryResponse:
    return HistoryResponse.from_domain(telemetry.history(device, day))


@router.get(
    "/events",
    response_model=EventListResponse,
    summary="기록(이벤트) 조회",
)
async def list_events(
    device: AuthenticatedDevice,
    telemetry: TelemetryServiceDep,
    since: Annotated[datetime, Query(description="이 시각 이후 이벤트 (UTC)")],
) -> EventListResponse:
    return EventListResponse(
        items=[EventResponse.from_domain(e) for e in telemetry.events_since(device, since)]
    )


@router.get(
    "/fleet-comparison",
    response_model=FleetComparisonResponse,
    summary="등록된 전체 기기 대비 내 위치",
)
async def fleet_comparison(
    device: AuthenticatedDevice, telemetry: TelemetryServiceDep
) -> FleetComparisonResponse:
    return FleetComparisonResponse.from_domain(telemetry.fleet_comparison(device))
