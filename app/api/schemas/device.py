from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.base import ApiModel


class DeviceRegisterRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    mac: Annotated[
        str,
        Field(
            min_length=12,
            max_length=17,
            description="점검장비 라벨의 MAC 주소. 구분자는 서버가 정규화한다",
            examples=["AA:BB:CC:DD:EE:FF"],
        ),
    ]


class DeviceRegisterResponse(ApiModel):
    device_id: Annotated[
        str, Field(description="이후 모든 경로에 쓰는 식별자", examples=["dev_01h8xzk3q0"])
    ]
    device_token: Annotated[
        str,
        Field(
            description=(
                "Authorization: Bearer 에 쓴다. 만료 없음. 재조회 불가 — 앱이 저장해야 한다"
            ),
            examples=["dtk_9f8e7d6c5b4a"],
        ),
    ]
    management_phone: Annotated[
        str | None,
        Field(
            description="등록 위치 관리실 전화번호. 경보 화면 버튼에 사용",
            examples=["01029015899"],
        ),
    ] = None


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
