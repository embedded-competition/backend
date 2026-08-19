from __future__ import annotations

from app.domain.exceptions.frame_error import FrameError


class FrameFieldError(FrameError):
    code = "frame_field_error"
