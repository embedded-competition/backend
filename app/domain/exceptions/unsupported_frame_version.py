from __future__ import annotations

from app.domain.exceptions.frame_error import FrameError


class UnsupportedFrameVersion(FrameError):
    code = "unsupported_frame_version"
