"""등록 기기 전체 대비 위치 계산. 저장소를 모르는 순수 계산."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.severity import severity_of, state_for
from app.domain.models import Device
from app.domain.value_objects import AlertState


@dataclass(frozen=True, slots=True)
class FleetComparison:
    fleet_size: int
    fleet_avg_level: AlertState
    my_level: AlertState
    my_multiplier: float


def compare(device: Device, fleet: list[Device]) -> FleetComparison:
    """1계정=1기기(O4)라 비교 모집단은 등록된 활성 기기 전체다."""
    my_level = device.last_state or AlertState.NORMAL
    severities = [severity_of(d.last_state or AlertState.NORMAL) for d in fleet]
    avg = sum(severities) / len(severities) if severities else 0.0
    return FleetComparison(
        fleet_size=len(fleet),
        fleet_avg_level=state_for(avg),
        my_level=my_level,
        # 평균이 0(전부 정상)이면 배수가 정의되지 않는다 — 1.0으로 둔다.
        my_multiplier=round(severity_of(my_level) / avg, 1) if avg > 0 else 1.0,
    )
