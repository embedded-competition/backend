from __future__ import annotations

from fastapi import status

from app.domain.exceptions import (
    AlertAlreadyAcknowledged,
    AlertNotFound,
    DeviceInactive,
    DeviceNotFound,
    DomainError,
    FrameError,
    InvalidInterval,
    InvalidMac,
    InvalidPeriod,
    LocationUnavailable,
    ReleaseNotAllowed,
)

_STATUS_BY_EXCEPTION: tuple[tuple[type[DomainError], int], ...] = (
    (DeviceNotFound, status.HTTP_404_NOT_FOUND),
    (LocationUnavailable, status.HTTP_404_NOT_FOUND),
    (AlertNotFound, status.HTTP_404_NOT_FOUND),
    (AlertAlreadyAcknowledged, status.HTTP_409_CONFLICT),
    (DeviceInactive, status.HTTP_409_CONFLICT),
    (ReleaseNotAllowed, status.HTTP_403_FORBIDDEN),
    (InvalidMac, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidPeriod, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (InvalidInterval, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (FrameError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


def status_for(exc: DomainError) -> int:
    for exc_type, code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_400_BAD_REQUEST
