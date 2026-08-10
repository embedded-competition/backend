from __future__ import annotations

from dataclasses import dataclass

from app.core.severity import severity_of, state_for
from app.domain.device import Device
from app.domain.value_objects import AlertState


@dataclass(frozen=True, slots=True)
class FleetComparison:
    fleet_size: int
    fleet_avg_level: AlertState
    my_level: AlertState
    my_multiplier: float


def compare(device: Device, fleet: list[Device]) -> FleetComparison:
    my_level = device.last_state or AlertState.NORMAL
    severities = [severity_of(d.last_state or AlertState.NORMAL) for d in fleet]
    avg = sum(severities) / len(severities) if severities else 0.0
    return FleetComparison(
        fleet_size=len(fleet),
        fleet_avg_level=state_for(avg),
        my_level=my_level,
        my_multiplier=round(severity_of(my_level) / avg, 1) if avg > 0 else 1.0,
    )
