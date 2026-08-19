from __future__ import annotations

from dataclasses import dataclass

_LAT_LIMIT = 90.0
_LON_LIMIT = 180.0


@dataclass(frozen=True, slots=True)
class Coordinates:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -_LAT_LIMIT <= self.lat <= _LAT_LIMIT:
            raise ValueError(f"lat 범위 이탈: {self.lat}")
        if not -_LON_LIMIT <= self.lon <= _LON_LIMIT:
            raise ValueError(f"lon 범위 이탈: {self.lon}")
