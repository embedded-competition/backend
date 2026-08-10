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
        if self.received - self._last_logged < every:
            return False
        self._last_logged = self.received
        return True
