from __future__ import annotations

from app.domain.exceptions.domain_error import DomainError


class FrameError(DomainError):
    code = "frame_error"
