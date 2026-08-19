from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadioQuality:
    rssi: int | None = None
    snr: float | None = None

    def __post_init__(self) -> None:
        if self.rssi is not None and self.rssi > 0:
            raise ValueError(f"rssi는 0 이하여야 한다: {self.rssi}")
