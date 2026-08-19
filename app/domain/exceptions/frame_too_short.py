from __future__ import annotations

from app.domain.exceptions.frame_error import FrameError


class FrameTooShort(FrameError):
    code = "frame_too_short"
