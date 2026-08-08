"""도메인 예외 → HTTP 상태 매핑 단일 지점. 라우터가 HTTPException을 흩뿌리지 않는다.

응답 형식은 앱 계약(api-spec.md §공통 에러): `{"error": "<code>"}`.
`requestId`를 덧붙이지만 앱은 `error` 키만 읽으므로 호환이 깨지지 않는다.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas.base import ErrorResponse
from app.domain.exceptions import (
    AlertAlreadyAcknowledged,
    AlertNotFound,
    DeviceAlreadyPaired,
    DeviceInactive,
    DeviceNotFound,
    DeviceNotRegistered,
    DomainError,
    FrameError,
    InvalidMac,
    ReleaseNotAllowed,
    Unauthorized,
)

logger = logging.getLogger(__name__)

# 구체 예외부터 검사한다 — 상속 관계라 순서가 곧 우선순위다.
_STATUS_BY_EXCEPTION: tuple[tuple[type[DomainError], int], ...] = (
    (Unauthorized, status.HTTP_401_UNAUTHORIZED),
    (DeviceNotFound, status.HTTP_404_NOT_FOUND),
    (AlertNotFound, status.HTTP_404_NOT_FOUND),
    (DeviceAlreadyPaired, status.HTTP_409_CONFLICT),
    (AlertAlreadyAcknowledged, status.HTTP_409_CONFLICT),
    (DeviceInactive, status.HTTP_409_CONFLICT),
    (ReleaseNotAllowed, status.HTTP_403_FORBIDDEN),
    (DeviceNotRegistered, status.HTTP_403_FORBIDDEN),
    (InvalidMac, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (FrameError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


def _status_for(exc: DomainError) -> int:
    for exc_type, code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_400_BAD_REQUEST


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str):
        return existing
    return uuid.uuid4().hex


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = _request_id(request)
        http_status = _status_for(exc)
        # 상세 메시지는 로그에만 — 응답에는 코드만 나간다.
        logger.warning(
            "domain error",
            extra={
                "code": exc.code,
                "status": http_status,
                "request_id": request_id,
                "detail": str(exc),
            },
        )
        return JSONResponse(
            status_code=http_status,
            content=ErrorResponse(error=exc.code, requestId=request_id).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        logger.info(
            "validation error",
            extra={"request_id": request_id, "errors": exc.errors()},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ErrorResponse(error="validation_error", requestId=request_id).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        # 스택·SQL·경로를 응답에 노출하지 않는다.
        logger.exception("unhandled error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(error="internal_error", requestId=request_id).model_dump(),
        )
