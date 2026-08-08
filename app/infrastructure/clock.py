"""Clock port 구현. 도메인·서비스는 datetime.now()를 직접 부르지 않는다."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
