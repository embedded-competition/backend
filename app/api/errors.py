"""도메인 예외 → HTTP 상태 매핑표. 핸들러 등록은 exception_handlers.py."""

from __future__ import annotations

from fastapi import status

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


def status_for(exc: DomainError) -> int:
    for exc_type, code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_400_BAD_REQUEST
