"""수신 카운터. 통신 품질 저하와 유실을 드러내는 유일한 지표다."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


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
    _last_logged: int = field(default=0, repr=False)

    def as_dict(self) -> dict[str, int]:
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}

    def should_report(self, every: int) -> bool:
        """N건마다 1줄만 남긴다 — 프레임마다 INFO를 찍으면 SD카드만 닳는다."""
        if self.received - self._last_logged < every:
            return False
        self._last_logged = self.received
        return True
