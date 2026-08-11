from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class InvalidInterval(DomainError):
    code = "invalid_interval"
