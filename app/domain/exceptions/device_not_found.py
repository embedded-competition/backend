from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class DeviceNotFound(DomainError):
    code = "device_not_found"
