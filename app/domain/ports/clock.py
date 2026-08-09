"""시간 주입 port."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """도메인·서비스에서 datetime.now()를 직접 부르지 않는다."""

    def now(self) -> datetime: ...
