from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class AlertNotFound(DomainError):
    code = "alert_not_found"
