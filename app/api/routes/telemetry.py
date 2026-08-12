from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query

from app.api.device_path import ResolvedDevice
from app.api.schemas.base import ErrorResponse
from app.api.schemas.channels import LocationResponse
from app.api.schemas.event import EventListResponse
from app.api.schemas.sensors import SensorDetailResponse
from app.api.schemas.telemetry import DeviceCurrentResponse, PeriodPeaksResponse
from app.domain.exceptions import LocationUnavailable
from app.domain.measurements import Sensor
from app.domain.value_objects import Interval, Period
from app.runtime.providers import TelemetryServiceDep

router = APIRouter(prefix="/devices/{mac}", tags=["telemetry"])

PeriodStart = Annotated[datetime, Query(alias="from", description="조회 시작 (UTC, 포함)")]
PeriodEnd = Annotated[datetime, Query(alias="to", description="조회 끝 (UTC, 미포함)")]
SensorPath = Annotated[Sensor, Path(description="단일 측정 채널")]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "MAC에 해당하는 기기 없음"}
}


def _period_of(start: PeriodStart, end: PeriodEnd) -> Period:
    return Period(start, end)


PeriodQuery = Annotated[Period, Depends(_period_of)]


@router.get(
    "/telemetry/current",
    response_model=DeviceCurrentResponse,
    summary="지금 상태 (메인 화면)",
    description="구간 개념이 없다. 관측이 하나도 없으면 status가 null이고 채널이 전부 null이다.",
    responses=_NOT_FOUND,
)
async def telemetry_current(
    device: ResolvedDevice, telemetry: TelemetryServiceDep
) -> DeviceCurrentResponse:
    return DeviceCurrentResponse.from_domain(telemetry.current(device))


@router.get(
    "/telemetry/peaks",
    response_model=PeriodPeaksResponse,
    summary="기간 중 최고치",
    description="from·to는 요청한 값 그대로라 에코백하지 않는다. 채널 at은 최고치를 찍은 시각.",
    responses=_NOT_FOUND,
)
async def telemetry_peaks(
    device: ResolvedDevice, telemetry: TelemetryServiceDep, period: PeriodQuery
) -> PeriodPeaksResponse:
    return PeriodPeaksResponse.from_domain(telemetry.peaks(device, period))


@router.get(
    "/sensors/{sensor}/detail",
    response_model=SensorDetailResponse,
    summary="단일 채널 기간·눈금별 집계 (상세 화면 차트)",
    description=(
        "각 칸의 값은 평균이 아니라 최고치다 — 평균은 스파이크를 지우고 "
        "지워진 스파이크가 곧 놓친 경보다."
    ),
    responses=_NOT_FOUND,
)
async def sensor_detail(
    device: ResolvedDevice,
    telemetry: TelemetryServiceDep,
    sensor: SensorPath,
    period: PeriodQuery,
    interval: Annotated[Interval, Query(description="집계 눈금")],
) -> SensorDetailResponse:
    return SensorDetailResponse.from_domain(telemetry.detail(device, sensor, period, interval))


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
    return EventListResponse.from_domain(telemetry.events_in(device, Period(since, until)))


@router.get(
    "/location",
    response_model=LocationResponse,
    summary="마지막으로 보고된 위치",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "device_not_found(기기 없음) 또는 location_unavailable(좌표 없음)",
        }
    },
)
async def device_location(
    device: ResolvedDevice, telemetry: TelemetryServiceDep
) -> LocationResponse:
    location = telemetry.location(device)
    if location is None:
        raise LocationUnavailable(f"좌표 기록 없음: {device.mac}")
    return LocationResponse.from_domain(location)
