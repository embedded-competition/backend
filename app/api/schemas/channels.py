"""센서 채널 DTO. 현재 상태와 시간당 집계가 공유한다."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.api.schemas.base import ApiModel


class GasChannelResponse(ApiModel):
    """raw(sraw·mv·baseline)는 없다 — 노드가 정규화값만 보낸다 (정합화 B2)."""

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
