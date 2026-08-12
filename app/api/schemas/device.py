from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.base import ApiModel
from app.core.device_profile import DeviceProfile
from app.domain.module_health import BatteryLevel, LinkQuality, SensorCheck


class PushTokenRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    token: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            description="Expo 푸시 토큰",
            examples=["ExponentPushToken[xxxxxxx]"],
        ),
    ]


class PushTokenResponse(ApiModel):
    registered: bool


class BatteryResponse(ApiModel):
    percent: Annotated[int, Field(ge=0, le=100, examples=[78])]
    days_left: Annotated[
        int | None, Field(description="남은 날 추정. 모르면 null", examples=[40])
    ] = None

    @classmethod
    def from_domain(cls, battery: BatteryLevel) -> BatteryResponse:
        return cls(percent=battery.percent, days_left=battery.days_left)


class DeviceResponse(ApiModel):
    mac: Annotated[str, Field(examples=["AA:BB:CC:DD:EE:FF"])]
    label: Annotated[str, Field(examples=["내 킥보드"])]
    parking_slot: Annotated[str | None, Field(examples=["B2-01"])] = None
    battery: Annotated[
        BatteryResponse | None,
        Field(description="감지 모듈 배터리. 노드가 전압을 보내기 전까지 null"),
    ] = None
    link: Annotated[
        LinkQuality | None,
        Field(description="연결 상태. 한 번도 받은 적 없으면 null"),
    ] = None
    sensor_check: Annotated[
        SensorCheck | None,
        Field(description="센서 점검 결과. 관측이 없으면 null"),
    ] = None
    last_seen_at: Annotated[
        datetime | None, Field(description="마지막으로 프레임을 받은 시각 (UTC)")
    ] = None

    @classmethod
    def from_domain(cls, profile: DeviceProfile) -> DeviceResponse:
        return cls(
            mac=profile.mac,
            label=profile.label,
            parking_slot=profile.parking_slot,
            battery=BatteryResponse.from_domain(profile.battery) if profile.battery else None,
            link=profile.link,
            sensor_check=profile.sensor_check,
            last_seen_at=profile.last_seen_at,
        )
