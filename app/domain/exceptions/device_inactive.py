from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class DeviceInactive(DomainError):
    code = "device_inactive"
