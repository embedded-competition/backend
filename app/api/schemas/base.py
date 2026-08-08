"""응답 DTO 공통 설정.

앱은 camelCase를 기대한다 (앱 api-spec.md). 서버 내부는 snake_case를 유지하고
직렬화 시점에만 alias로 변환한다 — 파이썬 코드에 camelCase가 번지지 않게.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
        # 응답은 항상 alias(camelCase)로 나간다
        serialize_by_alias=True,
    )


class ErrorResponse(BaseModel):
    """전 endpoint 단일 에러 형식 (앱 api-spec.md §공통 에러).

    앱은 `error` 키만 읽는다. `requestId`는 서버 로그 대조용 부가 정보라
    추가해도 앱 계약이 깨지지 않는다.
    """

    model_config = ConfigDict(strict=True)

    error: str
    # 필드명이 camelCase인 이유: 이 모델은 alias 변환 없이 그대로 직렬화된다
    requestId: str
