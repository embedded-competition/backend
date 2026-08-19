from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import status_for
from app.api.schemas.base import ErrorResponse
from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = _request_id(request)
        http_status = status_for(exc)
        logger.warning(
            "domain error",
            extra={
                "code": exc.code,
                "status": http_status,
                "request_id": request_id,
                "detail": str(exc),
            },
        )
        return _error(http_status, exc.code, request_id)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        logger.info("validation error", extra={"request_id": request_id, "errors": exc.errors()})
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", request_id)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception("unhandled error", extra={"request_id": request_id})
        return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", request_id)


def _error(http_status: int, code: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=ErrorResponse(error=code, requestId=request_id).model_dump(),
    )


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str):
        return existing
    return uuid.uuid4().hex
