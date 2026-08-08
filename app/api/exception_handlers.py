"""도메인 예외 → HTTP 상태 매핑 단일 지점. 라우터가 HTTPException을 흩뿌리지 않는다."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.domain.exceptions import (
    AlertAlreadyAcknowledged,
    AlertNotFound,
    DeviceInactive,
    DeviceNotFound,
    DeviceNotRegistered,
    DomainError,
    FrameError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_EXCEPTION: dict[type[DomainError], int] = {
    DeviceNotFound: status.HTTP_404_NOT_FOUND,
    AlertNotFound: status.HTTP_404_NOT_FOUND,
    DeviceNotRegistered: status.HTTP_403_FORBIDDEN,
    DeviceInactive: status.HTTP_409_CONFLICT,
    AlertAlreadyAcknowledged: status.HTTP_409_CONFLICT,
    FrameError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


class ErrorResponse(BaseModel):
    """전 endpoint 단일 에러 형식."""

    model_config = ConfigDict(strict=True)

    code: Annotated[str, Field(description="도메인 예외 코드", examples=["DEVICE_NOT_FOUND"])]
    message: Annotated[str, Field(description="사람이 읽는 설명")]
    request_id: Annotated[str, Field(description="로그 대조용 식별자")]
    detail: Annotated[dict[str, object] | None, Field(description="부가 정보")] = None


def _status_for(exc: DomainError) -> int:
    for exc_type, code in _STATUS_BY_EXCEPTION.items():
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_400_BAD_REQUEST


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = _request_id(request)
        logger.warning("domain error", extra={"code": exc.code, "request_id": request_id})
        return JSONResponse(
            status_code=_status_for(exc),
            content=ErrorResponse(
                code=exc.code, message=str(exc), request_id=request_id
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ErrorResponse(
                code="VALIDATION_ERROR",
                message="요청 형식이 올바르지 않다",
                request_id=request_id,
                detail={"errors": exc.errors()},
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        # 상세는 로그로만. 응답에 스택·SQL·경로를 노출하지 않는다.
        logger.exception("unhandled error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code="INTERNAL_ERROR",
                message="서버 내부 오류",
                request_id=request_id,
            ).model_dump(),
        )


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str):
        return existing
    return uuid.uuid4().hex
