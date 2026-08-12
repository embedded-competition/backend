from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.base import ApiModel
from app.core.module_status import ModuleStatus
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


class ModuleStatusResponse(ApiModel):
    """감지 모듈 자기진단. 전부 서버가 판정한 결과다.

    근거값(전압·dBm·마지막 수신 시각)은 담지 않는다 — 내보내면 앱이 그 값으로 다시
    판정할 수 있게 되고 임계가 두 곳에 생긴다.
    """

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

    @classmethod
    def from_domain(cls, status: ModuleStatus) -> ModuleStatusResponse:
        return cls(
            battery=BatteryResponse.from_domain(status.battery) if status.battery else None,
            link=status.link,
            sensor_check=status.sensor_check,
        )
