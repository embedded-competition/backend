from __future__ import annotations

from enum import StrEnum

from app.domain.value_objects import AlertState


class DeviceStatus(StrEnum):
    """사용자가 지금 무엇을 해야 하는가. 화면 게이지의 세 지점과 1:1이다.

    도메인의 AlertState는 다섯 값이지만 그중 둘은 사용자에게 시킬 행동이 없다.
    WARMUP은 아직 말할 것이 없고, WATCH는 "지켜본다"라서 게이지에 놓을 자리가
    없다 — 무엇을 지켜봐야 하는지는 stage가 대신 답한다.
    """

    STABLE = "STABLE"
    SERVICE_NEEDED = "SERVICE_NEEDED"
    REPORT = "REPORT"

    @classmethod
    def of(cls, state: AlertState | None) -> DeviceStatus | None:
        return _BY_STATE.get(state) if state is not None else None


_BY_STATE: dict[AlertState, DeviceStatus] = {
    AlertState.NORMAL: DeviceStatus.STABLE,
    AlertState.WATCH: DeviceStatus.STABLE,
    AlertState.FAULT: DeviceStatus.SERVICE_NEEDED,
    AlertState.ALARM: DeviceStatus.REPORT,
}
"""WARMUP은 일부러 빠져 있다. 예열 중에 "안정"이라고 답하면 아직 감지가 시작되지도
않았는데 괜찮다고 말하는 것이다. 그때는 null이 정직하다."""
