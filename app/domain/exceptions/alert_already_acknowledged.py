from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class AlertAlreadyAcknowledged(DomainError):
    code = "alert_already_acknowledged"
