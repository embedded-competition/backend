"""텔레메트리 응답 DTO.

**raw 센서값(sraw·mv·baseline·rsKohm·mvAvg)은 포함하지 않는다.**
노드가 판정하고 정규화값만 전송하므로 서버가 채울 수 없다.
근거와 앱 측 변경 요청은 docs/api-contract-reconciliation.md §B2.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.core.telemetry_service import DailyHistory, FleetComparison, HourlySample
from app.domain.models import Device, Event, Reading
from app.domain.value_objects import AlertState, GasChannel


class GasChannelResponse(ApiModel):
    dev_z: Annotated[
        float | None,
        Field(description="baseline 대비 z-score. 가스 방향이 양수", examples=[3.1]),
    ] = None
    slope: Annotated[float | None, Field(description="dev 변화율 (z/min)", examples=[2.4])] = None


class SignatureResponse(ApiModel):
    """판단 근거 3요소. 노드가 계산해 전송한다."""

    rise: bool
    hold: bool
    no_recover: bool
    hold_s: Annotated[int, Field(description="시그니처 지속 초", examples=[18])]


class EnvResponse(ApiModel):
    temp_c: float | None = None
    rh: Annotated[float | None, Field(description="상대습도 %")] = None
    d_rh_dt: Annotated[float | None, Field(description="습도 변화율 %RH/min. 습도 게이트 근거")] = (
        None
    )


class PressureResponse(ApiModel):
    pres_dev: float | None = None
    pres_rate: float | None = None


class LocationResponse(ApiModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]


class ModuleResponse(ApiModel):
    node_id: Annotated[str | None, Field(examples=["44bd8d239c28"])] = None
    seq: int | None = None
    batt_mv: Annotated[int | None, Field(description="노드 배터리 전압 mV")] = None
    rssi: Annotated[int | None, Field(description="수신 세기 dBm", examples=[-74])] = None
    snr: float | None = None
    last_seen: Annotated[
        datetime | None,
        Field(
            description=(
                "마지막 프레임 수신 시각(UTC). 폴링 주기보다 갱신이 느리므로 "
                "앱은 이 값으로 데이터 나이를 표시해야 한다"
            )
        ),
    ] = None


class TelemetryResponse(ApiModel):
    state: AlertState
    latched: Annotated[bool, Field(description="ALARM latch 유지 여부. 자동 해제 없음")] = False
    gas: GasChannelResponse
    h2: GasChannelResponse
    co: GasChannelResponse | None = None
    env: EnvResponse | None = None
    pressure: PressureResponse | None = None
    water: bool | None = None
    signature: SignatureResponse | None = None
    location: LocationResponse | None = None
    module: ModuleResponse

    @classmethod
    def from_domain(cls, device: Device, reading: Reading | None) -> TelemetryResponse:
        if reading is None:
            # 아직 프레임을 한 번도 못 받은 기기. 상태를 지어내지 않는다.
            return cls(
                state=device.last_state or AlertState.WARMUP,
                gas=GasChannelResponse(),
                h2=GasChannelResponse(),
                module=ModuleResponse(
                    node_id=str(device.hw_id) if device.hw_id else None,
                    seq=device.last_seq,
                    last_seen=device.last_seen_at,
                ),
            )
        return cls(
            state=reading.state,
            latched=bool(reading.latched),
            gas=_channel(reading, GasChannel.VOC),
            h2=_channel(reading, GasChannel.H2),
            co=_channel(reading, GasChannel.CO) if reading.channel(GasChannel.CO) else None,
            env=EnvResponse(
                temp_c=reading.temp_c,
                rh=reading.humidity_pct,
                d_rh_dt=reading.d_rh_dt,
            )
            if reading.temp_c is not None or reading.humidity_pct is not None
            else None,
            pressure=PressureResponse(
                pres_dev=reading.pressure_dev, pres_rate=reading.pressure_rate
            )
            if reading.pressure_dev is not None or reading.pressure_rate is not None
            else None,
            water=reading.water,
            signature=SignatureResponse(
                rise=reading.signature.rise,
                hold=reading.signature.hold,
                no_recover=reading.signature.no_recover,
                hold_s=reading.signature.hold_s,
            )
            if reading.signature
            else None,
            location=LocationResponse(lat=reading.lat, lon=reading.lon)
            if reading.lat is not None and reading.lon is not None
            else None,
            module=ModuleResponse(
                node_id=str(device.hw_id) if device.hw_id else None,
                seq=reading.seq,
                batt_mv=reading.batt_mv,
                rssi=reading.rssi,
                snr=reading.snr,
                last_seen=reading.received_at,
            ),
        )


def _channel(reading: Reading, channel: GasChannel) -> GasChannelResponse:
    measurement = reading.channel(channel)
    if measurement is None:
        return GasChannelResponse()
    return GasChannelResponse(dev_z=measurement.deviation, slope=measurement.slope)


class HourlySampleResponse(ApiModel):
    hour: Annotated[str, Field(examples=["14:00"])]
    state: AlertState
    gas: GasChannelResponse
    h2: GasChannelResponse
    co: GasChannelResponse
    temp_c: float | None = None
    rh: float | None = None
    pres_dev: float | None = None

    @classmethod
    def from_domain(cls, sample: HourlySample) -> HourlySampleResponse:
        return cls(
            hour=sample.hour,
            state=sample.state,
            gas=GasChannelResponse(dev_z=sample.channels.get(GasChannel.VOC)),
            h2=GasChannelResponse(dev_z=sample.channels.get(GasChannel.H2)),
            co=GasChannelResponse(dev_z=sample.channels.get(GasChannel.CO)),
            temp_c=sample.temp_c,
            rh=sample.humidity_pct,
            pres_dev=sample.pressure_dev,
        )


class HistoryEventResponse(ApiModel):
    time: Annotated[str, Field(examples=["14:32"])]
    description: str


class HistoryResponse(ApiModel):
    date: date
    samples: list[HourlySampleResponse]
    events: list[HistoryEventResponse]

    @classmethod
    def from_domain(cls, history: DailyHistory) -> HistoryResponse:
        return cls(
            date=history.day,
            samples=[HourlySampleResponse.from_domain(s) for s in history.samples],
            events=[
                HistoryEventResponse(
                    time=event.occurred_at.strftime("%H:%M"),
                    description=event.description,
                )
                for event in history.events
            ],
        )


class EventResponse(ApiModel):
    id: Annotated[str, Field(examples=["evt_1"])]
    timestamp: datetime
    kind: str
    description: str

    @classmethod
    def from_domain(cls, event: Event) -> EventResponse:
        return cls(
            id=f"evt_{event.id}",
            timestamp=event.occurred_at,
            kind=event.kind.value,
            description=event.description,
        )


class EventListResponse(ApiModel):
    items: list[EventResponse]


class FleetComparisonResponse(ApiModel):
    fleet_size: int
    fleet_avg_level: AlertState
    my_level: AlertState
    my_multiplier: Annotated[
        float, Field(description="전체 평균 심각도 대비 내 배수", examples=[8.0])
    ]

    @classmethod
    def from_domain(cls, comparison: FleetComparison) -> FleetComparisonResponse:
        return cls(
            fleet_size=comparison.fleet_size,
            fleet_avg_level=comparison.fleet_avg_level,
            my_level=comparison.my_level,
            my_multiplier=comparison.my_multiplier,
        )


class AlarmReleaseRequest(ApiModel):
    note: Annotated[str | None, Field(max_length=255)] = None


class AlarmReleaseResponse(ApiModel):
    released: bool
