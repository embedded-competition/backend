from __future__ import annotations

from app.domain.exceptions.frame_error import FrameError


class FrameCrcError(FrameError):
    code = "frame_crc_error"
