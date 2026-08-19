from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta


@dataclass(slots=True)
class ReceiveStats:
    received: int = 0
    stored: int = 0
    duplicate: int = 0
    crc_error: int = 0
    parse_error: int = 0
    unknown_device: int = 0
    missed_frames: int = 0
    alerts: int = 0
    _reported_at: datetime | None = field(default=None, repr=False)

    def as_dict(self) -> dict[str, int]:
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}

    def should_report(self, at: datetime, every: timedelta) -> bool:
        """프레임 개수가 아니라 시간으로 끊는다.

        수신 속도는 소스마다 열 배씩 다르다. 개수로 끊으면 느린 소스는 몇 시간에
        한 줄, 빠른 소스는 몇 초에 한 줄이 되고, 빠른 쪽이 느린 쪽의 경고를 묻는다.
        시각은 프레임이 들고 온 것을 쓴다 — 이 통계는 수신의 통계이지 벽시계의
        통계가 아니고, 시계를 따로 주입할 이유도 없다.
        """
        if self._reported_at is None:
            self._reported_at = at
            return False
        if at - self._reported_at < every:
            return False
        self._reported_at = at
        return True
