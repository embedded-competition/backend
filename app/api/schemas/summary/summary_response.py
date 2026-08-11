from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.summary.summary_channel_response import SummaryChannelResponse
from app.core.period_summary import PeriodSummary
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState


class SummaryResponse(ApiModel):
    from_: Annotated[datetime, Field(alias="from", description="조회 시작 (UTC, 포함)")]
    to: Annotated[datetime, Field(description="조회 끝 (UTC, 미포함)")]
    live: Annotated[
        bool,
        Field(
            description=(
                "구간이 현재를 포함하는지. true면 모든 값이 최신 관측이고, false면 기간 중 최고치다"
            )
        ),
    ]
    state: Annotated[
        AlertState | None,
        Field(
            description=(
                "live면 현재 상태, 아니면 기간 중 가장 심각했던 상태. "
                "관측이 하나도 없으면 null — '데이터 없음'과 '정상'은 다른 사건이다"
            )
        ),
    ] = None
    at: Annotated[
        datetime | None,
        Field(description="이 응답이 근거로 삼은 마지막 관측 시각 (UTC). 관측이 없으면 null"),
    ] = None
    latched: Annotated[bool, Field(description="ALARM latch 유지 여부. 자동 해제 없음")] = False
    water: Annotated[bool, Field(description="침수·누액 감지 여부")] = False
    management_phone: Annotated[
        str | None,
        Field(description="관리실 전화번호. 경보 화면 버튼에 사용", examples=["01029015899"]),
    ] = None
    gas: SummaryChannelResponse | None = None
    h2: SummaryChannelResponse | None = None
    co: SummaryChannelResponse | None = None
    pressure: SummaryChannelResponse | None = None
    temp_c: Annotated[float | None, Field(examples=[26.1])] = None
    rh: Annotated[float | None, Field(description="상대습도 %", examples=[43.4])] = None

    @classmethod
    def from_domain(cls, summary: PeriodSummary) -> SummaryResponse:
        return cls(
            from_=summary.period.start,
            to=summary.period.end,
            live=summary.live,
            state=summary.state,
            at=summary.at,
            latched=summary.latched,
            water=summary.water,
            management_phone=summary.management_phone,
            gas=_channel(summary, Measure.VOC_DEV),
            h2=_channel(summary, Measure.H2_DEV),
            co=_channel(summary, Measure.CO_DEV),
            pressure=_channel(summary, Measure.PRESSURE_DEV),
            temp_c=summary.value(Measure.TEMP_C),
            rh=summary.value(Measure.HUMIDITY_PCT),
        )


def _channel(summary: PeriodSummary, deviation: Measure) -> SummaryChannelResponse | None:
    peak = summary.channel(deviation)
    return SummaryChannelResponse.from_domain(peak) if peak else None
