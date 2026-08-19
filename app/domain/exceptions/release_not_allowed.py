from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class ReleaseNotAllowed(DomainError):
    code = "not_allowed"
