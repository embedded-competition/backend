from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class InvalidMac(DomainError):
    code = "invalid_mac"
