from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.channels import LocationResponse
from app.api.schemas.event import EventListResponse, EventResponse
from app.api.schemas.history import HistoryResponse
from app.api.schemas.summary import SummaryResponse
from app.domain.exceptions import DeviceNotFound
from app.domain.value_objects import Interval, Period
from app.runtime.providers import TelemetryServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["telemetry"])

PeriodStart = Annotated[datetime, Query(alias="from", description="조회 시작 (UTC, 포함)")]
PeriodEnd = Annotated[datetime, Query(alias="to", description="조회 끝 (UTC, 미포함)")]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}
}


@router.get(
    "/telemetry/summary",
    response_model=SummaryResponse,
    summary="기간 요약 (메인 화면)",
    description=(
        "구간이 현재를 포함하면 `live=true`이고 모든 값이 최신 관측이다. "
        "지난 구간이면 `live=false`이고 기간 중 최고치를 담는다. "
        "채널의 `at`은 어느 쪽이든 '이 값이 언제 것인가'를 말한다."
    ),
    responses=_NOT_FOUND,
)
async def telemetry_summary(
    device: ResolvedDevice,
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
    responses=_NOT_FOUND,
)
async def telemetry_history(
    device: ResolvedDevice,
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
    responses=_NOT_FOUND,
)
async def list_events(
    device: ResolvedDevice,
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
    "/location",
    response_model=LocationResponse,
    summary="마지막으로 보고된 위치",
    responses={404: {"model": ErrorResponse, "description": "기기가 없거나 좌표를 받은 적 없음"}},
)
async def device_location(
    device: ResolvedDevice, telemetry: TelemetryServiceDep
) -> LocationResponse:
    location = telemetry.location(device)
    if location is None:
        raise DeviceNotFound(f"좌표 기록 없음: {device.mac}")
    return LocationResponse.from_domain(location)
