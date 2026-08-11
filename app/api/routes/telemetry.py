from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.auth import AuthenticatedDevice
from app.api.schemas.event import EventListResponse, EventResponse
from app.api.schemas.fleet import FleetComparisonResponse
from app.api.schemas.history import HistoryResponse
from app.api.schemas.summary import SummaryResponse
from app.api.schemas.telemetry import TelemetryResponse
from app.domain.value_objects import Interval, Period
from app.runtime.providers import TelemetryServiceDep

router = APIRouter(prefix="/devices/{device_id}", tags=["telemetry"])

PeriodStart = Annotated[datetime, Query(alias="from", description="조회 시작 (UTC, 포함)")]
PeriodEnd = Annotated[datetime, Query(alias="to", description="조회 끝 (UTC, 미포함)")]


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
    "/telemetry/summary",
    response_model=SummaryResponse,
    summary="기간 요약 (메인 화면)",
    description=(
        "구간이 현재를 포함하면 `range.live=true`이고 `current`에 실시간 값이 담긴다. "
        "지난 구간이면 `current`는 null이고 `peaks`의 기간 중 최고치를 쓴다."
    ),
)
async def telemetry_summary(
    device: AuthenticatedDevice,
    telemetry: TelemetryServiceDep,
    start: PeriodStart,
    end: PeriodEnd,
) -> SummaryResponse:
    return SummaryResponse.from_domain(telemetry.summary(device, Period(start, end)))


@router.get(
    "/telemetry/history",
    response_model=HistoryResponse,
    summary="기간·눈금별 집계 (상세 화면 차트)",
    description=(
        "각 칸의 값은 평균이 아니라 최고치다 — 평균은 스파이크를 지우고 "
        "지워진 스파이크가 곧 놓친 경보다."
    ),
)
async def telemetry_history(
    device: AuthenticatedDevice,
    telemetry: TelemetryServiceDep,
    start: PeriodStart,
    end: PeriodEnd,
    interval: Annotated[str, Query(description="집계 눈금", examples=["2h"])],
) -> HistoryResponse:
    return HistoryResponse.from_domain(
        telemetry.history(device, Period(start, end), Interval.parse(interval))
    )


@router.get(
    "/events",
    response_model=EventListResponse,
    summary="기록(이벤트) 조회",
)
async def list_events(
    device: AuthenticatedDevice,
    telemetry: TelemetryServiceDep,
    since: Annotated[datetime, Query(description="이 시각 이후 이벤트 (UTC, 포함)")],
    until: Annotated[datetime, Query(description="이 시각 이전 이벤트 (UTC, 미포함)")],
) -> EventListResponse:
    return EventListResponse(
        items=[
            EventResponse.from_domain(event)
            for event in telemetry.events_in(device, Period(since, until))
        ]
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
