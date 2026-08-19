from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.gas_channel import GasChannel


@dataclass(frozen=True, slots=True)
class ChannelReading:
    channel: GasChannel
    deviation: float | None
    slope: float | None
