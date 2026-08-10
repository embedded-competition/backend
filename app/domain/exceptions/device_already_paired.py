from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class DeviceAlreadyPaired(DomainError):
    code = "already_paired"
